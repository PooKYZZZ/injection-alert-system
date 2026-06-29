'use client'

import { cn } from '@/lib/utils'
import { EmptyState } from '@/components/ui/StateViews'

interface ConfidenceThresholdsProps {
  thresholds: { low: number | null; medium: number | null; high: number | null; critical: number | null }
}

function LegendItem({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <div className={cn('w-2 h-2 rounded-sm', color)} />
      <span className="text-[var(--color-text-secondary)] text-[10px]">{label}</span>
    </div>
  )
}

// Thresholds are stored 0–1 in backend, display as 0–100
function toPercent(value: number | null): number | null {
  if (value === null) return null
  return value <= 1 ? Math.round(value * 100) : value
}

export function ConfidenceThresholds({ thresholds }: ConfidenceThresholdsProps) {
  const low = toPercent(thresholds.low)
  const high = toPercent(thresholds.high)
  const critical = toPercent(thresholds.critical)

  if (
    low === null ||
    high === null ||
    critical === null ||
    low < 0 ||
    low >= high ||
    high >= critical ||
    critical > 100
  ) {
    return <EmptyState message="Threshold data not configured" />
  }

  // Calculate width percentages based on the 0-100 scale
  const lowWidth = low
  const mediumWidth = high - low
  const highWidth = critical - high
  const criticalWidth = 100 - critical

  return (
    <>
      <div className="text-[10px] text-[var(--color-text-muted)] mb-2">
        Configured confidence thresholds for non-Normal enforcement policy
      </div>
      <div className="relative h-8 bg-[var(--color-bg-inset)] rounded-md overflow-hidden flex">
        <div
          className="h-full bg-[var(--color-severity-safe-bg)] text-emerald-400 flex items-center justify-center text-[10px] font-medium"
          style={{ width: `${lowWidth}%` }}
        >
          {`Low <${low}%`}
        </div>
        <div
          className="h-full bg-[var(--color-severity-blocked-bg)] text-amber-400 flex items-center justify-center text-[10px] font-medium border-l border-[var(--color-bg-inset)]"
          style={{ width: `${mediumWidth}%` }}
        >
          {`Medium ${low}%–${high}%`}
        </div>
        <div
          className="h-full bg-[var(--color-severity-high-bg)] text-red-400 flex items-center justify-center text-[10px] font-medium border-l border-[var(--color-bg-inset)]"
          style={{ width: `${highWidth}%` }}
        >
          {`High >${high}%–<${critical}%`}
        </div>
        <div
          className="h-full bg-[var(--color-severity-high-bg)] text-red-400 flex items-center justify-center text-[10px] font-medium border-l border-[var(--color-bg-inset)]"
          style={{ width: `${criticalWidth}%` }}
        >
          {`Critical >=${critical}%`}
        </div>
      </div>
      <div className="flex gap-4 mt-2 text-[10px]">
        <LegendItem color="bg-emerald-500" label="Allow" />
        <LegendItem color="bg-amber-500" label="Throttle" />
        <LegendItem color="bg-red-500" label="Block" />
      </div>
      <div className="mt-3 text-[10px] text-[var(--color-text-muted)]">
        Normal predictions remain allowed for all valid confidence tiers.
      </div>
    </>
  )
}
