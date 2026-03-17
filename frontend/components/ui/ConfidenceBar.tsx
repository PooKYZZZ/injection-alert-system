import { cn } from '@/lib/utils'
import type { AlertPrediction } from '@/features/alerts/contract'

interface ConfidenceBarProps {
  confidence: number
  prediction: AlertPrediction
}

export function ConfidenceBar({ confidence, prediction }: ConfidenceBarProps) {
  const pct = Math.round(confidence * 100)
  const colorClass =
    prediction === 'Normal' ? 'bg-severity-benign-accent' : 'bg-accent-purple'

  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-bg-elevated">
        <div
          className={cn('h-full rounded-full', colorClass)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="w-9 text-right text-xs tabular-nums text-text-secondary">
        {pct}%
      </span>
    </div>
  )
}
