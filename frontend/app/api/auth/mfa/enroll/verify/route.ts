import { NextResponse } from 'next/server'
import { z } from 'zod'

import { auth } from '@/auth'
import { requireMfaEnrollmentPermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import {
  featureDisabledResponse,
  mfaEnrollmentEnabled,
  requireTrustedOrigin,
  totpErrorResponse,
} from '@/lib/server/db/account-route-response'
import { completeTotpEnrollment } from '@/lib/server/db/totp-enrollment'

const requestSchema = z.object({
  factor_id: z.string().uuid(),
  code: z.string().regex(/^\d{6}$/),
}).strict()

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
    const input = requestSchema.parse(await request.json())
    return NextResponse.json(
      await completeTotpEnrollment(session!.user.id, input.factor_id, input.code)
    )
  } catch (error) {
    return totpErrorResponse(error)
  }
}
