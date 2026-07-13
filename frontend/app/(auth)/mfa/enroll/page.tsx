import { notFound, redirect } from 'next/navigation'

import { auth } from '@/auth'
import { requireMfaEnrollmentPermission } from '@/lib/auth/route-guard'
import { readPreAuthHandleFromCookies } from '@/lib/auth/preauth'
import { PERMISSIONS } from '@/lib/auth/roles'
import { readPageRuntimeAuthFlags } from '@/lib/server/runtime-config'
import { TotpEnrollmentForm } from '@/features/user-management/TotpEnrollmentForm'

export default async function TotpEnrollmentPage() {
  const flags = await readPageRuntimeAuthFlags()
  if (!flags.mfaEnrollmentEnabled) notFound()
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
