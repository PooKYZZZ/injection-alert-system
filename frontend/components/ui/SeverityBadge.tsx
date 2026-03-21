'use client'

import { cn } from '@/lib/utils'
import type { AlertPrediction } from '@/features/alerts/contract'

interface SeverityBadgeProps {
  severity: 'HIGH' | 'MEDIUM' | 'LOW'
  prediction?: AlertPrediction
}

const styles: Record<string, string> = {
  HIGH: 'bg-transparent border border-red-500/30 text-red-400',
  MEDIUM: 'bg-transparent border border-amber-500/30 text-amber-400',
  LOW: 'bg-transparent border border-emerald-500/30 text-emerald-400',
  BENIGN: 'bg-transparent border border-[#30363d] text-[#7d8590]',
}

export function SeverityBadge({ severity, prediction }: SeverityBadgeProps) {
  const isBenign = prediction === 'Normal'
  const displaySeverity = isBenign ? 'BENIGN' : severity
  const label = isBenign ? 'Benign' : severity

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium border',
        styles[displaySeverity]
      )}
    >
      {label}
    </span>
  )
}
