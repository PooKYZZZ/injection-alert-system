import { NextResponse } from 'next/server'
import { z } from 'zod'

import { auth } from '@/auth'
import { requireMfaEnrollmentPermission } from '@/lib/auth/route-guard'
import { readPreAuthHandle } from '@/lib/auth/preauth'
import { setMfaCompletionCookie } from '@/lib/auth/mfa-completion-cookie'
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
  const preAuthHandle = readPreAuthHandle(request)
  const authorization = await requireMfaEnrollmentPermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT,
    preAuthHandle
  )
  if (!authorization.ok) return authorization.response
  try {
    const input = requestSchema.parse(await request.json())
    const result = await completeTotpEnrollment(
      session!.user.id,
      input.factor_id,
      input.code,
      preAuthHandle
    )
    await setMfaCompletionCookie(result.completion_token)
    return NextResponse.json({
      backup_codes: result.backup_codes,
      status: 'pending_finalization',
    })
  } catch (error) {
    return totpErrorResponse(error)
  }
}
