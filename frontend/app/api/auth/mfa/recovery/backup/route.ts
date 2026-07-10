import { NextResponse } from 'next/server'

import { auth, signIn } from '@/auth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { requireTrustedOrigin, recoveryErrorResponse, mfaEnrollmentEnabled } from '@/lib/server/db/account-route-response'
import { consumeBackupCodeForRecovery } from '@/lib/server/db/mfa-recovery'
import { z } from 'zod'

const requestSchema = z.object({ code: z.string().min(1).max(32) }).strict()

export async function POST(request: Request): Promise<Response> {
  if (!mfaEnrollmentEnabled()) return NextResponse.json({ error: { code: 'NOT_FOUND' } }, { status: 404 })
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const session = await auth()
  const authorization = await requireMfaChallengePermission(session, PERMISSIONS.MFA_ENROLLMENT)
  if (!authorization.ok) return authorization.response
  try {
    const input = requestSchema.parse(await request.json())
    const completion = await consumeBackupCodeForRecovery(session!.user.id, input.code)
    await signIn('credentials', {
      recovery_completion_token: completion.completion_token,
      redirectTo: '/mfa/enroll',
    })
    return NextResponse.json({ status: 'recovery_started' })
  } catch (error) {
    if (error instanceof Error && error.message === 'NEXT_REDIRECT') throw error
    return recoveryErrorResponse(error)
  }
}
