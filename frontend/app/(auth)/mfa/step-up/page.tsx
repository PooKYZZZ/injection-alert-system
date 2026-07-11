import { redirect } from 'next/navigation'

import { auth } from '@/auth'
import { requireMfaChallengePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { mfaEnrollmentEnabled } from '@/lib/server/db/account-route-response'
import { RecentTotpStepUpForm } from '@/features/user-management/RecentTotpStepUpForm'

export default async function RecentTotpStepUpPage({
  searchParams,
}: {
  searchParams: Promise<{ returnTo?: string }>
}) {
  if (!mfaEnrollmentEnabled()) redirect('/login')
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
