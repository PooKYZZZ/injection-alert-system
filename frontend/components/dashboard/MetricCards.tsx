'use client'

import type { CSSProperties } from 'react'
import { useMemo } from 'react'
import type { Alert } from 'features/alerts/types'
import { cn } from 'lib/utils'

interface MetricCardsProps {
  alerts: Alert[]
  alertsPending: boolean
  alertsError?: Error | null
}

interface MetricCardProps {
  label: string
  value: string | number
  subtitle?: string
  className?: string
  valueClassName?: string
  style?: CSSProperties
}

function MetricCard({ label, value, subtitle = 'Loaded records', className, valueClassName, style }: MetricCardProps) {
  return (
    <div
      className={cn(
        'rounded-r-lg rounded-l-none border border-border-light bg-bg-panel p-4',
        className
      )}
      style={style}
    >
      <p className="text-label font-semibold uppercase tracking-[0.07em] text-text-muted">
        {label}
      </p>
      <div className={cn('mt-3 text-kpi font-medium leading-none text-text-primary', valueClassName)}>
        {value}
      </div>
      <p className="mt-3 text-[10px] italic text-text-muted">{subtitle}</p>
    </div>
  )
}

function MetricCardSkeleton() {
  return (
    <div className="rounded-lg bg-bg-elevated p-4" aria-hidden="true">
      <div className="h-2.5 w-20 rounded-sm bg-bg-panel [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
      <div className="mt-4 h-8 w-16 rounded-sm bg-bg-panel [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
      <div className="mt-4 h-2.5 w-24 rounded-sm bg-bg-panel [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
    </div>
  )
}

export default function MetricCards({ alerts, alertsPending, alertsError }: MetricCardsProps) {
  const metrics = useMemo(() => {
    const highAlerts = alerts.filter((alert) => alert.confidence_level === 'HIGH').length
    const blocked = alerts.filter((alert) => alert.action_taken === 'BLOCKED').length
    const allowed = alerts.filter((alert) => alert.action_taken === 'ALLOWED').length
    const totalRequests = alerts.length
    const avgConfidenceValue =
      alerts.length > 0
        ? (alerts.reduce((sum, alert) => sum + alert.confidence, 0) / alerts.length) * 100
        : 0

    return {
      highAlerts,
      blocked,
      allowed,
      avgConfidence: alerts.length > 0 ? `${avgConfidenceValue.toFixed(1)}%` : '—',
      totalRequests,
    }
  }, [alerts])

  if (alertsPending) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <MetricCardSkeleton key={index} />
        ))}
      </div>
    )
  }

  if (alertsError) {
    return (
      <div className="rounded-lg border border-severity-high-border bg-severity-high-bg p-4">
        <p className="text-sm font-medium text-severity-high-text">Unable to load dashboard metrics.</p>
        <p className="mt-1 text-xs text-text-secondary">{alertsError.message}</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      <MetricCard
        label="High Alerts"
        value={metrics.highAlerts}
        className="border-l-2 border-l-severity-high-accent bg-severity-high-bg"
        valueClassName="text-severity-high-text"
        style={{ borderRadius: '0 8px 8px 0' }}
      />
      <MetricCard
        label="Blocked"
        value={metrics.blocked}
        className="border-l-2 border-l-severity-blocked-accent bg-severity-blocked-bg"
        valueClassName="text-severity-blocked-text"
        style={{ borderRadius: '0 8px 8px 0' }}
      />
      <MetricCard label="Allowed" value={metrics.allowed} />
      <MetricCard
        label="Avg ML Confidence"
        value={metrics.avgConfidence}
        valueClassName="text-accent-purple"
      />
      <MetricCard label="Total Requests" value={metrics.totalRequests} />
    </div>
  )
}
