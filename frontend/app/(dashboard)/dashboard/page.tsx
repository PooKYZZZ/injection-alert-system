'use client'

import dynamic from 'next/dynamic'
import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { AnimatePresence, motion } from 'motion/react'
import { cn } from '@/lib/utils'
import { StatCard } from '@/components/dashboard/StatCard'
import { AttackTypePanel } from '@/components/dashboard/AttackTypePanel'
import { MLConfidenceBands } from '@/components/dashboard/MLConfidenceBands'
import { TopSourceIPs } from '@/components/dashboard/TopSourceIPs'
import { TopTargetedPaths } from '@/components/dashboard/TopTargetedPaths'
import { RecentAlertsTable } from '@/components/dashboard/RecentAlertsTable'
import { PageHeader } from '@/components/layout/PageHeader'
import { ErrorState } from '@/components/ui/StateViews'
import { useDashboardStats } from '@/features/stats/queries'
import { useAlerts } from '@/features/alerts/queries'
import type { DashboardFilters } from '@/lib/searchParams'
import type { TimeWindow } from '@/components/dashboard/TimelineChart'
import { formatConfidencePercent } from '@/lib/date-time'
import { getCurrentSearchParams } from '@/lib/searchParams'

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

const TIME_WINDOWS: TimeWindow[] = ['1h', '6h', '24h', '7d']
const TIME_WINDOW_LABELS: Record<TimeWindow, string> = {
  '1h': '1 hour',
  '6h': '6 hours',
  '24h': '24 hours',
  '7d': '7 days',
}

function parseTimeWindow(value: string | null): TimeWindow {
  return value && TIME_WINDOWS.includes(value as TimeWindow) ? (value as TimeWindow) : '6h'
}

function DashboardQueryError({ message, onRetry }: DashboardQueryErrorProps) {
  return (
    <div className="min-w-0 rounded-lg border border-severity-high-border bg-severity-high-bg/30 p-3">
      <ErrorState message={message} onRetry={onRetry} />
    </div>
  )
}

export default function DashboardPage() {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const urlTimeWindow = parseTimeWindow(
    searchParams.get('window') ?? searchParams.get('timeRange')
  )

  // Keep the URL canonical while updating the control immediately on click.
  // The URL remains the source of truth after navigation or reload.
  const [timeWindow, setTimeWindow] = useState<TimeWindow>(urlTimeWindow)
  useEffect(() => {
    setTimeWindow(urlTimeWindow)
  }, [urlTimeWindow])

  const handleTimeWindowChange = useCallback((next: TimeWindow) => {
    setTimeWindow(next)
    const params = getCurrentSearchParams(searchParams)
    params.set('window', next)
    params.delete('timeRange')
    const query = params.toString()
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
  }, [pathname, router, searchParams])

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
  const allConfidenceBands = stats?.counts_by_confidence_tier ?? null

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
  const hasDistributionData =
    summaryWindowTotal > 0 ||
    Object.keys(attackCounts).length > 0 ||
    Object.values(allConfidenceBands ?? {}).some((count) => count > 0) ||
    (stats?.top_source_ips.length ?? 0) > 0 ||
    (stats?.top_targeted_paths.length ?? 0) > 0

  // Stat card values with honest fallback
  const statCards = [
    {
      label: 'Non-Normal predictions',
      value: stats?.high_alert_count ?? '—',
      valueColor: 'text-text-primary',
      valueFlashColor: 'text-red-200',
      secondary:
        statsUnavailable
          ? 'Unavailable'
          : stats?.high_alert_count === 0
            ? timeWindow
              ? 'No threats in this window'
              : 'No threats detected'
            : undefined,
      secondaryColor: 'text-text-secondary',
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
      secondary: statsUnavailable ? 'Unavailable' : 'Normal or LOW-confidence requests',
      secondaryColor: 'text-emerald-400',
      previousValue: stats?.prev_allowed_count ?? null,
      deltaInverted: true,
      delay: 0.15,
    },
  ]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="min-w-0 flex flex-col gap-6"
    >
      <PageHeader
        title="Dashboard"
        description="Review request activity, detection volume, and enforcement outcomes for the selected window."
      />

      {/* Summary metrics */}
      <div className="grid min-w-0 grid-cols-1 divide-y divide-surface-border overflow-hidden rounded-lg border border-border-light bg-surface-panel sm:grid-cols-2 sm:divide-y-0 xl:grid-cols-4 xl:divide-x xl:divide-y-0">
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
            hideDeltaWhenValueZero={card.hideDeltaWhenValueZero}
            delay={card.delay}
          />
        ))}
      </div>

      <dl className="flex flex-wrap items-baseline gap-x-6 gap-y-2 text-sm">
        <div className="flex items-baseline gap-2">
          <dt className="text-text-secondary">Average model confidence</dt>
          <dd className="font-medium tabular-nums text-text-primary">{formatConfidencePercent(stats?.avg_confidence)}</dd>
          <span className="text-xs text-text-muted">not attack severity</span>
        </div>
        <div className="flex items-baseline gap-2">
          <dt className="text-text-secondary">Allowed non-Normal rate</dt>
          <dd className="font-medium tabular-nums text-text-primary">
            {stats?.false_positive_rate != null ? `${stats.false_positive_rate}%` : '—'}
          </dd>
          <span className="text-xs text-text-muted">operational proxy, not ground-truth FPR</span>
        </div>
      </dl>

      {/* Timeline Panel */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="min-w-0 rounded-lg border border-border-light bg-surface-panel p-3 sm:p-4"
      >
        <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
            <h2 className="min-w-0 text-base font-semibold text-text-primary">Request activity</h2>
            <div className="flex shrink-0 gap-1" role="group" aria-label="Timeline window">
              {TIME_WINDOWS.map((win) => (
                <button
                  key={win}
                  type="button"
                  aria-label={TIME_WINDOW_LABELS[win]}
                  aria-pressed={timeWindow === win}
                  onClick={() => handleTimeWindowChange(win)}
                  className={cn(
                    'rounded px-2.5 py-1 text-xs font-medium transition-colors',
                    'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-1 focus-visible:ring-offset-[var(--color-bg-panel)]',
                    timeWindow === win
                      ? 'bg-violet-500/10 text-violet-400 ring-1 ring-inset ring-violet-500/30'
                      : 'text-text-muted hover:bg-surface-inset hover:text-text-primary'
                  )}
                >
                  {TIME_WINDOW_LABELS[win]}
                </button>
              ))}
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <span
              role="status"
              aria-live="polite"
              className="text-xs text-text-muted"
            >
              {statsPending || alertsPending
                ? 'Loading…'
                : statsFetching || alertsFetching
                  ? 'Updating…'
                  : null}
            </span>
            <span className="hidden text-xs text-text-muted sm:inline">
              Rolling window · ending now
            </span>
          </div>
        </div>
        {hasTimelineEvents && !statsUnavailable ? (
          <div
            role="list"
            aria-label="Activity series"
            className="mb-2 flex flex-wrap gap-x-4 gap-y-1 text-xs text-text-secondary"
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
        ) : null}
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

      {/* Window detail */}
      {!statsUnavailable && hasDistributionData ? (
        <div className="grid min-w-0 grid-cols-1 divide-y divide-border-light overflow-hidden rounded-lg border border-border-light bg-surface-panel md:grid-cols-2 md:divide-x md:divide-y-0">
          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut', delay: 0.05 }}
            className="min-w-0 flex flex-col gap-2 p-4"
          >
            <h2 className="mb-2 text-sm font-semibold text-text-primary">Attack type distribution</h2>
            <AttackTypePanel countsByLabel={attackCounts} isPending={statsPending} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut', delay: 0.1 }}
            className="min-w-0 flex flex-col gap-2 p-4"
          >
            <h2 className="mb-2 text-sm font-semibold text-text-primary">Model confidence</h2>
            <MLConfidenceBands
              critical={allConfidenceBands?.critical ?? 0}
              high={allConfidenceBands?.high ?? 0}
              medium={allConfidenceBands?.medium ?? 0}
              low={allConfidenceBands?.low ?? 0}
              isPending={statsPending}
              unavailable={allConfidenceBands == null}
            />
            <p className="mt-3 text-xs leading-5 text-text-muted">
              Enforcement thresholds are maintained with the active model.
              <Link href="/ml-health" className="ml-1 text-text-secondary underline decoration-border-light underline-offset-2 hover:text-text-primary">
                Review ML Health
              </Link>
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut', delay: 0.15 }}
            className="min-w-0 flex flex-col gap-2 p-4"
          >
            <h2 className="mb-2 text-sm font-semibold text-text-primary">Top source IPs</h2>
            <TopSourceIPs ips={stats?.top_source_ips ?? []} isPending={statsPending} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, ease: 'easeOut', delay: 0.2 }}
            className="min-w-0 flex flex-col gap-2 p-4"
          >
            <h2 className="mb-2 text-sm font-semibold text-text-primary">Top targeted paths</h2>
            <TopTargetedPaths paths={stats?.top_targeted_paths ?? []} isPending={statsPending} />
          </motion.div>
        </div>
      ) : !statsUnavailable && statsPending ? (
        <section className="rounded-lg border border-border-light bg-surface-panel p-4" aria-label="Window detail loading">
          <p className="text-sm text-text-secondary">Loading window detail…</p>
        </section>
      ) : !statsUnavailable ? (
        <section className="rounded-lg border border-border-light bg-surface-panel px-4 py-5" aria-label="Window detail">
          <h2 className="text-sm font-semibold text-text-primary">Window detail</h2>
          <p className="mt-1 max-w-2xl text-sm leading-6 text-text-secondary">
            No traffic was reported in this window. Detailed distributions will appear when activity is available.
          </p>
        </section>
      ) : null}

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
