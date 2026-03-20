import { Suspense } from 'react'
import { normalizeAlertSearchParams } from '@/lib/searchParams'
import { getAlerts } from '@/lib/bff-client'
import { FilterBar } from '@/components/alerts/FilterBar'
import { AlertsPageClient } from '@/components/alerts/AlertsPageClient'

export default async function AlertsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  const params = await searchParams
  const filters = normalizeAlertSearchParams(params)

  const urlParams = new URLSearchParams()

  for (const [key, value] of Object.entries(filters)) {
    if (value === undefined || value === null) continue

    if (key === 'confidence_level' && Array.isArray(value)) {
      for (const entry of value) urlParams.append(key, String(entry))
      continue
    }

    urlParams.set(key, String(value))
  }

  const result = await getAlerts(urlParams)
  const filteredCount = result.ok ? result.data.total : undefined

  return (
    <main className="flex flex-col gap-4" style={{ height: 'auto' }}>
      <Suspense fallback={null}>
        <FilterBar filteredCount={filteredCount} />
      </Suspense>
      <AlertsPageClient />
    </main>
  )
}
