import MetricCards from '@/components/dashboard/MetricCards'
import AlertsTable from '@/components/dashboard/AlertsTable/AlertsTable'
import DashboardAlertAnalyticsSection from '@/components/dashboard/DashboardAlertAnalyticsSection'
import IncidentDetailPanel from '@/components/dashboard/IncidentDetailPanel'

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-4">
      <DashboardAlertAnalyticsSection />
      <AlertsTable />
      <IncidentDetailPanel />
    </div>
  )
}
