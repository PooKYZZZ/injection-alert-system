'use client'

import { getConfidenceLevel } from '@/lib/utils'
import type { AlertConfidenceTier } from '@/features/alerts/contract'
import { formatCompactConfidencePercent, formatConfidenceLabel } from '@/lib/date-time'

interface ConfidenceSummaryProps {
  confidence: number
  confidenceTier?: AlertConfidenceTier
}

export function ConfidenceSummary({
  confidence,
  confidenceTier,
}: ConfidenceSummaryProps) {
  const tier = confidenceTier ?? getConfidenceLevel(confidence)
  const accessibleLabel = formatConfidenceLabel(confidence, tier)

  return (
    <div
      role="group"
      aria-label={`Confidence ${accessibleLabel}`}
      className="inline-flex min-w-0 items-center"
    >
      <span className="inline-flex items-center gap-1 font-mono text-xs leading-5 tabular-nums">
        <span className="text-text-primary">{formatCompactConfidencePercent(confidence)}</span>
        <span aria-hidden="true" className="text-text-muted">·</span>
        <span className="rounded border border-surface-border bg-surface-inset px-1 py-px font-sans text-[10px] font-semibold leading-4 tracking-wide text-text-secondary">
          {tier}
        </span>
      </span>
    </div>
  )
}
