import { NextResponse } from 'next/server'
import { z } from 'zod'

import { requireTrustedOrigin } from '@/lib/server/db/account-route-response'
import { completePasswordReset } from '@/lib/server/db/password-recovery'

const requestSchema = z.object({ token: z.string().min(40).max(512), password: z.string().min(6).max(256) }).strict()

export async function POST(request: Request): Promise<Response> {
  if (process.env.AUTH_PASSWORD_RESET_ENABLED !== 'true') return NextResponse.json({ error: { code: 'NOT_FOUND' } }, { status: 404 })
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  try {
    const input = requestSchema.parse(await request.json())
    await completePasswordReset(input.token, input.password)
    return NextResponse.json({ status: 'password_reset' })
  } catch {
    return NextResponse.json({ error: { code: 'INVALID_OR_EXPIRED', message: 'This reset link is invalid or expired.' } }, { status: 400 })
  }
}
