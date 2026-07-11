import { NextResponse } from 'next/server'

import { auth } from '@/auth'
import { setPreAuthCookie } from '@/lib/auth/preauth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import {
  featureDisabledResponse,
  mfaEnrollmentEnabled,
  requireTrustedOrigin,
  totpErrorResponse,
} from '@/lib/server/db/account-route-response'
import { beginRecentTotpChallenge } from '@/lib/server/db/mfa-challenges'

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
  try {
    const challenge = await beginRecentTotpChallenge(session!.user.id)
    await setPreAuthCookie(challenge.handle)
    return NextResponse.json({
      status: 'challenge_started',
      expires_at: challenge.expires_at,
    })
  } catch (error) {
    return totpErrorResponse(error)
  }
}
