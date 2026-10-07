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
    // The account lookup remains an internal implementation detail. A 202
    // response means the request was accepted for processing, not delivered.
    await requestPasswordReset(parsed.data.email)
    return respond(
      {
        status: 'accepted',
        message: 'If an eligible account matches this address, reset instructions will be queued for delivery.',
      },
      202
    )
  } catch {
    return respond(
      { status: 'unavailable', message: 'Password reset is unavailable right now. Please try again later.' },
      503
    )
  }
}
