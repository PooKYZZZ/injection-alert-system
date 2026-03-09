import { cn, getConfidenceLevel } from '@/lib/utils'

interface ConfidenceBarProps {
  confidence: number
}

const levelColorClass: Record<string, string> = {
  HIGH:   'bg-status-high',
  MEDIUM: 'bg-status-medium',
  LOW:    'bg-status-ratelimited',
}

export function ConfidenceBar({ confidence }: ConfidenceBarProps) {
  const pct = Math.round(confidence * 100)
  const level = getConfidenceLevel(confidence)
  const colorClass = levelColorClass[level]

  return (
    <div className="flex items-center gap-2 min-w-[100px]">
      <div className="flex-1 h-1.5 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={cn('h-full rounded-full', colorClass)}
          style={{ width: `${pct}%` }}
        />
      </div>
      <span className="text-xs text-text-muted tabular-nums w-9 text-right">
        {pct}%
      </span>
    </div>
  )
}
