'use client'

import { useDashboardStats } from 'features/stats/queries'
import { cn } from 'lib/utils'

interface MetricItemProps {
  label: string
  value: string | number
  colorClass?: string
}

function MetricItem({ label, value, colorClass }: MetricItemProps) {
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
        {label}
      </span>
      <span className={cn('text-2xl font-bold', colorClass ?? 'text-text-main')}>
        {value}
      </span>
    </div>
  )
}

function MetricItemSkeleton() {
  return (
    <div className="flex flex-col gap-1">
      <div className="animate-pulse bg-gray-200 rounded h-3 w-28" />
      <div className="animate-pulse bg-gray-200 rounded h-8 w-16 mt-1" />
    </div>
  )
}

export default function CRSComparisonPanel() {
  const { data, isPending } = useDashboardStats()

  return (
    <div className="bg-surface-light border border-border-light rounded-sm shadow-subtle p-4">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
          CRS VS CRS+ML ENFORCEMENT COMPARISON
        </h2>
        <span className="text-[10px] font-medium text-text-muted bg-gray-100 border border-border-light px-2 py-0.5 rounded">
          Baseline: CRS PL2 | Mode: PL2 + ML Triage
        </span>
      </div>

      {isPending ? (
        <div className="grid grid-cols-6 gap-6">
          <MetricItemSkeleton />
          <MetricItemSkeleton />
          <MetricItemSkeleton />
          <MetricItemSkeleton />
          <MetricItemSkeleton />
          <MetricItemSkeleton />
        </div>
      ) : (
        <div className="grid grid-cols-6 gap-6">
          <MetricItem
            label="False Positive Reduction"
            value={
              data
                ? `${data.crs_comparison.false_positive_reduction_pct.toFixed(1)}%`
                : '—'
            }
            colorClass="text-green-600"
          />
          <MetricItem
            label="ML-Gated Blocks"
            value={data?.crs_comparison.ml_confirmed ?? '—'}
          />
          <MetricItem
            label="Precision Gain"
            value={
              data
                ? `${(
                    (data.crs_comparison.ml_confirmed /
                      Math.max(data.crs_comparison.total_crs_flagged, 1)) *
                    100
                  ).toFixed(1)}%`
                : '—'
            }
            colorClass="text-blue-600"
          />
          <MetricItem
            label="Total ML Inferences"
            value={data?.crs_comparison.total_crs_flagged ?? '—'}
          />
          <MetricItem
            label="ML Avg Inference Time"
            value={data ? `${data.crs_comparison.avg_inference_ms}ms` : '—'}
          />
          <MetricItem
            label="CRS Flag Rate"
            value={data
              ? `${((data.crs_comparison.total_crs_flagged / Math.max(data.crs_comparison.total_requests, 1)) * 100).toFixed(1)}%`
              : '—'}
          />
        </div>
      )}
    </div>
  )
}
