import { NextResponse } from 'next/server'
import { z } from 'zod'

import { auth, signIn } from '@/auth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { requireTrustedOrigin, recoveryErrorResponse, featureDisabledResponse } from '@/lib/server/db/account-route-response'
import { completeEmailRecovery } from '@/lib/server/db/mfa-recovery'
import { readRecoveryCompletionCookie } from '@/lib/auth/recovery-cookie'
import { clearRecoveryHandoffCookies } from '@/lib/auth/recovery-handoff'

const requestSchema = z.object({ code: z.string().regex(/^\d{6}$/) }).strict()

export async function POST(request: Request): Promise<Response> {
  if (process.env.AUTH_EMAIL_RECOVERY_ENABLED !== 'true') return featureDisabledResponse()
  const originError = requireTrustedOrigin(request)
  if (originError) return originError
  const session = await auth()
  const completionToken = readRecoveryCompletionCookie(request)
  const authorization = await requireMfaChallengePermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT,
    { allowRecoveryFinalization: Boolean(completionToken) }
  )
  if (!authorization.ok) return authorization.response
  if (!completionToken) return recoveryErrorResponse(new Error('INVALID_CODE'))
  try {
    const input = requestSchema.parse(await request.json())
    let handoffComplete = false
    try {
      await completeEmailRecovery(session!.user.id, input.code)
    } catch {
      // A prior Auth.js handoff may have consumed the DB token before the
      // browser received its redirect.  Retrying the same short-lived cookie
      // is allowed by the database handoff contract; a first-use token still
      // fails closed here.
      await signIn('credentials', {
        recovery_completion_token: completionToken,
        redirect: false,
        redirectTo: '/mfa/enroll',
      })
      handoffComplete = true
    }
    if (!handoffComplete) {
      await signIn('credentials', {
        recovery_completion_token: completionToken,
        redirect: false,
        redirectTo: '/mfa/enroll',
      })
    }
    await clearRecoveryHandoffCookies()
    return NextResponse.json({ status: 'recovery_started' })
  } catch (error) {
    return recoveryErrorResponse(error)
  }
}
