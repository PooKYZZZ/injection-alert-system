'use client'

import { cn } from '@/lib/utils'
import type { AlertPrediction } from '@/features/alerts/contract'

interface SeverityBadgeProps {
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  prediction?: AlertPrediction
}

const styles: Record<'HIGH' | 'MEDIUM' | 'LOW' | 'BENIGN', string> = {
  HIGH: 'bg-transparent border-severity-high-border/30 text-severity-high-text',
  MEDIUM: 'bg-transparent border-severity-blocked-border/30 text-severity-blocked-text',
  LOW: 'bg-transparent border-severity-safe-border/30 text-severity-safe-text',
  BENIGN: 'bg-transparent border-surface-border text-text-secondary',
}

export function SeverityBadge({ severity, prediction }: SeverityBadgeProps) {
  const isBenign = prediction === 'Normal'
  const displaySeverity = isBenign ? 'BENIGN' : severity
  const label = isBenign ? 'Benign' : severity

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full border px-1.5 py-0.5 text-[10px] font-medium',
        styles[displaySeverity]
      )}
    >
      {label}
    </span>
  )
}


