'use client'

import type { CSSProperties } from 'react'
import type { DashboardStats } from '@/features/stats/types'
import { cn } from 'lib/utils'

interface MetricCardsProps {
  stats: DashboardStats | undefined
  statsPending: boolean
  statsError: Error | null
  onRetry?: () => void
}

interface MetricCardProps {
  label: string
  value: string | number
  subtitle?: string
  className?: string
  valueClassName?: string
  style?: CSSProperties
  unavailable?: boolean
}

function MetricCard({
  label,
  value,
  subtitle = 'System-wide',
  className,
  valueClassName,
  style,
  unavailable = false,
}: MetricCardProps) {
  return (
    <div
      className={cn(
        'border border-border-light bg-bg-panel p-4',
        className,
        unavailable && 'opacity-60'
      )}
      style={style}
    >
      <p className="text-label font-semibold uppercase tracking-[0.07em] text-text-muted">
        {label}
      </p>
      <div className={cn('mt-3 text-kpi font-medium leading-none text-text-primary', valueClassName)}>
        {unavailable ? '—' : value}
      </div>
      <p className="mt-3 text-[10px] italic text-text-muted">
        {unavailable ? 'Not available from stats' : subtitle}
      </p>
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

export default function MetricCards({ stats, statsPending, statsError, onRetry }: MetricCardsProps) {
  if (statsPending) {
    return (
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        {Array.from({ length: 5 }).map((_, index) => (
          <MetricCardSkeleton key={index} />
        ))}
      </div>
    )
  }

  if (statsError) {
    return (
      <div className="rounded-lg border border-severity-high-border bg-severity-high-bg p-4">
        <p className="text-sm font-medium text-severity-high-text">Unable to load dashboard metrics.</p>
        <p className="mt-1 text-xs text-text-secondary">{statsError.message}</p>
        {onRetry ? (
          <button
            type="button"
            onClick={onRetry}
            className="mt-3 rounded border border-severity-high-border bg-severity-high-bg px-3 py-1 text-[11px] font-medium text-text-primary transition-colors hover:border-severity-high-accent"
          >
            Retry
          </button>
        ) : null}
      </div>
    )
  }

  if (!stats) {
    return (
      <div className="rounded-lg border border-border-light bg-bg-panel p-4">
        <p className="text-sm font-medium text-text-muted">No stats data available.</p>
      </div>
    )
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
      <MetricCard
        label="High Alerts"
        value={stats.actionable_alerts}
        className="border-l-2 border-l-severity-high-accent bg-severity-high-bg"
        valueClassName="text-severity-high-text"
        style={{ borderRadius: '0 8px 8px 0' }}
      />
      <MetricCard
        label="Blocked"
        value={stats.blocked_count}
        className="rounded-lg"
        valueClassName="text-severity-high-text"
      />
      <MetricCard
        label="Allowed"
        value={stats.allowed_count}
        className="rounded-lg"
        valueClassName="text-severity-medium-text"
      />
      <MetricCard
        label="Avg ML Confidence"
        value={stats.avg_confidence !== null ? `${(stats.avg_confidence * 100).toFixed(0)}%` : '—'}
        unavailable={stats.avg_confidence === null}
        className="rounded-lg"
        valueClassName="text-accent-purple"
      />
      <MetricCard
        label="Total Requests"
        value={stats.total_requests}
        className="rounded-lg"
      />
    </div>
  )
}
