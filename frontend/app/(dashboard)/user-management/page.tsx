import { notFound } from 'next/navigation'

import { UserManagementWorkspace } from '@/features/user-management/UserManagementWorkspace'
import { getSession } from '@/lib/auth-session'
import { requireMfaPermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { listManagedAccounts } from '@/lib/server/db/account-management'

export default async function UserManagementPage() {
  if (process.env.AUTH_ACCOUNT_MANAGEMENT_ENABLED !== 'true') notFound()
  const session = await getSession()
  const authorization = await requireMfaPermission(
    session,
    PERMISSIONS.ACCOUNTS_READ
  )
  if (!authorization.ok) notFound()
  return <UserManagementWorkspace initialAccounts={await listManagedAccounts()} />
}
