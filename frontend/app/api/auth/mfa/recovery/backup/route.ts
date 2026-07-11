import { NextResponse } from 'next/server'

import { auth, signIn } from '@/auth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { requireTrustedOrigin, recoveryErrorResponse, mfaEnrollmentEnabled } from '@/lib/server/db/account-route-response'
import { consumeBackupCodeForRecovery } from '@/lib/server/db/mfa-recovery'
import {
  clearRecoveryCompletionCookie,
  readRecoveryCompletionCookie,
  setRecoveryCompletionCookie,
} from '@/lib/auth/recovery-cookie'
import { z } from 'zod'

const requestSchema = z.object({ code: z.string().min(1).max(32) }).strict()

export async function POST(request: Request): Promise<Response> {
  if (!mfaEnrollmentEnabled()) return NextResponse.json({ error: { code: 'NOT_FOUND' } }, { status: 404 })
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const session = await auth()
  let completionToken = readRecoveryCompletionCookie(request)
  const authorization = await requireMfaChallengePermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT,
    { allowRecoveryFinalization: Boolean(completionToken) }
  )
  if (!authorization.ok) return authorization.response
  try {
    if (completionToken) {
      try {
        await signIn('credentials', {
          recovery_completion_token: completionToken,
          redirectTo: '/mfa/enroll',
        })
        await clearRecoveryCompletionCookie()
        return NextResponse.json({ status: 'recovery_started' })
      } catch (handoffError) {
        if (handoffError instanceof Error && handoffError.message === 'NEXT_REDIRECT') {
          await clearRecoveryCompletionCookie()
          throw handoffError
        }
        completionToken = null
      }
    }
    const input = requestSchema.parse(await request.json())
    const completion = await consumeBackupCodeForRecovery(session!.user.id, input.code)
    completionToken = completion.completion_token
    await setRecoveryCompletionCookie(completionToken)
    await signIn('credentials', {
      recovery_completion_token: completionToken,
      redirectTo: '/mfa/enroll',
    })
    await clearRecoveryCompletionCookie()
    return NextResponse.json({ status: 'recovery_started' })
  } catch (error) {
    if (error instanceof Error && error.message === 'NEXT_REDIRECT') {
      await clearRecoveryCompletionCookie()
      throw error
    }
    return recoveryErrorResponse(error)
  }
}
