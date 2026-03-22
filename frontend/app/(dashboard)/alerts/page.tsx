import { Suspense } from 'react'
import { FilterBar } from '@/components/alerts/FilterBar'
import { AlertsPageClient } from '@/components/alerts/AlertsPageClient'

export default function AlertsPage() {
  return (
    <main className="flex flex-col gap-4" style={{ height: 'auto' }}>
      <Suspense fallback={null}>
        <FilterBar />
      </Suspense>
      <AlertsPageClient />
    </main>
  )
}
