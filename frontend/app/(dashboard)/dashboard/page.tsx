'use client'

import dynamic from 'next/dynamic'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { AnimatePresence, motion } from 'motion/react'
import { ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import { StatCard } from '@/components/dashboard/StatCard'
import { AttackTypePanel } from '@/components/dashboard/AttackTypePanel'
import { MLConfidenceBands } from '@/components/dashboard/MLConfidenceBands'
import { MLEnforcementMap } from '@/components/dashboard/MLEnforcementMap'
import { TopSourceIPs } from '@/components/dashboard/TopSourceIPs'
import { TopTargetedPaths } from '@/components/dashboard/TopTargetedPaths'
import { RecentAlertsTable } from '@/components/dashboard/RecentAlertsTable'
import { PageHeader } from '@/components/layout/PageHeader'
import { ErrorState } from '@/components/ui/StateViews'
import { InfoDisclosure } from '@/components/ui/InfoDisclosure'
import { useDashboardStats } from '@/features/stats/queries'
import { useAlerts } from '@/features/alerts/queries'
import type { DashboardFilters } from '@/lib/searchParams'
import { emptyConfidenceBandCounts } from '@/features/alerts/confidenceBands'
import type { TimeWindow } from '@/components/dashboard/TimelineChart'
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
  const nonNormalEnforcementBands = stats?.non_normal_counts_by_confidence_tier ?? null

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
  const statCards: Array<{
    label: string
    info?: string
    value: string | number
    secondary?: string
    secondaryColor?: string
    previousValue?: number | null
    progressBar?: number
    hideDeltaWhenValueZero?: boolean
    delay?: number
  }> = [
    {
      label: 'Actionable detections',
      info: 'Counts persisted records with an actionable attack classification in this window. It is a record count, not a confirmed incident count.',
      value: stats?.high_alert_count ?? '—',
      secondary:
        statsUnavailable
          ? 'Unavailable'
          : stats?.high_alert_count === 0
            ? 'No actionable detections in this window'
            : undefined,
      secondaryColor: 'text-text-secondary',
      previousValue: stats?.prev_high_alert_count ?? null,
      hideDeltaWhenValueZero: true,
      delay: 0,
    },
    {
      label: 'Recorded blocked',
      info: 'Counts records whose stored action label is BLOCKED. This does not confirm that a WAF blocked the request or establish the observed HTTP outcome.',
      value: stats?.blocked_count ?? '—',
      secondary: statsUnavailable ? 'Unavailable' : undefined,
      secondaryColor: 'text-text-secondary',
      previousValue: stats?.prev_blocked_count ?? null,
      delay: 0.05,
    },
    {
      label: 'Recorded throttled',
      value: stats?.throttled_count ?? '—',
      secondaryColor: 'text-text-secondary',
      previousValue: stats?.prev_throttled_count ?? null,
      delay: 0.1,
    },
    {
      label: 'Traffic records',
      info: 'Counts stored traffic-log rows for this window. A single request may produce multiple related records.',
      value: stats?.total_requests ?? '—',
      secondary: statsUnavailable ? 'Unavailable' : undefined,
      secondaryColor: 'text-text-secondary',
      previousValue: stats?.prev_total_requests ?? null,
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
        description="Overview of recent security activity for the selected window."
      />

      {/* Summary metrics */}
      <div className="grid min-w-0 grid-cols-2 overflow-hidden rounded-lg border border-border-light bg-surface-panel [&>*:nth-child(odd)]:border-r [&>*:nth-child(odd)]:border-surface-border [&>*:nth-child(-n+2)]:border-b [&>*:nth-child(-n+2)]:border-surface-border xl:grid-cols-4 xl:[&>*:nth-child(-n+3)]:border-r xl:[&>*:nth-child(-n+3)]:border-surface-border xl:[&>*:nth-child(-n+2)]:border-b-0">
        {statCards.map((card) => (
          <StatCard
            key={card.label}
            label={card.label}
            info={card.info}
            value={card.value}
            secondary={card.secondary ?? undefined}
            secondaryColor={card.secondaryColor}
            previousValue={card.previousValue}
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
        className="min-w-0 rounded-lg border border-border-light bg-surface-panel p-3 sm:p-4"
      >
        <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
          <div className="flex min-w-0 flex-1 flex-wrap items-center gap-3">
            <div className="flex items-center gap-2">
              <h2 className="min-w-0 text-base font-semibold text-text-primary">Recorded actions over time</h2>
              <InfoDisclosure label="Recorded actions">
                These series count stored BLOCKED, THROTTLED, and ALLOWED action labels. They do not prove the HTTP outcome or identify which system enforced a request.
              </InfoDisclosure>
            </div>
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
                      ? 'bg-action-bg text-action-accent ring-1 ring-inset ring-action-border'
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
              ['Recorded blocked', 'bg-severity-high-accent'],
              ['Recorded throttled', 'bg-severity-blocked-accent'],
              ['Recorded allowed', 'bg-severity-safe-accent'],
            ].map(([label, colorClass]) => (
              <span key={label} role="listitem" className="inline-flex items-center gap-1.5">
                <span aria-hidden="true" className={cn('h-1.5 w-1.5 rounded-full', colorClass)} />
                {label}
              </span>
            ))}
          </div>
        ) : null}
        {hasWindowDataMismatch ? (
          <p role="status" className="mb-2 text-xs leading-5 text-text-muted">
            Counts may differ briefly while activity updates.
          </p>
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

      {alertsError ? (
        <DashboardQueryError
          message={
            alertsUnavailable
              ? 'Detection data is unavailable. Try again.'
              : 'Detection data refresh failed. Showing the last successful data.'
          }
          onRetry={() => void refetchAlerts()}
        />
      ) : null}

      {/* Recent detection preview */}
      {alertsUnavailable ? null : <RecentAlertsTable alerts={alerts} isPending={alertsPending} />}

      {/* Secondary analytics follow the recent-event preview in the scan order. */}
      {!statsUnavailable ? (
        <details className="group min-w-0 rounded-lg border border-border-light bg-surface-panel">
          <summary className="flex cursor-pointer list-none items-center justify-between gap-4 rounded-lg px-4 py-3 transition-colors hover:bg-surface-inset focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 [&::-webkit-details-marker]:hidden">
            <span className="min-w-0">
              <span role="heading" aria-level={2} className="block text-sm font-semibold text-text-primary">
                Attack and model breakdown
              </span>
              <span className="mt-1 block text-xs font-normal leading-5 text-text-secondary">
                Attack types, confidence, policy, top sources and paths
              </span>
            </span>
            <ChevronDown
              aria-hidden="true"
              size={16}
              className="shrink-0 text-text-muted transition-transform group-open:rotate-180"
            />
          </summary>
          <div className="space-y-5 border-t border-border-light p-4">
            {!statsUnavailable && hasDistributionData ? (
              <>
                <section aria-labelledby="dashboard-traffic-patterns" className="min-w-0 space-y-3">
                  <h2 id="dashboard-traffic-patterns" className="text-sm font-semibold text-text-primary">
                    Traffic patterns
                  </h2>
                  <div className="grid min-w-0 grid-cols-1 gap-px overflow-hidden rounded-lg border border-border-light bg-border-light md:grid-cols-2 xl:grid-cols-3">
                    <section className="min-w-0 bg-surface-panel p-4">
                      <h3 className="mb-3 text-sm font-medium text-text-primary">Attack types</h3>
                      <AttackTypePanel countsByLabel={attackCounts} isPending={statsPending} />
                    </section>
                    <section className="min-w-0 bg-surface-panel p-4">
                      <h3 className="mb-3 text-sm font-medium text-text-primary">Top source IPs</h3>
                      <TopSourceIPs ips={stats?.top_source_ips ?? []} isPending={statsPending} />
                    </section>
                    <section className="min-w-0 bg-surface-panel p-4">
                      <h3 className="mb-3 text-sm font-medium text-text-primary">Top targeted paths</h3>
                      <TopTargetedPaths paths={stats?.top_targeted_paths ?? []} isPending={statsPending} />
                    </section>
                  </div>
                </section>

                <section aria-labelledby="dashboard-model-context" className="min-w-0 space-y-3 border-t border-border-light pt-5">
                  <h2 id="dashboard-model-context" className="text-sm font-semibold text-text-primary">
                    Model and policy context
                  </h2>
                  <div className="grid min-w-0 grid-cols-1 items-start gap-3 md:grid-cols-2">
                    <div className="min-w-0 rounded-lg border border-border-light bg-surface-panel p-4">
                      <div className="mb-3 flex items-center gap-2">
                        <h3 className="text-sm font-medium text-text-primary">Confidence by tier</h3>
                        <InfoDisclosure label="Confidence">
                          Confidence indicates how strongly the model supports its predicted classification. It does not represent attack severity.
                        </InfoDisclosure>
                      </div>
                      <MLConfidenceBands
                        critical={allConfidenceBands?.critical ?? 0}
                        high={allConfidenceBands?.high ?? 0}
                        medium={allConfidenceBands?.medium ?? 0}
                        low={allConfidenceBands?.low ?? 0}
                        informational={allConfidenceBands?.informational ?? 0}
                        isPending={statsPending}
                        unavailable={allConfidenceBands == null}
                      />
                    </div>
                    <div className="min-w-0 rounded-lg border border-border-light bg-surface-panel p-4">
                      <h3 className="mb-3 text-sm font-medium text-text-primary">Policy by confidence tier</h3>
                      <MLEnforcementMap
                        nonNormalCounts={nonNormalEnforcementBands ?? emptyConfidenceBandCounts()}
                        isPending={statsPending}
                        unavailable={nonNormalEnforcementBands == null}
                      />
                    </div>
                  </div>
                </section>
              </>
            ) : statsPending ? (
              <section aria-label="Breakdown loading">
                <p className="text-sm text-text-secondary">Loading activity breakdown…</p>
              </section>
            ) : !statsUnavailable ? (
              <section aria-label="Activity breakdown">
                <h2 className="text-sm font-semibold text-text-primary">No activity in this time window</h2>
                <p className="mt-1 max-w-2xl text-sm leading-6 text-text-secondary">
                  Traffic summaries will appear when activity is available for the selected window.
                </p>
              </section>
            ) : null}
          </div>
        </details>
      ) : null}
    </motion.div>
  )
}
