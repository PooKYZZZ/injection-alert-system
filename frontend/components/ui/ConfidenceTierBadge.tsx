'use client'

import { cn } from '@/lib/utils'
import type { AlertConfidenceTier, AlertPrediction } from '@/features/alerts/contract'

interface ConfidenceTierBadgeProps {
  confidenceTier: AlertConfidenceTier
  prediction?: AlertPrediction
}

const styles: Record<AlertConfidenceTier | 'BENIGN', string> = {
  HIGH: 'bg-transparent border-severity-high-border/30 text-severity-high-text',
  CRITICAL: 'bg-transparent border-severity-high-border/30 text-severity-high-text',
  MEDIUM: 'bg-transparent border-severity-blocked-border/30 text-severity-blocked-text',
  LOW: 'bg-transparent border-severity-safe-border/30 text-severity-safe-text',
  BENIGN: 'bg-transparent border-surface-border text-text-secondary',
}

export function ConfidenceTierBadge({
  confidenceTier,
  prediction,
}: ConfidenceTierBadgeProps) {
  const isBenign = prediction === 'Normal'
  const displayConfidenceTier = isBenign ? 'BENIGN' : confidenceTier
  const label = isBenign ? 'Benign' : confidenceTier

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium',
        styles[displayConfidenceTier]
      )}
    >
      {label}
    </span>
  )
}

export type { ConfidenceTierBadgeProps }
