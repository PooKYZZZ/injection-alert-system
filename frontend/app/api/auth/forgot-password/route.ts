import { NextResponse } from 'next/server'
import { z } from 'zod'

import { requireTrustedOrigin } from '@/lib/server/db/account-route-response'
import { requestPasswordReset } from '@/lib/server/db/password-recovery'

const requestSchema = z.object({ email: z.string().max(320) }).strict()

export async function POST(request: Request): Promise<Response> {
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const generic = { status: 'sent', message: 'If the account is eligible, a reset link has been sent.' }
  if (process.env.AUTH_PASSWORD_RESET_ENABLED !== 'true') return NextResponse.json(generic)
  try {
    const input = requestSchema.parse(await request.json())
    await requestPasswordReset(input.email)
  } catch {
    // Keep known and unknown account responses indistinguishable.
  }
  return NextResponse.json(generic)
}
