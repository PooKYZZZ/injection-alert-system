import { Suspense } from 'react'
import { FilterBar } from '@/components/alerts/FilterBar'
import { AlertsPageClientOnly } from '@/components/alerts/AlertsPageClientOnly'

export default function AlertsPage() {
  return (
    <main className="alerts-page-compact flex flex-col gap-4" style={{ height: 'auto' }}>
      <Suspense fallback={null}>
        <FilterBar />
      </Suspense>
      <AlertsPageClientOnly />
    </main>
  )
}
