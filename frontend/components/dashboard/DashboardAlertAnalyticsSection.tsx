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
      <div className="flex flex-col gap-4">
        <div className="h-3 w-52 animate-pulse rounded-sm bg-border-light" />
        <div className="grid gap-4 xl:grid-cols-2">
          {Array.from({ length: 4 }).map((_, index) => (
            <div
              key={index}
              className="rounded-sm border border-border-light bg-surface-light p-4 shadow-subtle"
            >
              <div className="mb-4">
                <div className="h-4 w-36 animate-pulse rounded-sm bg-border-light" />
                <div className="mt-2 h-3 w-52 animate-pulse rounded-sm bg-border-light" />
              </div>
              <div className="space-y-3">
                {Array.from({ length: 4 }).map((_, rowIndex) => (
                  <div
                    key={rowIndex}
                    className="grid grid-cols-[minmax(0,160px)_1fr_auto] items-center gap-3"
                  >
                    <div className="h-3 w-24 animate-pulse rounded-sm bg-border-light" />
                    <div className="h-3 animate-pulse rounded-full bg-border-light" />
                    <div className="h-3 w-8 animate-pulse rounded-sm bg-border-light" />
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
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
