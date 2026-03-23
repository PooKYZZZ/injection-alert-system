'use client'

import dynamic from 'next/dynamic'
import { useSearchParams } from 'next/navigation'
import { useState, useCallback } from 'react'
import { QueryErrorResetBoundary } from '@tanstack/react-query'
import MetricCards from '@/components/dashboard/MetricCards'
import HeroActivityStrip from '@/components/dashboard/HeroActivityStrip'
import { useAlerts } from '@/features/alerts/queries'
import { useDashboardStats } from '@/features/stats/queries'
import { useMLHealth } from '@/features/ml-health/queries'
import type { DashboardFilters, SeverityFilter, TimeRange } from '@/lib/searchParams'

const DashboardAlertAnalytics = dynamic(
  () => import('@/components/dashboard/DashboardAlertAnalytics'),
  {
    ssr: false,
    loading: () => (
      <div className="grid gap-4 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div key={index} className="rounded-lg border border-border-light bg-bg-panel p-4 shadow-subtle">
            <div className="mb-4">
              <div className="h-4 w-36 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
              <div className="mt-2 h-3 w-52 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
            </div>
            <div className="space-y-3">
              {Array.from({ length: 4 }).map((_, rowIndex) => (
                <div key={rowIndex} className="grid grid-cols-[minmax(0,160px)_1fr_auto] items-center gap-3">
                  <div className="h-3 w-24 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
                  <div className="h-3 rounded-full bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
                  <div className="h-3 w-8 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
                </div>
              ))}
            </div>
          </div>
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

  // Track actual data source used by hero strip for truthful subtitle
  const [heroStripDbBacked, setHeroStripDbBacked] = useState<boolean>(false)

  // Stats query for metric cards - system-wide stats, not filtered
  const { data: stats, isPending: statsPending, error: statsError } = useDashboardStats()

  // Alerts query for the alerts table - filtered data
  // Note: We intentionally do NOT use fallback here to ensure loading/error states are handled
  // by child components. If data exists but items is undefined, treat as empty array.
  const { data: alertsData, isPending: alertsPending, error: alertsError } = useAlerts(filters)
  const alertsErrorMessage = alertsError instanceof Error ? alertsError : null

  // ML health query for threshold source of truth
  const { data: mlHealthData, isPending: mlHealthPending, isError: mlHealthError, refetch: refetchMlHealth } = useMLHealth()

  // Presentational fallback: only apply when we know data exists but items is missing
  // This is a legitimate presentation fallback, NOT a contract-masking one
  const alerts = alertsData?.items !== undefined ? alertsData.items : []

  // Callback to track actual data source used by hero strip
  const handleHeroDataSourceDetected = useCallback((isDbBacked: boolean) => {
    setHeroStripDbBacked(isDbBacked)
  }, [])

  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <div className="flex flex-col gap-4">
          <MetricCards
            stats={stats}
            statsPending={statsPending}
            statsError={statsError}
            onRetry={reset}
          />
          <div style={{ maxHeight: '56px', overflow: 'hidden' }}>
            <HeroActivityStrip
              activityBuckets={stats?.activity_buckets}
              alerts={alerts}
              isPending={alertsPending}
              onDataSourceDetected={handleHeroDataSourceDetected}
            />
          </div>
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.09em] text-text-muted">
              Security overview
            </span>
            <span className="text-[11px] italic text-text-muted">
              {heroStripDbBacked ? 'Real-time activity from database.' : 'Derived from loaded alerts.'}
            </span>
          </div>
          <DashboardAlertAnalytics
            alerts={alerts}
            alertsPending={alertsPending}
            alertsError={alertsErrorMessage}
            onRetryAlerts={() => window.location.reload()}
            thresholdState={{
              thresholds: mlHealthData?.thresholds ?? null,
              isPending: mlHealthPending,
              isError: mlHealthError,
              onRetry: () => {
                void refetchMlHealth()
              },
            }}
          />
        </div>
      )}
    </QueryErrorResetBoundary>
  )
}

