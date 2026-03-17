import { normalizeSearchParams } from '@/lib/searchParams'
import AlertsTable from '@/components/dashboard/AlertsTable/AlertsTable'
import IncidentDetailPanel from '@/components/dashboard/IncidentDetailPanel'

export default async function AlertsPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>
}) {
  // MUST await searchParams (Next.js 15 Promise-based searchParams)
  const _filters = await normalizeSearchParams(searchParams)

  return (
    <main className="flex flex-col gap-4" style={{ height: 'auto' }}>
      <AlertsTable />
      <IncidentDetailPanel />
    </main>
  )
}
