'use client'

import dynamic from 'next/dynamic'
import { useSearchParams } from 'next/navigation'
import MetricCards from '@/components/dashboard/MetricCards'
import { useAlerts } from '@/features/alerts/queries'
import type { DashboardFilters, SeverityFilter, TimeRange } from '@/lib/searchParams'

const DashboardAlertAnalytics = dynamic(
  () => import('@/components/dashboard/DashboardAlertAnalytics'),
  {
    ssr: false,
    loading: () => (
      <div className="grid gap-4 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-72 animate-pulse rounded-sm border border-border-light bg-surface-light shadow-subtle"
          />
        ))}
      </div>
    ),
  }
)

function buildFilters(searchParams: Pick<URLSearchParams, 'get'> | null): DashboardFilters {
  return {
    severity: (searchParams?.get('severity') ?? 'ALL') as SeverityFilter,
    timeRange: (searchParams?.get('timeRange') ?? '24h') as TimeRange,
    search: searchParams?.get('search') ?? '',
  }
}

export default function DashboardAlertAnalyticsSection() {
  const searchParams = useSearchParams()
  const filters = buildFilters(searchParams)
  const { data, isPending, error } = useAlerts(filters)
  const alerts = data?.items ?? []
  const alertsError = error instanceof Error ? error : null

  return (
    <>
      <MetricCards alerts={alerts} alertsPending={isPending} alertsError={alertsError} />
      <DashboardAlertAnalytics
        alerts={alerts}
        alertsPending={isPending}
        alertsError={alertsError}
      />
    </>
  )
}
