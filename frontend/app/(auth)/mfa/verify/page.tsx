import { redirect } from 'next/navigation'

import { auth } from '@/auth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { mfaEnrollmentEnabled } from '@/lib/server/db/account-route-response'
import { MfaVerifyForm } from '@/features/user-management/MfaVerifyForm'

export default async function MfaVerifyPage() {
  if (!mfaEnrollmentEnabled()) redirect('/login')
  const session = await auth()
  const authorization = await requireMfaChallengePermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT
  )
  if (!authorization.ok) redirect('/login')
  return <MfaVerifyForm />
}
