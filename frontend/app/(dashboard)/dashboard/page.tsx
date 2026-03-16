import MetricCards from '@/components/dashboard/MetricCards'
import AlertsTable from '@/components/dashboard/AlertsTable/AlertsTable'
import IncidentDetailPanel from '@/components/dashboard/IncidentDetailPanel'

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-4">

      <MetricCards />

      <AlertsTable />

      <IncidentDetailPanel />

    </div>
  )
}
