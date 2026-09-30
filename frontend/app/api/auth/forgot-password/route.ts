import { NextResponse } from 'next/server'
import { z } from 'zod'

import { requireTrustedOrigin } from '@/lib/server/db/account-route-response'
import { requestPasswordReset } from '@/lib/server/db/password-recovery'

const requestSchema = z.object({ email: z.string().trim().email().max(320) }).strict()

export async function POST(request: Request): Promise<Response> {
  const originError = requireTrustedOrigin(request)
  if (originError) return originError

  const respond = (body: Record<string, string>, status: number) =>
    NextResponse.json(body, {
      status,
      headers: { 'Cache-Control': 'no-store' },
    })

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return respond({ status: 'invalid_request', message: 'Enter a valid email address.' }, 400)
  }

  const parsed = requestSchema.safeParse(body)
  if (!parsed.success) {
    return respond({ status: 'invalid_request', message: 'Enter a valid email address.' }, 400)
  }

  if (process.env.AUTH_PASSWORD_RESET_ENABLED !== 'true') {
    return respond(
      { status: 'unavailable', message: 'Password reset is unavailable right now. Please try again later.' },
      503
    )
  }

  try {
    const result = await requestPasswordReset(parsed.data.email)
    if (result.status === 'not_found') {
      return respond(
        { status: 'not_found', message: 'No eligible account was found for this email address.' },
        404
      )
    }
    return respond(
      { status: 'sent', message: 'Reset instructions were queued for this account. Check your inbox.' },
      200
    )
  } catch {
    return respond(
      { status: 'unavailable', message: 'Password reset is unavailable right now. Please try again later.' },
      503
    )
  }
}
