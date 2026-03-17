import { redirect } from 'next/navigation'
import { getSession } from '@/lib/auth-session'
import { Sidebar } from '@/components/layout/Sidebar'
import { DashboardTopBar } from '@/components/layout/TopBar'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const session = await getSession()
  if (!session) redirect('/login')

  return (
    <div className="flex h-screen overflow-hidden bg-background-main">
      <Sidebar
        displayName={session.user?.name ?? null}
        secondaryLabel={session.user?.email ?? null}
      />
      <div className="flex flex-col flex-1 overflow-hidden">
        <DashboardTopBar />
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  )
}
