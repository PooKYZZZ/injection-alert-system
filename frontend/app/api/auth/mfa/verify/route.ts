import { NextResponse } from 'next/server'
import { z } from 'zod'

import { auth, signIn } from '@/auth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { readPreAuthHandle, clearPreAuthCookie } from '@/lib/auth/preauth'
import {
  mfaEnrollmentEnabled,
  requireTrustedOrigin,
  featureDisabledResponse,
  isTerminalTotpError,
  totpErrorResponse,
} from '@/lib/server/db/account-route-response'
import { verifyMfaLogin } from '@/lib/server/db/mfa-challenges'

const requestSchema = z.object({ code: z.string().regex(/^\d{6}$/) }).strict()

export async function POST(request: Request): Promise<Response> {
  if (!mfaEnrollmentEnabled()) return featureDisabledResponse()
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const session = await auth()
  const authorization = await requireMfaChallengePermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT
  )
  if (!authorization.ok) return authorization.response
  const preAuthHandle = readPreAuthHandle(request)
  if (!preAuthHandle) return totpErrorResponse(new Error('INVALID_REQUEST'))
  try {
    const input = requestSchema.parse(await request.json())
    const completion = await verifyMfaLogin(
      session!.user.id,
      preAuthHandle,
      input.code
    )
    await signIn('credentials', {
      mfa_completion_token: completion.completion_token,
      redirect: false,
      redirectTo: '/dashboard',
    })
    await clearPreAuthCookie()
    return NextResponse.json({ status: 'authenticated' })
  } catch (error) {
    if (isTerminalTotpError(error)) {
      try {
        await clearPreAuthCookie()
      } catch {
        // Keep the terminal response safe even if cookie cleanup is unavailable.
      }
    }
    return totpErrorResponse(error)
  }
}
