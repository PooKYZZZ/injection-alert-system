'use client'

import { cn } from '@/lib/utils'
import type { AlertPrediction } from '@/features/alerts/contract'

interface ConfidenceBarProps {
  confidence: number
  prediction: AlertPrediction
}

function getConfidenceColors(confidence: number): { text: string; bg: string } {
  const value = Math.round(confidence * 100)
  if (value >= 80) return { text: 'text-violet-400', bg: 'bg-violet-600' }
  if (value >= 50) return { text: 'text-amber-400', bg: 'bg-amber-600' }
  return { text: 'text-emerald-400', bg: 'bg-emerald-600' }
}

export function ConfidenceBar({ confidence, prediction: _prediction }: ConfidenceBarProps) {
  const value = Math.round(confidence * 100)
  const colors = getConfidenceColors(confidence)

  return (
    <div className="flex items-center gap-2">
      <span className={cn('min-w-[32px] font-medium', colors.text)}>
        {value}%
      </span>
      <div className="h-1 w-12 overflow-hidden rounded-full bg-[var(--color-bg-base)]">
        <div
          className={cn('h-full', colors.bg)}
          style={{ width: `${value}%` }}
        />
      </div>
    </div>
  )
}

