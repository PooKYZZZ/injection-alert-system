import MetricCards from '@/components/dashboard/MetricCards'
import CRSComparisonPanel from '@/components/dashboard/CRSComparisonPanel'
import AlertBanner from '@/components/dashboard/AlertBanner'
import AlertsTable from '@/components/dashboard/AlertsTable/AlertsTable'
import AttackDistribution from '@/components/dashboard/AttackDistribution'
import ConfidenceHistogram from '@/components/dashboard/ConfidenceHistogram'
import IncidentDetailPanel from '@/components/dashboard/IncidentDetailPanel'

const ATTACK_DISTRIBUTION = [
  { label: 'SQL Injection', pct: 42.3, colorClass: 'bg-red-500' },
  { label: 'XSS', pct: 28.1, colorClass: 'bg-orange-400' },
  { label: 'Path Traversal', pct: 14.7, colorClass: 'bg-yellow-400' },
  { label: 'Command Injection', pct: 9.6, colorClass: 'bg-purple-500' },
  { label: 'Other', pct: 5.3, colorClass: 'bg-gray-400' },
]

const CONFIDENCE_BINS = [
  { label: '0–20%', count: 12, pct: 8, colorClass: 'bg-gray-300' },
  { label: '20–40%', count: 18, pct: 12, colorClass: 'bg-yellow-300' },
  { label: '40–60%', count: 24, pct: 16, colorClass: 'bg-yellow-400' },
  { label: '60–80%', count: 47, pct: 32, colorClass: 'bg-orange-400' },
  { label: '80–100%', count: 47, pct: 47, colorClass: 'bg-red-500' },
]

export default function DashboardPage() {
  return (
    <div className="flex flex-col gap-4">
      <AlertBanner
        variant="error"
        message="Critical: 3 high-confidence SQL injection attempts detected in the last hour."
        detail="Source IPs have been flagged for immediate review."
      />

      <MetricCards />

      <CRSComparisonPanel />

      <AlertBanner
        variant="warning"
        message="Warning: ML model confidence has dropped below 70% for 12% of recent requests."
        detail="Consider reviewing the retraining schedule."
      />

      <AlertsTable />

      <div className="grid grid-cols-2 gap-4">
        <AttackDistribution distribution={ATTACK_DISTRIBUTION} />
        <ConfidenceHistogram bins={CONFIDENCE_BINS} />
      </div>

      <IncidentDetailPanel />
    </div>
  )
}
