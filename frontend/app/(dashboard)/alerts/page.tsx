import { Suspense } from 'react'
import { FilterBar } from '@/components/alerts/FilterBar'
import { AlertsPageClientOnly } from '@/components/alerts/AlertsPageClientOnly'
import { PageHeader } from '@/components/layout/PageHeader'
import { getSession } from '@/lib/auth-session'

export default async function AlertsPage() {
  const session = await getSession()

  return (
    <main className="flex flex-col gap-6" style={{ height: 'auto' }}>
      <PageHeader
        title="Alerts"
        description="Review detections, correlate evidence, and record analyst disposition."
      />
      <Suspense fallback={null}>
        <FilterBar />
      </Suspense>
      <AlertsPageClientOnly role={session?.user?.role} />
    </main>
  )
}
