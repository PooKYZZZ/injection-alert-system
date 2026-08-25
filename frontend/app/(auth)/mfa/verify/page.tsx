import { redirect } from 'next/navigation'

import { auth } from '@/auth'
import { readPreAuthHandleFromCookies } from '@/lib/auth/preauth'
import { canRenderLoginMfaPage } from '@/lib/auth/login-mfa-challenge'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { readPageRuntimeAuthFlags } from '@/lib/server/runtime-config'
import { MfaVerifyForm } from '@/features/user-management/MfaVerifyForm'

export default async function MfaVerifyPage() {
  const flags = await readPageRuntimeAuthFlags()
  if (!flags.mfaEnrollmentEnabled) redirect('/login')
  const session = await auth()
  const authorization = await requireMfaChallengePermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT
  )
  const preAuthHandle = await readPreAuthHandleFromCookies()
  if (!authorization.ok || !canRenderLoginMfaPage(session, preAuthHandle)) redirect('/login')
  return <MfaVerifyForm />
}
