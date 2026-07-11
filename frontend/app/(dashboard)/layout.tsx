import { redirect } from 'next/navigation'
import type { ReactNode } from 'react'
import { getSession } from '@/lib/auth-session'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS } from '@/lib/auth/roles'
import { Sidebar } from '@/components/layout/Sidebar'
import { DashboardTopBar } from '@/components/layout/TopBar'

export default async function DashboardLayout({
  children,
}: {
  children: ReactNode
}) {
  const session = await getSession()
  if (!session) redirect('/login')
  const authorization = await requirePermission(
    session,
    PERMISSIONS.ALERTS_READ
  )
  if (!authorization.ok) {
    if (
      session.user?.auth_level === 'password' &&
      (session.user.role === 'ADMIN' || session.user.role === 'ANALYST')
    ) {
      redirect(
        session.user.mfa_challenge_purpose === 'mfa_enrollment'
          ? '/mfa/enroll'
          : '/mfa/verify'
      )
    }
    if (
      session.user?.auth_level === 'recovery' &&
      (session.user.role === 'ADMIN' || session.user.role === 'ANALYST')
    ) {
      redirect('/mfa/enroll')
    }
    redirect('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background-main">
      <Sidebar
        displayName={session.user?.name ?? null}
        secondaryLabel={session.user?.email ?? null}
        role={session.user.role}
      />
      <div className="flex flex-col flex-1 overflow-hidden">
        <DashboardTopBar />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  )
}
