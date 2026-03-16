'use client'

import { useDashboardStats } from 'features/stats/queries'
import { cn } from 'lib/utils'

interface MetricCardProps {
  label: string
  icon: string
  value: string | number
  detail: string
  highlight?: boolean
}

function MetricCard({ label, icon, value, detail, highlight }: MetricCardProps) {
  return (
    <div
      className={cn(
        'bg-surface-light border border-border-light p-1 rounded-sm shadow-subtle',
        highlight && 'border-t-[2px] border-primary bg-surface-light'
      )}
    >
      <div className="flex justify-between items-start mb-2">
        <span className="text-[12px] font-semibold text-text-muted uppercase tracking-wider">
          {label}
        </span>
        <span className="material-symbols-outlined text-text-muted text-[20px]">
          {icon}
        </span>
      </div>

      <div className="text-3xl font-bold text-text-main">{value}</div>

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

export default function MetricCards() {
  const { data, isPending, isError, error } = useDashboardStats()
  const avgInferenceLatency =
    data?.avg_inference_latency_ms === null || data?.avg_inference_latency_ms === undefined
      ? 'Unavailable with current response'
      : `${data.avg_inference_latency_ms} ms`

  if (isPending) {
    return (
      <div className="grid grid-cols-3 gap-4">
        <MetricCardSkeleton />
        <MetricCardSkeleton />
        <MetricCardSkeleton />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-sm border border-status-high/50 bg-status-high/10 p-4">
        <p className="text-sm font-medium text-status-high">Failed to load dashboard stats</p>
        <p className="mt-1 text-xs text-text-muted">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="rounded-sm border border-border-light bg-surface-light p-4">
        <p className="text-sm text-text-muted">No data available</p>
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-4">

      {/* Actionable Alerts */}
      <MetricCard
        label="Actionable Alerts"
        icon="gpp_maybe"
        value={formatMetricValue(data.actionable_alerts)}
        detail="Derived from attack-labeled requests in current stats response"
        highlight
      />

      {/* Average Inference Latency */}
      <MetricCard
        label="Avg Inference Latency"
        icon="speed"
        value={avgInferenceLatency}
        detail="Backend average model latency (ms)"
      />

      {/* Total Requests */}
      <MetricCard
        label="Total Requests"
        icon="public"
        value={formatMetricValue(data.total_requests)}
        detail="All requests in current stats response"
      />
    </div>
  )
}
