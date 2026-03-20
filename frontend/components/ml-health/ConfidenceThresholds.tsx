'use client'

import { cn } from '@/lib/utils'
import { EmptyState } from '@/components/ui/StateViews'

interface ConfidenceThresholdsProps {
  thresholds: { low: number | null; medium: number | null; high: number | null }
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

  if (low === null || high === null) {
    return <EmptyState message="Threshold data unavailable" />
  }

  // Calculate width percentages based on the 0-100 scale
  const lowWidth = low
  const mediumWidth = high - low
  const highWidth = 100 - high

  return (
    <>
      <div className="text-[10px] text-[var(--color-text-muted)] mb-2">
        How ML confidence maps to enforcement actions
      </div>
      <div className="relative h-8 bg-[var(--color-bg-inset)] rounded-md overflow-hidden flex">
        <div
          className="h-full bg-[#0f2d1a] text-emerald-400 flex items-center justify-center text-[10px] font-medium"
          style={{ width: `${lowWidth}%` }}
        >
          {`Low < ${low}%`}
        </div>
        <div
          className="h-full bg-[#2d2310] text-amber-400 flex items-center justify-center text-[10px] font-medium border-l border-[var(--color-bg-inset)]"
          style={{ width: `${mediumWidth}%` }}
        >
          {`Med ${low}%–${high}%`}
        </div>
        <div
          className="h-full bg-[#2d1b1b] text-red-400 flex items-center justify-center text-[10px] font-medium border-l border-[var(--color-bg-inset)]"
          style={{ width: `${highWidth}%` }}
        >
          {`High > ${high}%`}
        </div>
      </div>
      <div className="flex gap-4 mt-2 text-[10px]">
        <LegendItem color="bg-emerald-500" label="Allow" />
        <LegendItem color="bg-amber-500" label="Throttle" />
        <LegendItem color="bg-red-500" label="Block" />
      </div>
      <div className="mt-3 text-[10px] text-[var(--color-text-muted)]">
        {`Enforcement thresholds: HIGH > 80%, MEDIUM 50–80%, LOW < 50% per policy.`}
      </div>
    </>
  )
}
