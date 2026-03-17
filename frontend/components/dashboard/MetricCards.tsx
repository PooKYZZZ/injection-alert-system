'use client'

import { useMemo } from 'react'
import { useDashboardStats } from 'features/stats/queries'
import type { Alert } from 'features/alerts/types'
import { cn } from 'lib/utils'

interface MetricCardProps {
  label: string
  icon: string
  value: string | number
  detail: string
  accent?: 'urgent' | 'blocked'
}

interface MetricCardsProps {
  alerts: Alert[]
  alertsPending: boolean
  alertsError?: Error | null
}

function MetricCard({ label, icon, value, detail, accent }: MetricCardProps) {
  return (
    <div
      className={cn(
        'rounded-sm border border-border-light bg-surface-light p-4 shadow-subtle',
        accent === 'urgent' && 'border-l-[3px] border-l-status-high',
        accent === 'blocked' && 'border-l-[3px] border-l-status-medium'
      )}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-text-muted">
          {label}
        </span>
        <span className="material-symbols-outlined text-text-muted text-[20px]">
          {icon}
        </span>
      </div>

      <div className="text-4xl font-extrabold leading-none text-text-main">{value}</div>

      <div className="text-xs text-text-muted mt-2">{detail}</div>
    </div>
  )
}

function MetricCardSkeleton() {
  return (
    <div className="bg-surface-light border border-border-light p-4 rounded-sm shadow-subtle">
      <div className="flex justify-between items-start mb-2">
        <div className="animate-pulse bg-gray-200 rounded h-3 w-24" />
        <div className="animate-pulse bg-gray-200 rounded h-5 w-5" />
      </div>
      <div className="animate-pulse bg-gray-200 rounded h-9 w-20 mt-1" />
      <div className="animate-pulse bg-gray-200 rounded h-3 w-28 mt-2" />
    </div>
  )
}

function formatMetricValue(value: string | number | null | undefined): string | number {
  return value ?? 'N/A'
}

function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'N/A'
  }

  return `${(value * 100).toFixed(1)}%`
}

export default function MetricCards({ alerts, alertsPending, alertsError }: MetricCardsProps) {
  const {
    data: stats,
    isPending: statsPending,
    isError: statsError,
    error: statsQueryError,
  } = useDashboardStats()

  const alertMetrics = useMemo(() => {
    const highSeverityAlerts = alerts.filter((alert) => alert.confidence_level === 'HIGH').length
    const blockedAlerts = alerts.filter((alert) => alert.action_taken === 'BLOCKED').length
    const allowedAlerts = alerts.filter((alert) => alert.action_taken === 'ALLOWED').length
    const avgConfidence =
      alerts.length > 0
        ? alerts.reduce((sum, alert) => sum + alert.confidence, 0) / alerts.length
        : null

    return {
      highSeverityAlerts,
      blockedAlerts,
      allowedAlerts,
      avgConfidence,
      loadedAlertCount: alerts.length,
    }
  }, [alerts])

  if (statsPending || alertsPending) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <MetricCardSkeleton />
        <MetricCardSkeleton />
        <MetricCardSkeleton />
        <MetricCardSkeleton />
        <MetricCardSkeleton />
      </div>
    )
  }

  if (statsError || alertsError) {
    const error = statsQueryError ?? alertsError
    return (
      <div className="rounded-sm border border-status-high/50 bg-status-high/10 p-4">
        <p className="text-sm font-medium text-status-high">Failed to load dashboard metrics</p>
        <p className="mt-1 text-xs text-text-muted">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="rounded-sm border border-border-light bg-surface-light p-4">
        <p className="text-sm text-text-muted">No data available</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      <MetricCard
        label="High Severity Alerts"
        icon="gpp_maybe"
        value={formatMetricValue(alertMetrics.highSeverityAlerts)}
        detail={`From ${alertMetrics.loadedAlertCount} loaded alerts in the current view`}
        accent="urgent"
      />
      <MetricCard
        label="Blocked"
        icon="block"
        value={formatMetricValue(alertMetrics.blockedAlerts)}
        detail="Blocked actions in the current loaded alert set"
        accent="blocked"
      />
      <MetricCard
        label="Allowed"
        icon="check_circle"
        value={formatMetricValue(alertMetrics.allowedAlerts)}
        detail="Allowed actions in the current loaded alert set"
      />
      <MetricCard
        label="Avg ML Confidence"
        icon="network_intelligence"
        value={formatPercent(alertMetrics.avgConfidence)}
        detail="Average confidence across the current loaded alert set"
      />
      <MetricCard
        label="Total Requests"
        icon="public"
        value={formatMetricValue(stats.total_requests)}
        detail="All requests in the current stats response"
      />
    </div>
  )
}
