'use client'

import { cn } from '@/lib/utils'
import type { AlertPrediction } from '@/features/alerts/contract'

interface SeverityBadgeProps {
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  prediction?: AlertPrediction
}

const styles: Record<string, string> = {
  HIGH: 'bg-[#2d1b1b] text-red-400',
  MEDIUM: 'bg-[#2d2310] text-amber-400',
  LOW: 'bg-[#1a2b1a] text-emerald-400',
  BENIGN: 'bg-[#1c1c2e] text-[#6b7280]',
}

export function SeverityBadge({ severity, prediction }: SeverityBadgeProps) {
  const isBenign = prediction === 'Normal'
  const displaySeverity = isBenign ? 'BENIGN' : severity
  const label = isBenign ? 'Benign' : severity

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium',
        styles[displaySeverity]
      )}
    >
      {label}
    </span>
  )
}
