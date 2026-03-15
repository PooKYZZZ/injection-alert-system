'use client'

import { useDashboardStats } from 'features/stats/queries'
import { cn } from 'lib/utils'

interface MetricCardProps {
  label: string
  icon: string
  value: string | number
  trend: string
  highlight?: boolean
}

function MetricCard({ label, icon, value, trend, highlight }: MetricCardProps) {
  return (
    <div
      className={cn(
        'bg-[#1A1A1A] border border-border-light p-1 rounded-sm shadow-subtle',
        highlight && 'border-t-[2px] border-primary bg-[#1A1A1A]'
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

      <div className="text-xs text-text-muted mt-2">{trend}</div>
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
  const { data, isPending } = useDashboardStats()

  if (isPending) {
    return (
      <div className="grid grid-cols-3 gap-4">
        <MetricCardSkeleton />
        <MetricCardSkeleton />
        <MetricCardSkeleton />
      </div>
    )
  }

  return (
    <div className="grid grid-cols-3 gap-4">

      {/* High Detections */}
      <MetricCard
        label="High Detections"
        icon="gpp_maybe"
        value={formatMetricValue(data?.actionable_alerts)}
        trend="vs. last 24h"
        highlight
      />

      {/* Attack Types Detected */}
     <MetricCard
        label="Attack Types Detected"
        icon="bug_report"
        value="SQLi / XSS"
        trend="Command Injection also detected"
      />

      {/* Total Requests */}
      <MetricCard
        label="Total Requests"
        icon="public"
        // Source: /api/stats -> crs_comparison.total_requests
        value={formatMetricValue(data?.crs_comparison?.total_requests)}
        trend="in last 24h"
      />

    </div>
  )
}
