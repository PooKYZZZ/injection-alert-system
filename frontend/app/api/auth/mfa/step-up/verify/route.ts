import { NextResponse } from 'next/server'
import { z } from 'zod'

import { auth, signIn } from '@/auth'
import { clearPreAuthCookie, readPreAuthHandle } from '@/lib/auth/preauth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import {
  featureDisabledResponse,
  mfaEnrollmentEnabled,
  requireTrustedOrigin,
  totpErrorResponse,
} from '@/lib/server/db/account-route-response'
import { verifyRecentTotp } from '@/lib/server/db/mfa-challenges'

const requestSchema = z.object({
  code: z.string().regex(/^\d{6}$/),
  redirect_to: z.string().optional(),
}).strict()

function safeRedirectTarget(value: string | undefined): string {
  return value && value.startsWith('/') && !value.startsWith('//')
    ? value
    : '/dashboard'
}

export async function POST(request: Request): Promise<Response> {
  if (!mfaEnrollmentEnabled()) return featureDisabledResponse()
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const session = await auth()
  const authorization = await requireMfaChallengePermission(
    session,
    PERMISSIONS.ACCOUNTS_MANAGE
  )
  if (!authorization.ok) return authorization.response
  const preAuthHandle = readPreAuthHandle(request)
  if (!preAuthHandle) return totpErrorResponse(new Error('INVALID_REQUEST'))
  try {
    const input = requestSchema.parse(await request.json())
    const completion = await verifyRecentTotp(
      session!.user.id,
      preAuthHandle,
      input.code
    )
    await signIn('credentials', {
      mfa_completion_token: completion.completion_token,
      redirect: false,
      redirectTo: safeRedirectTarget(input.redirect_to),
    })
    await clearPreAuthCookie()
    return NextResponse.json({ status: 'authenticated' })
  } catch (error) {
    return totpErrorResponse(error)
  }
}
