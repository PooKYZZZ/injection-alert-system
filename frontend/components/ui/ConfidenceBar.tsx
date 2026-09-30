'use client'

import { getConfidenceLevel } from '@/lib/utils'
import type { AlertConfidenceTier, AlertPrediction } from '@/features/alerts/contract'
import { formatCompactConfidencePercent, formatConfidenceLabel } from '@/lib/date-time'

interface ConfidenceBarProps {
  confidence: number
  confidenceTier?: AlertConfidenceTier
  prediction: AlertPrediction
}

export function ConfidenceBar({
  confidence,
  confidenceTier,
  prediction: _prediction,
}: ConfidenceBarProps) {
  const normalizedConfidence = Math.min(Math.max(confidence, 0), 1)
  const value = normalizedConfidence * 100
  const tier = confidenceTier ?? getConfidenceLevel(confidence)
  const accessibleLabel = formatConfidenceLabel(confidence, tier)

  return (
    <div
      role="group"
      aria-label={`Confidence ${accessibleLabel}`}
      className="flex items-center gap-2"
    >
      <span className="inline-flex items-center gap-1 font-mono text-xs leading-5 tabular-nums">
        <span className="text-text-primary">{formatCompactConfidencePercent(confidence)}</span>
        <span aria-hidden="true" className="text-text-muted">·</span>
        <span className="rounded border border-surface-border bg-surface-inset px-1 py-px font-sans text-[10px] font-semibold leading-4 tracking-wide text-text-secondary">
          {tier}
        </span>
      </span>
      <div aria-hidden="true" className="h-1 w-12 shrink-0 overflow-hidden rounded-full bg-surface-inset">
        <div
          className="h-full bg-accent-analytic"
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}
