'use client'

import { cn } from '@/lib/utils'
import type { AlertConfidenceTier, AlertPrediction } from '@/features/alerts/contract'

interface ConfidenceTierBadgeProps {
  confidenceTier: AlertConfidenceTier
  prediction?: AlertPrediction
}

const styles: Record<AlertConfidenceTier, string> = {
  HIGH: 'bg-transparent border-severity-high-border/30 text-severity-high-text',
  CRITICAL: 'bg-transparent border-severity-high-border/30 text-severity-high-text',
  MEDIUM: 'bg-transparent border-severity-blocked-border/30 text-severity-blocked-text',
  LOW: 'bg-transparent border-severity-safe-border/30 text-severity-safe-text',
}

export function ConfidenceTierBadge({
  confidenceTier,
}: ConfidenceTierBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium',
        styles[confidenceTier]
      )}
    >
      {confidenceTier}
    </span>
  )
}

export type { ConfidenceTierBadgeProps }
