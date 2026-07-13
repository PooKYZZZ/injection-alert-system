import { redirect } from 'next/navigation'

import { auth } from '@/auth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { readPageRuntimeAuthFlags } from '@/lib/server/runtime-config'
import { RecentTotpStepUpForm } from '@/features/user-management/RecentTotpStepUpForm'

export default async function RecentTotpStepUpPage({
  searchParams,
}: {
  searchParams: Promise<{ returnTo?: string }>
}) {
  const flags = await readPageRuntimeAuthFlags()
  if (!flags.mfaEnrollmentEnabled) redirect('/login')
  const session = await auth()
  const authorization = await requireMfaChallengePermission(
    session,
    PERMISSIONS.ACCOUNTS_MANAGE
  )
  if (!authorization.ok) redirect('/login')
  const params = await searchParams
  const returnTo = params.returnTo && params.returnTo.startsWith('/') && !params.returnTo.startsWith('//')
    ? params.returnTo
    : '/dashboard'
  return <RecentTotpStepUpForm redirectTo={returnTo} />
}
