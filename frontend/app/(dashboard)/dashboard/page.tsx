'use client'

import dynamic from 'next/dynamic'
import { useState, useMemo } from 'react'
import Link from 'next/link'
import { motion } from 'motion/react'
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
          <div className="h-32 bg-[#161b22] rounded" />
        </div>
      </div>
    ),
  }
)

// Default filters for dashboard preview
const DEFAULT_DASHBOARD_FILTERS: DashboardFilters = {
  severity: 'ALL',
  timeRange: '24h',
  search: '',
}

export default function DashboardPage() {
  // Time window selector state (display-only until backend supports it)
  const [timeWindow, setTimeWindow] = useState<TimeWindow>('6h')

  // Stats query for dashboard data
  const { data: stats, isPending: statsPending } = useDashboardStats(timeWindow)

  // Alerts query for recent alerts preview
  const { data: alertsData, isPending: alertsPending } = useAlerts(DEFAULT_DASHBOARD_FILTERS)
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

  // Stat card values with honest fallback
  const statCards = [
    {
      label: 'High alerts',
      value: stats?.actionable_alerts ?? '—',
      secondaryColor: 'text-red-400',
      borderColor: 'border-l-red-700',
    },
    {
      label: 'Blocked',
      value: stats?.blocked_count ?? '—',
      secondary:
        stats?.blocked_count != null && stats?.total_requests
          ? `${Math.round((stats.blocked_count / stats.total_requests) * 100)}% block rate`
          : 'Calculating...',
      secondaryColor: 'text-violet-400',
    },
    {
      label: 'Throttled',
      value: stats?.throttled_count ?? '—',
      secondaryColor: 'text-amber-400',
      borderColor: 'border-l-amber-700',
    },
    {
      label: 'Allowed',
      value: stats?.allowed_count ?? '—',
      secondary: 'Benign / LOW conf',
      secondaryColor: 'text-emerald-400',
    },
    {
      label: 'Avg ML confidence',
      value: stats?.avg_confidence != null ? `${Math.round(stats.avg_confidence * 100)}%` : '—',
      secondaryColor: 'text-emerald-400',
    },
    {
      label: 'False Positive Rate',
      value: '—',
      secondary: 'Not available',
      secondaryColor: 'text-[#7d8590]',
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
        {statCards.map((card, index) => (
          <StatCard
            key={card.label}
            label={card.label}
            value={card.value}
            secondary={card.secondary ?? undefined}
            secondaryColor={card.secondaryColor}
            borderColor={card.borderColor}
          />
        ))}
      </div>

      {/* Timeline Panel */}
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, ease: 'easeOut' }}
        className="bg-[#161b22] border border-[#30363d] rounded-lg p-4"
      >
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-3">
            <span className="text-[12px] font-medium text-[#7d8590] uppercase tracking-wider">
              Attack events — last {timeWindow}
            </span>
            <div className="flex gap-1">
              {(['1h', '6h', '24h', '7d'] as TimeWindow[]).map((win) => (
                <button
                  key={win}
                  onClick={() => setTimeWindow(win)}
                  className={cn(
                    'text-[10px] px-2 py-0.5 rounded border transition-all cursor-pointer',
                    timeWindow === win
                      ? 'bg-violet-600 border-violet-500 text-white'
                      : 'bg-[#161b22] border-[#30363d] text-[#7d8590] hover:text-[#e6edf3]'
                  )}
                >
                  {win}
                </button>
              ))}
            </div>
          </div>
          {/* Time window filter applied to stats query */}
          <span className="text-[10px] text-[#484f58]">Hover for details</span>
        </div>
        <TimelineChart
          buckets={stats?.activity_buckets ?? []}
          timeWindow={timeWindow}
          isLoading={statsPending}
        />
      </motion.div>

      {/* Distribution Grid */}
      <div className="grid grid-cols-4 gap-3">
        {/* Attack Type Panel */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.05 }}
          className="bg-[#161b22] border border-[#30363d] rounded-lg p-3.5 flex flex-col gap-2"
        >
          <div className="text-[11px] font-medium text-[#8b949e] uppercase tracking-wider mb-1">
            Attack type dist.
          </div>
          <AttackTypePanel countsByLabel={attackCounts} isLoading={alertsPending} />
        </motion.div>

        {/* ML Confidence Bands + Enforcement Map */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.1 }}
          className="bg-[#161b22] border border-[#30363d] rounded-lg p-3.5 flex flex-col gap-2"
        >
          <div className="text-[11px] font-medium text-[#8b949e] uppercase tracking-wider mb-1">
            ML confidence bands
          </div>
          <MLConfidenceBands
            high={confidenceBands.high}
            medium={confidenceBands.medium}
            low={confidenceBands.low}
            isLoading={alertsPending}
          />

          <div className="mt-4 pt-3 border-t border-[#21262d] flex flex-col gap-2">
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
              isLoading={alertsPending}
            />
          </div>
        </motion.div>

        {/* Top Source IPs */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.15 }}
          className="bg-[#161b22] border border-[#30363d] rounded-lg p-3.5 flex flex-col gap-2"
        >
          <div className="text-[11px] font-medium text-[#8b949e] uppercase tracking-wider mb-1">
            Top source IPs
          </div>
          <TopSourceIPs ips={stats?.top_source_ips ?? []} />
        </motion.div>

        {/* Top Targeted Paths */}
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, ease: 'easeOut', delay: 0.2 }}
          className="bg-[#161b22] border border-[#30363d] rounded-lg p-3.5 flex flex-col gap-2"
        >
          <div className="text-[11px] font-medium text-[#8b949e] uppercase tracking-wider mb-1">
            Top targeted paths
          </div>
          <TopTargetedPaths paths={stats?.top_targeted_paths ?? []} />
        </motion.div>
      </div>

      {/* Recent Alerts Table (Preview) */}
      <RecentAlertsTable alerts={alerts} isLoading={alertsPending} />
    </motion.div>
  )
}
