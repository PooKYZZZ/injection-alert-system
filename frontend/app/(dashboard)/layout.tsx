import { redirect } from 'next/navigation'
import Link from 'next/link'
import type { ReactNode } from 'react'
import { getSession } from '@/lib/auth-session'
import { requirePermission } from '@/lib/auth/route-guard'
import { PERMISSIONS, roleRequiresMfa } from '@/lib/auth/roles'
import { Sidebar } from '@/components/layout/Sidebar'
import { DashboardTopBar } from '@/components/layout/TopBar'
import { AlertStreamSync } from '@/components/alerts/AlertStreamSync'

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
    if (authorization.response.status === 503) {
      return (
        <div className="min-h-screen bg-background-main px-4 py-8 text-text-primary sm:px-6">
          <main
            role="alert"
            className="mx-auto max-w-xl rounded-lg border border-border-light bg-[var(--color-bg-panel)] p-6 shadow-sm"
          >
            <p className="text-sm font-medium text-text-secondary">
              Security verification
            </p>
            <h1 className="mt-2 text-xl font-semibold">
              Dashboard temporarily unavailable
            </h1>
            <p className="mt-3 text-sm leading-6 text-text-secondary">
              We can’t verify your session right now. Your account was not
              changed. Please try again shortly.
            </p>
            <Link
              href="/dashboard"
              className="mt-5 inline-flex min-h-10 items-center rounded-md bg-accent px-4 text-sm font-semibold text-white transition-colors hover:bg-accent/90 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-accent"
            >
              Try again
            </Link>
          </main>
        </div>
      )
    }
    if (
      session.user?.auth_level === 'password' &&
      roleRequiresMfa(session.user.role)
    ) {
      redirect(
        session.user.mfa_challenge_purpose === 'mfa_enrollment'
          ? '/mfa/enroll'
          : '/mfa/verify'
      )
    }
    if (
      session.user?.auth_level === 'recovery' &&
      roleRequiresMfa(session.user.role)
    ) {
      redirect('/mfa/enroll')
    }
    redirect('/login')
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background-main">
      <AlertStreamSync />
      <Sidebar
        displayName={session.user?.name ?? null}
        secondaryLabel={session.user?.email ?? null}
        role={session.user.role}
      />
      <div className="flex flex-col flex-1 overflow-hidden">
        <DashboardTopBar />
        <main className="min-w-0 flex-1 overflow-auto p-3 sm:p-4 lg:p-6">{children}</main>
      </div>
    </div>
  )
}
