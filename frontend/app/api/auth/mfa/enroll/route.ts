import { NextResponse } from 'next/server'

import { auth } from '@/auth'
import { requireMfaEnrollmentPermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import {
  featureDisabledResponse,
  mfaEnrollmentEnabled,
  requireTrustedOrigin,
  totpErrorResponse,
} from '@/lib/server/db/account-route-response'
import { beginTotpEnrollment } from '@/lib/server/db/totp-enrollment'

export async function POST(request: Request): Promise<Response> {
  if (!mfaEnrollmentEnabled()) return featureDisabledResponse()
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const session = await auth()
  const authorization = await requireMfaEnrollmentPermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT
  )
  if (!authorization.ok) return authorization.response
  try {
    return NextResponse.json(await beginTotpEnrollment(session!.user.id))
  } catch (error) {
    return totpErrorResponse(error)
  }
}
