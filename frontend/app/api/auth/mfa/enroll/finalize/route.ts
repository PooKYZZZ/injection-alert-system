import { NextResponse } from 'next/server'

import { auth, signIn } from '@/auth'
import { clearPreAuthCookie } from '@/lib/auth/preauth'
import {
  clearMfaCompletionCookie,
  readMfaCompletionCookie,
} from '@/lib/auth/mfa-completion-cookie'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import {
  featureDisabledResponse,
  mfaEnrollmentEnabled,
  requireTrustedOrigin,
  totpErrorResponse,
} from '@/lib/server/db/account-route-response'

export async function POST(request: Request): Promise<Response> {
  if (!mfaEnrollmentEnabled()) return featureDisabledResponse()
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const session = await auth()
  const completionToken = readMfaCompletionCookie(request)
  const authorization = await requireMfaChallengePermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT,
    { allowEnrollmentFinalization: Boolean(completionToken) }
  )
  if (!authorization.ok) return authorization.response
  if (!completionToken) return totpErrorResponse(new Error('INVALID_REQUEST'))
  try {
    await signIn('credentials', {
      mfa_completion_token: completionToken,
      redirectTo: '/dashboard',
    })
    await clearMfaCompletionCookie()
    await clearPreAuthCookie()
    return NextResponse.json({ status: 'authenticated' })
  } catch (error) {
    if (error instanceof Error && error.message === 'NEXT_REDIRECT') {
      await clearMfaCompletionCookie()
      await clearPreAuthCookie()
      throw error
    }
    return totpErrorResponse(error)
  }
}
