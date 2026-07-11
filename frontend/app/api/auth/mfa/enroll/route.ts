import { NextResponse } from 'next/server'

import { auth } from '@/auth'
import { requireMfaEnrollmentPermission } from '@/lib/auth/route-guard'
import { generatePreAuthHandle, readPreAuthHandle, setPreAuthCookie } from '@/lib/auth/preauth'
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
  const recoveryEnrollment = session?.user?.auth_level === 'recovery'
  const preAuthHandle = recoveryEnrollment
    ? generatePreAuthHandle()
    : readPreAuthHandle(request)
  const authorization = await requireMfaEnrollmentPermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT,
    preAuthHandle
  )
  if (!authorization.ok) return authorization.response
  try {
    if (recoveryEnrollment && preAuthHandle) await setPreAuthCookie(preAuthHandle)
    return NextResponse.json(
      recoveryEnrollment
        ? await beginTotpEnrollment(session!.user.id, preAuthHandle, true)
        : await beginTotpEnrollment(session!.user.id, preAuthHandle)
    )
  } catch (error) {
    return totpErrorResponse(error)
  }
}
