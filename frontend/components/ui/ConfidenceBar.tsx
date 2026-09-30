'use client'

import { cn, getConfidenceLevel } from '@/lib/utils'
import type { AlertConfidenceTier, AlertPrediction } from '@/features/alerts/contract'
import { formatConfidenceLabel } from '@/lib/date-time'

interface ConfidenceBarProps {
  confidence: number
  confidenceTier?: AlertConfidenceTier
  prediction: AlertPrediction
}

export function getConfidenceColors(
  confidence: number,
  confidenceTier?: AlertConfidenceTier
): { text: string; bg: string } {
  const tier = confidenceTier ?? getConfidenceLevel(confidence)
  if (tier === 'CRITICAL' || tier === 'HIGH') {
    return { text: 'text-severity-high-text', bg: 'bg-severity-high-accent' }
  }
  if (tier === 'MEDIUM') {
    return { text: 'text-severity-blocked-text', bg: 'bg-severity-blocked-accent' }
  }
  if (tier === 'LOW') {
    return { text: 'text-severity-safe-text', bg: 'bg-severity-safe-accent' }
  }

  return { text: 'text-text-secondary', bg: 'bg-surface-border' }
}

export function ConfidenceBar({
  confidence,
  confidenceTier,
  prediction: _prediction,
}: ConfidenceBarProps) {
  const normalizedConfidence = Math.min(Math.max(confidence, 0), 1)
  const value = normalizedConfidence * 100
  const colors = getConfidenceColors(confidence, confidenceTier)

  return (
    <div className="flex items-center gap-2">
      <span className={cn('min-w-[32px] font-medium', colors.text)}>
        {formatConfidenceLabel(confidence, confidenceTier ?? getConfidenceLevel(confidence))}
      </span>
      <div className="h-1 w-12 overflow-hidden rounded-full bg-surface-inset">
        <div
          className={cn('h-full', colors.bg)}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}
