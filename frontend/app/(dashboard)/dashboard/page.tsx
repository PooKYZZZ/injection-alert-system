'use client'

import dynamic from 'next/dynamic'
import { useState, useMemo } from 'react'
import { AnimatePresence, motion } from 'motion/react'
import { cn } from '@/lib/utils'
import { StatCard } from '@/components/dashboard/StatCard'
import { AttackTypePanel } from '@/components/dashboard/AttackTypePanel'
import { MLConfidenceBands } from '@/components/dashboard/MLConfidenceBands'
import { MLEnforcementMap } from '@/components/dashboard/MLEnforcementMap'
import { TopSourceIPs } from '@/components/dashboard/TopSourceIPs'
import { TopTargetedPaths } from '@/components/dashboard/TopTargetedPaths'
import { RecentAlertsTable } from '@/components/dashboard/RecentAlertsTable'
import { ErrorState } from '@/components/ui/StateViews'
import { useDashboardStats } from '@/features/stats/queries'
import { useAlerts } from '@/features/alerts/queries'
import type { DashboardFilters } from '@/lib/searchParams'
import type { AlertPrediction } from '@/features/alerts/contract'
import { countAlertsByConfidenceTier } from '@/features/alerts/confidenceBands'
import type { TimeWindow } from '@/components/dashboard/TimelineChart'

// Lazy-load TimelineChart to avoid SSR hydration issues and reduce initial bundle
const TimelineChart = dynamic(
  () => import('@/components/dashboard/TimelineChart').then((m) => m.TimelineChart),
  {
    ssr: false,
    loading: () => (
      <div className="h-48 flex items-center justify-center">
        <div className="animate-pulse flex flex-col gap-2 w-full">
          <div className="h-32 bg-[var(--color-bg-panel)] rounded" />
        </div>
      </div>
    ),
  }
)

export default function DashboardPage() {
  // Time window selector state (display-only until backend supports it)
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('6h')

  const dashboardFilters = useMemo<DashboardFilters>(
    () => ({
      confidenceTier: 'ALL',
      timeRange: timeWindow,
      search: '',
    }),
    [timeWindow]
  )

  // Stats query for dashboard data
  const {
    data: stats,
    isPending: statsPending,
    error: statsError,
    refetch: refetchStats,
  } = useDashboardStats(timeWindow)

  // Alerts query for recent alerts preview
  const {
    data: alertsData,
    isPending: alertsPending,
    error: alertsError,
    refetch: refetchAlerts,
  } = useAlerts(dashboardFilters)
  const alerts = useMemo(() => alertsData?.items ?? [], [alertsData?.items])

  // Calculate attack type distribution from alerts
  const attackCounts = useMemo(() => {
    const counts: Partial<Record<AlertPrediction, number>> = {}
    for (const alert of alerts) {
      const prediction = alert.prediction
      counts[prediction] = (counts[prediction] ?? 0) + 1
    }
    return counts
  }, [alerts])

  const allConfidenceBands = useMemo(
    () => countAlertsByConfidenceTier(alerts),
    [alerts]
  )
  const nonNormalEnforcementBands = useMemo(
    () => countAlertsByConfidenceTier(alerts, { nonNormalOnly: true }),
    [alerts]
  )

  const summaryWindowTotal =
    (stats?.blocked_count ?? 0) +
    (stats?.throttled_count ?? 0) +
    (stats?.allowed_count ?? 0)

  const bucketWindowTotal =
    stats?.activity_buckets.reduce(
      (sum, bucket) => sum + bucket.blocked_count + bucket.throttled_count + bucket.allowed_count,
      0
    ) ?? 0

  const hasTimelineEvents = bucketWindowTotal > 0
  const hasWindowDataMismatch = stats != null && summaryWindowTotal !== bucketWindowTotal

  // Stat card values with honest fallback
  const statCards = [
      {
        label: 'High-confidence alerts',
        value: stats?.high_alert_count ?? '—',
      valueColor: 'text-emerald-500',
      valueFlashColor: 'text-red-200',
      secondary:
        stats?.high_alert_count === 0
          ? timeWindow
            ? 'No threats in this window'
            : 'No threats detected'
          : undefined,
        secondaryColor: 'text-red-400',
        previousValue: stats?.prev_high_alert_count ?? null,
        hideDeltaWhenValueZero: true,
        delay: 0,
    },
    {
      label: 'Blocked',
      value: stats?.blocked_count ?? '—',
        valueColor: 'text-red-500',
        valueFlashColor: 'text-red-200',
        secondary:
          stats?.blocked_count != null && stats?.total_requests
            ? `${Math.round((stats.blocked_count / stats.total_requests) * 100)}% block rate`
            : 'No traffic in window',
        secondaryColor: 'text-violet-400',
        previousValue: stats?.prev_blocked_count ?? null,
        progressBar:
          stats?.total_requests && stats.total_requests > 0
          ? (stats.blocked_count / stats.total_requests) * 100
          : undefined,
      delay: 0.05,
    },
    {
      label: 'Throttled',
        value: stats?.throttled_count ?? '—',
        valueColor: 'text-amber-400',
        valueFlashColor: 'text-amber-200',
        secondaryColor: 'text-amber-400',
        previousValue: stats?.prev_throttled_count ?? null,
        delay: 0.1,
      },
    {
      label: 'Allowed',
      value: stats?.allowed_count ?? '—',
        secondary: 'Benign / LOW conf',
        secondaryColor: 'text-emerald-400',
        previousValue: stats?.prev_allowed_count ?? null,
        deltaInverted: true,
        delay: 0.15,
    },
    {
      label: 'Avg ML confidence',
        value: stats?.avg_confidence != null ? `${Math.round(stats.avg_confidence * 100)}%` : '—',
        secondary:
          stats?.avg_confidence != null ? 'Model stable' : 'No traffic in window',
        secondaryColor: 'text-emerald-400',
        delay: 0.2,
      },
    {
      label: 'Allowed non-Normal prediction rate (proxy)',
      value: stats?.false_positive_rate != null ? `${stats.false_positive_rate}%` : '—',
        secondary:
          stats?.false_positive_rate == null
            ? 'No telemetry in window'
            : 'Not ground-truth FPR',
        secondaryColor: 'text-[var(--color-text-secondary)]',
        delay: 0.25,
      },
  ]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="min-w-0 flex flex-col gap-3 p-3 sm:p-4"
    >
      {/* Stats Row */}
      <div className="grid min-w-0 grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {statCards.map((card) => (
            <StatCard
              key={card.label}
              label={card.label}
              value={card.value}
              valueColor={card.valueColor}
              valueFlashColor={card.valueFlashColor}
              secondary={card.secondary ?? undefined}
              secondaryColor={card.secondaryColor}
              previousValue={card.previousValue}
              deltaInverted={card.deltaInverted}
              progressBar={card.progressBar}
            hideDeltaWhenValueZero={card.hideDeltaWhenValueZero}
            delay={card.delay}
          />
        ))}
      </div>

      {/* Timeline Panel */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="min-w-0 rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] p-3 sm:p-4"
      >
        <div className="mb-3 flex flex-wrap items-start justify-between gap-2">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-2 sm:gap-3">
            <span className="min-w-0 text-[12px] font-medium uppercase tracking-wider text-[var(--color-text-secondary)]">
              Attack events — last {timeWindow}
            </span>
            <div className="flex shrink-0 gap-1" role="group" aria-label="Timeline window">
              {(['1h', '6h', '24h', '7d'] as TimeWindow[]).map((win) => (
                <button
                  key={win}
                  type="button"
                  aria-pressed={timeWindow === win}
                  onClick={() => setTimeWindow(win)}
                  className={cn(
                    'rounded px-3 py-1 text-xs font-medium transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--color-bg-panel)]',
                    timeWindow === win
                      ? 'bg-violet-500/10 text-violet-400 ring-1 ring-inset ring-violet-500/30'
                      : 'text-[#7d8590] hover:bg-[#1e2a3d]/50 hover:text-[#e6edf3]'
                  )}
                >
                  {win}
                </button>
              ))}
            </div>
          </div>
          {/* Time window filter applied to stats query */}
          <span className="hidden shrink-0 text-[10px] text-[var(--color-text-muted)] sm:inline">Hover for details</span>
        </div>
        <AnimatePresence mode="wait">
          <motion.div
            key={timeWindow}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
          >
            <TimelineChart
              buckets={stats?.activity_buckets ?? []}
              timeWindow={timeWindow}
              isPending={statsPending}
              hasEvents={hasTimelineEvents}
              consistencyWarning={
                hasWindowDataMismatch
                  ? 'Window totals are being recalculated. Timeline data may be briefly out of sync.'
                  : null
              }
            />
          </motion.div>
        </AnimatePresence>
      </motion.div>

      {statsError ? (
        <div className="min-w-0 rounded-lg border border-severity-high-border bg-severity-high-bg/30 p-3">
          <ErrorState
            message="Dashboard metrics are unavailable. Try again."
            onRetry={() => void refetchStats()}
          />
        </div>
      ) : null}

      {/* Distribution Grid */}
      <div className="grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {/* Attack Type Panel */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.05 }}
          className="min-w-0 rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] p-3.5 flex flex-col gap-2"
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
            Attack type dist.
          </div>
          <AttackTypePanel countsByLabel={attackCounts} isPending={alertsPending} />
        </motion.div>

        {/* ML Confidence Bands + Enforcement Map */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.1 }}
          className="min-w-0 rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] p-3.5 flex flex-col gap-2"
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
            ML confidence bands
          </div>
            <MLConfidenceBands
              critical={allConfidenceBands.critical}
              high={allConfidenceBands.high}
              medium={allConfidenceBands.medium}
              low={allConfidenceBands.low}
              isPending={alertsPending}
            />

          <div className="mt-4 min-w-0 border-t border-[var(--color-text-ghost)] pt-3 flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-violet-400 uppercase tracking-widest">
                ML Enforcement Map
              </span>
              <div className="h-1 w-8 bg-violet-500/30 rounded-full overflow-hidden">
                <div className="h-full bg-violet-500 w-2/3" />
              </div>
            </div>
            <MLEnforcementMap
              nonNormalCounts={nonNormalEnforcementBands}
              isPending={alertsPending}
            />
          </div>
        </motion.div>

        {/* Top Source IPs */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.15 }}
          className="min-w-0 rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] p-3.5 flex flex-col gap-2"
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
            Top source IPs
          </div>
          <TopSourceIPs ips={stats?.top_source_ips ?? []} isPending={statsPending} />
        </motion.div>

        {/* Top Targeted Paths */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.2 }}
          className="min-w-0 rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] p-3.5 flex flex-col gap-2"
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
            Top targeted paths
          </div>
          <TopTargetedPaths paths={stats?.top_targeted_paths ?? []} isPending={statsPending} />
        </motion.div>
      </div>

      {alertsError ? (
        <div className="min-w-0 rounded-lg border border-severity-high-border bg-severity-high-bg/30 p-3">
          <ErrorState
            message="Alert data is unavailable. Try again."
            onRetry={() => void refetchAlerts()}
          />
        </div>
      ) : null}

      {/* Recent Alerts Table (Preview) */}
      <RecentAlertsTable alerts={alerts} isPending={alertsPending} />
    </motion.div>
  )
}
