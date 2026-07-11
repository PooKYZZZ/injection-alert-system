import { notFound, redirect } from 'next/navigation'

import { auth } from '@/auth'
import { requireMfaEnrollmentPermission } from '@/lib/auth/route-guard'
import { readPreAuthHandleFromCookies } from '@/lib/auth/preauth'
import { PERMISSIONS } from '@/lib/auth/roles'
import { mfaEnrollmentEnabled } from '@/lib/server/db/account-route-response'
import { TotpEnrollmentForm } from '@/features/user-management/TotpEnrollmentForm'

export default async function TotpEnrollmentPage() {
  if (!mfaEnrollmentEnabled()) notFound()
  const session = await auth()
  const preAuthHandle = await readPreAuthHandleFromCookies()
  const authorization = await requireMfaEnrollmentPermission(
    session,
    PERMISSIONS.MFA_ENROLLMENT,
    preAuthHandle
  )
  if (!authorization.ok) redirect('/login')
  return <TotpEnrollmentForm />
}
