import { NextResponse } from 'next/server'
import { z } from 'zod'

import { auth, signIn } from '@/auth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { requireTrustedOrigin, recoveryErrorResponse, featureDisabledResponse } from '@/lib/server/db/account-route-response'
import { completeEmailRecovery } from '@/lib/server/db/mfa-recovery'
import { clearRecoveryCompletionCookie, readRecoveryCompletionCookie } from '@/lib/auth/recovery-cookie'

const requestSchema = z.object({ code: z.string().regex(/^\d{6}$/) }).strict()

export async function POST(request: Request): Promise<Response> {
  if (process.env.AUTH_EMAIL_RECOVERY_ENABLED !== 'true') return featureDisabledResponse()
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const session = await auth()
  const authorization = await requireMfaChallengePermission(session, PERMISSIONS.MFA_ENROLLMENT)
  if (!authorization.ok) return authorization.response
  const completionToken = readRecoveryCompletionCookie(request)
  if (!completionToken) return recoveryErrorResponse(new Error('INVALID_CODE'))
  try {
    const input = requestSchema.parse(await request.json())
    await completeEmailRecovery(session!.user.id, input.code)
    await clearRecoveryCompletionCookie()
    await signIn('credentials', {
      recovery_completion_token: completionToken,
      redirectTo: '/mfa/enroll',
    })
    return NextResponse.json({ status: 'recovery_started' })
  } catch (error) {
    if (error instanceof Error && error.message === 'NEXT_REDIRECT') throw error
    return recoveryErrorResponse(error)
  }
}
