import { NextResponse } from 'next/server'

import { auth } from '@/auth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { requireTrustedOrigin, recoveryErrorResponse, featureDisabledResponse } from '@/lib/server/db/account-route-response'
import { requestEmailRecovery } from '@/lib/server/db/mfa-recovery'
import { setRecoveryCompletionCookie } from '@/lib/auth/recovery-cookie'

export async function POST(request: Request): Promise<Response> {
  if (process.env.AUTH_EMAIL_RECOVERY_ENABLED !== 'true') return featureDisabledResponse()
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const session = await auth()
  const authorization = await requireMfaChallengePermission(session, PERMISSIONS.MFA_ENROLLMENT)
  if (!authorization.ok) return authorization.response
  try {
    const result = await requestEmailRecovery(session!.user.id)
    await setRecoveryCompletionCookie(result.completion_token)
    return NextResponse.json({ status: 'sent' })
  } catch (error) {
    return recoveryErrorResponse(error)
  }
}
