import { NextResponse } from 'next/server'
import { z } from 'zod'

import { requireTrustedOrigin } from '@/lib/server/db/account-route-response'
import {
  completePasswordReset,
  PasswordRecoveryError,
} from '@/lib/server/db/password-recovery'

const requestSchema = z.object({ token: z.string().min(40).max(512), password: z.string().min(6).max(256) }).strict()

export async function POST(request: Request): Promise<Response> {
  const respond = (body: Record<string, unknown>, status: number) =>
    NextResponse.json(body, {
      status,
      headers: { 'Cache-Control': 'no-store' },
    })

  if (process.env.AUTH_PASSWORD_RESET_ENABLED !== 'true') {
    return respond({ error: { code: 'NOT_FOUND' } }, 404)
  }
  const originError = requireTrustedOrigin(request)
  if (originError) return originError

  let body: unknown
  try {
    body = await request.json()
  } catch {
    return respond(
      { error: { code: 'INVALID_REQUEST', message: 'Check the reset form and try again.' } },
      400
    )
  }

  const parsed = requestSchema.safeParse(body)
  if (!parsed.success) {
    return respond(
      { error: { code: 'INVALID_REQUEST', message: 'Check the reset form and try again.' } },
      400
    )
  }

  try {
    await completePasswordReset(parsed.data.token, parsed.data.password)
    return respond({ status: 'password_reset' }, 200)
  } catch (error) {
    if (error instanceof PasswordRecoveryError) {
      if (error.code === 'INVALID_OR_EXPIRED') {
        return respond(
          { error: { code: error.code, message: 'This reset link is invalid or expired.' } },
          400
        )
      }
      if (error.code === 'INVALID_REQUEST') {
        return respond(
          { error: { code: error.code, message: 'Check the reset form and try again.' } },
          400
        )
      }
    }

    return respond(
      { error: { code: 'UNAVAILABLE', message: 'Password reset is temporarily unavailable. Try again.' } },
      503
    )
  }
}
