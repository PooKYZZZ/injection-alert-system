import MetricCards from '@/components/dashboard/MetricCards'
import AlertsTable from '@/components/dashboard/AlertsTable/AlertsTable'
import AttackDistribution from '@/components/dashboard/AttackDistribution'
import IncidentDetailPanel from '@/components/dashboard/IncidentDetailPanel'

const ATTACK_DISTRIBUTION = [
  { label: 'SQL Injection', pct: 42.3, colorClass: 'bg-red-500' },
  { label: 'XSS', pct: 28.1, colorClass: 'bg-orange-400' },
  { label: 'Command Injection', pct: 9.6, colorClass: 'bg-purple-500' },
]

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-4">

      <MetricCards />

      <AlertsTable />

      <div className="grid grid-cols-2 gap-4">
        <AttackDistribution distribution={ATTACK_DISTRIBUTION} />
      </div>

      <IncidentDetailPanel />

    </div>
  )
}