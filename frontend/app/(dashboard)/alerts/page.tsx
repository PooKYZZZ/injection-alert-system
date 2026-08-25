import { Suspense } from 'react'
import { FilterBar } from '@/components/alerts/FilterBar'
import { AlertsPageClientOnly } from '@/components/alerts/AlertsPageClientOnly'
import { getSession } from '@/lib/auth-session'

export default async function AlertsPage() {
  const session = await getSession()

  return (
    <main className="flex flex-col gap-4" style={{ height: 'auto' }}>
      <Suspense fallback={null}>
        <FilterBar />
      </Suspense>
      <AlertsPageClientOnly role={session?.user?.role} />
    </main>
  )
}
