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
import { useDashboardStats } from '@/features/stats/queries'
import { useAlerts } from '@/features/alerts/queries'
import type { DashboardFilters } from '@/lib/searchParams'
import type { AlertPrediction } from '@/features/alerts/contract'
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
      severity: 'ALL',
      timeRange: timeWindow,
      search: '',
    }),
    [timeWindow]
  )

  // Stats query for dashboard data
  const { data: stats, isPending: statsPending } = useDashboardStats(timeWindow)

  // Alerts query for recent alerts preview
  const { data: alertsData, isPending: alertsPending } = useAlerts(dashboardFilters)
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

  // Calculate confidence bands from alerts
  const confidenceBands = useMemo(() => {
    let high = 0
    let medium = 0
    let low = 0
    for (const alert of alerts) {
      const confPercent = alert.confidence * 100
      if (confPercent > 80) {
        high += 1
      } else if (confPercent >= 50) {
        medium += 1
      } else {
        low += 1
      }
    }
    return { high, medium, low }
  }, [alerts])

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
        label: 'High alerts',
        value: stats?.actionable_alerts ?? '—',
      secondary:
        stats?.actionable_alerts === 0
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
      label: 'False Positive Rate',
      value: stats?.false_positive_rate != null ? `${stats.false_positive_rate}%` : '—',
        secondary:
          stats?.false_positive_rate == null
            ? 'No data'
            : stats.false_positive_rate > 0
              ? 'Of total requests'
              : 'Clean window',
        secondaryColor: 'text-[var(--color-text-secondary)]',
        delay: 0.25,
      },
  ]

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
      className="flex flex-col gap-3 p-4"
    >
      {/* Stats Row */}
      <div className="grid grid-cols-6 gap-2">
        {statCards.map((card) => (
            <StatCard
              key={card.label}
              label={card.label}
              value={card.value}
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
        className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-4"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="text-[12px] font-medium text-[var(--color-text-secondary)] uppercase tracking-wider">
              Attack events — last {timeWindow}
            </span>
            <div className="flex gap-1">
              {(['1h', '6h', '24h', '7d'] as TimeWindow[]).map((win) => (
                <button
                  key={win}
                  onClick={() => setTimeWindow(win)}
                className={cn(
                    'rounded px-3 py-1 text-xs font-medium transition-colors',
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
          <span className="text-[10px] text-[var(--color-text-muted)]">Hover for details</span>
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

      {/* Distribution Grid */}
      <div className="grid grid-cols-4 gap-3">
        {/* Attack Type Panel */}
        <motion.div
          key={`attack-type-${timeWindow}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.05 }}
          className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-3.5 flex flex-col gap-2"
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
            Attack type dist.
          </div>
          <AttackTypePanel countsByLabel={attackCounts} isPending={alertsPending} />
        </motion.div>

        {/* ML Confidence Bands + Enforcement Map */}
        <motion.div
          key={`ml-confidence-${timeWindow}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.1 }}
          className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-3.5 flex flex-col gap-2"
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
            ML confidence bands
          </div>
            <MLConfidenceBands
              high={confidenceBands.high}
              medium={confidenceBands.medium}
              low={confidenceBands.low}
              isPending={alertsPending}
            />

          <div className="mt-4 pt-3 border-t border-[var(--color-text-ghost)] flex flex-col gap-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-bold text-violet-400 uppercase tracking-widest">
                ML Enforcement Map
              </span>
              <div className="h-1 w-8 bg-violet-500/30 rounded-full overflow-hidden">
                <div className="h-full bg-violet-500 w-2/3" />
              </div>
            </div>
            <MLEnforcementMap
              high={confidenceBands.high}
              medium={confidenceBands.medium}
              low={confidenceBands.low}
              isPending={alertsPending}
            />
          </div>
        </motion.div>

        {/* Top Source IPs */}
        <motion.div
          key={`source-ips-${timeWindow}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.15 }}
          className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-3.5 flex flex-col gap-2"
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
            Top source IPs
          </div>
          <TopSourceIPs ips={stats?.top_source_ips ?? []} isPending={statsPending} />
        </motion.div>

        {/* Top Targeted Paths */}
        <motion.div
          key={`targeted-paths-${timeWindow}`}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.2 }}
          className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-3.5 flex flex-col gap-2"
        >
          <div className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
            Top targeted paths
          </div>
          <TopTargetedPaths paths={stats?.top_targeted_paths ?? []} isPending={statsPending} />
        </motion.div>
      </div>

      {/* Recent Alerts Table (Preview) */}
      <RecentAlertsTable alerts={alerts} isPending={alertsPending} />
    </motion.div>
  )
}
