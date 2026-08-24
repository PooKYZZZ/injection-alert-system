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
import { emptyConfidenceBandCounts } from '@/features/alerts/confidenceBands'
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

interface DashboardQueryErrorProps {
  message: string
  onRetry: () => void
}

function DashboardQueryError({ message, onRetry }: DashboardQueryErrorProps) {
  return (
    <div className="min-w-0 rounded-lg border border-severity-high-border bg-severity-high-bg/30 p-3">
      <ErrorState message={message} onRetry={onRetry} />
    </div>
  )
}

export default function DashboardPage() {
  // The selected window is part of both the stats and recent-preview query keys.
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
    isFetching: statsFetching,
    error: statsError,
    refetch: refetchStats,
  } = useDashboardStats(timeWindow)

  // Alerts query for recent alerts preview
  const {
    data: alertsData,
    isPending: alertsPending,
    isFetching: alertsFetching,
    error: alertsError,
    refetch: refetchAlerts,
  } = useAlerts(dashboardFilters)
  const alerts = useMemo(() => alertsData?.items ?? [], [alertsData?.items])
  const statsUnavailable = statsError != null && stats == null
  const alertsUnavailable = alertsError != null && alertsData == null

  // These distributions come from the complete-window stats aggregate. The
  // alerts query is intentionally only a small recent preview and must not be
  // used as the source for Dashboard totals.
  const attackCounts = stats?.attack_distribution ?? {}
  const allConfidenceBands = stats?.counts_by_confidence_tier ?? emptyConfidenceBandCounts()
  const nonNormalEnforcementBands =
    stats?.non_normal_counts_by_confidence_tier ?? emptyConfidenceBandCounts()

  const summaryWindowTotal = stats?.total_requests ?? 0

  const bucketWindowTotal =
    stats?.activity_buckets.reduce(
      (sum, bucket) => sum + bucket.total_count,
      0
    ) ?? 0

  const bucketActionTotal =
    stats?.activity_buckets.reduce(
      (sum, bucket) => sum + bucket.blocked_count + bucket.throttled_count + bucket.allowed_count,
      0
    ) ?? 0

  const hasTimelineEvents = bucketActionTotal > 0
  const hasWindowDataMismatch = stats != null && summaryWindowTotal !== bucketWindowTotal

  // Stat card values with honest fallback
  const statCards = [
    {
      label: 'Non-Normal alerts',
      value: stats?.high_alert_count ?? '—',
      valueColor: 'text-emerald-500',
      valueFlashColor: 'text-red-200',
      secondary:
        statsUnavailable
          ? 'Unavailable'
          : stats?.high_alert_count === 0
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
        statsUnavailable
          ? 'Unavailable'
          : stats?.blocked_count != null && stats?.total_requests
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
      secondary: statsUnavailable ? 'Unavailable' : 'Benign / LOW conf',
      secondaryColor: 'text-emerald-400',
      previousValue: stats?.prev_allowed_count ?? null,
      deltaInverted: true,
      delay: 0.15,
    },
    {
      label: 'Avg ML confidence',
      value: stats?.avg_confidence != null ? `${Math.round(stats.avg_confidence * 100)}%` : '—',
      secondary:
        statsUnavailable
          ? 'Unavailable'
          : stats?.avg_confidence != null
            ? 'Model stable'
            : 'No traffic in window',
      secondaryColor: 'text-emerald-400',
      delay: 0.2,
    },
    {
      label: 'Allowed non-Normal prediction rate (proxy)',
      value: stats?.false_positive_rate != null ? `${stats.false_positive_rate}%` : '—',
      secondary:
        statsUnavailable
          ? 'Unavailable'
          : stats?.false_positive_rate == null
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
              Request activity — last {timeWindow}
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
                      : 'text-text-muted hover:bg-surface-inset hover:text-text-primary'
                  )}
                >
                  {win}
                </button>
              ))}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span
              role="status"
              aria-live="polite"
              className="text-[10px] text-[var(--color-text-muted)]"
            >
              {statsPending || alertsPending
                ? 'Loading…'
                : statsFetching || alertsFetching
                  ? 'Updating…'
                  : `Showing ${timeWindow} window`}
            </span>
            <span className="hidden text-[10px] text-[var(--color-text-muted)] sm:inline">
              Hover for details
            </span>
          </div>
        </div>
        <div
          role="list"
          aria-label="Activity series"
          className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-[10px] text-[var(--color-text-secondary)]"
        >
          {[
            ['Blocked', 'bg-severity-high-accent'],
            ['Throttled', 'bg-severity-blocked-accent'],
            ['Allowed', 'bg-severity-safe-accent'],
          ].map(([label, colorClass]) => (
            <span key={label} role="listitem" className="inline-flex items-center gap-1.5">
              <span aria-hidden="true" className={cn('h-1.5 w-1.5 rounded-full', colorClass)} />
              {label}
            </span>
          ))}
        </div>
        {statsUnavailable ? (
          <div className="flex h-[140px] items-center justify-center">
            <p className="text-[11px] text-[var(--color-text-secondary)]">Timeline unavailable</p>
          </div>
        ) : (
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
        )}
      </motion.div>

      {statsError ? (
        <DashboardQueryError
          message={
            statsUnavailable
              ? 'Dashboard metrics are unavailable. Try again.'
              : 'Dashboard metrics refresh failed. Showing the last successful data.'
          }
          onRetry={() => void refetchStats()}
        />
      ) : null}

      {/* Distribution Grid */}
      <div className="grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 xl:grid-cols-4">
        {!statsUnavailable ? (
          <>
            {/* Attack Type Panel */}
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, ease: 'easeOut', delay: 0.05 }}
              className="min-w-0 rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] p-3.5 flex flex-col gap-2"
            >
              <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
                Attack type distribution
              </div>
              <AttackTypePanel countsByLabel={attackCounts} isPending={statsPending} />
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
                isPending={statsPending}
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
                  isPending={statsPending}
                />
              </div>
            </motion.div>
          </>
        ) : null}

        {!statsUnavailable ? (
          <>
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
          </>
        ) : null}
      </div>

      {alertsError ? (
        <DashboardQueryError
          message={
            alertsUnavailable
              ? 'Alert data is unavailable. Try again.'
              : 'Alert data refresh failed. Showing the last successful data.'
          }
          onRetry={() => void refetchAlerts()}
        />
      ) : null}

      {/* Recent Alerts Table (Preview) */}
      {alertsUnavailable ? null : <RecentAlertsTable alerts={alerts} isPending={alertsPending} />}
    </motion.div>
  )
}
