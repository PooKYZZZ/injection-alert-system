'use client'

import { cn } from '@/lib/utils'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'
import { type AlertPrediction } from '@/features/alerts/contract'

interface AttackTypePanelProps {
  countsByLabel: Partial<Record<AlertPrediction, number>>
  isPending?: boolean
}

const colorMap: Record<AlertPrediction, string> = {
  'SQL Injection': 'var(--color-chart-primary)',
  'Code Injection': 'var(--color-chart-secondary)',
  'Other Attacks': 'var(--color-chart-tertiary)',
  'Normal': 'var(--color-severity-safe-accent)',
}

const labelOrder: AlertPrediction[] = [
  'SQL Injection',
  'Code Injection',
  'Other Attacks',
  'Normal',
]

export function AttackTypePanel({ countsByLabel, isPending = false }: AttackTypePanelProps) {
  if (isPending) {
    return <LoadingSkeleton rows={4} />
  }

  const entries = labelOrder
    .filter((label) => countsByLabel[label] !== undefined && countsByLabel[label]! > 0)
    .map((label) => ({
      label,
      count: countsByLabel[label] ?? 0,
    }))

  const total = entries.reduce((sum, { count }) => sum + count, 0)

  if (entries.length === 0) {
    return <EmptyState message="No attack data" subtext="Distribution unavailable" />
  }

  return (
    <div className="flex flex-col gap-2">
      {entries.map(({ label, count }) => {
        const percentage = total > 0 ? (count / total) * 100 : 0

        return (
          <div key={label} className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(48px,96px)_auto] items-center gap-2">
            <span className="min-w-0 truncate text-[11px] text-[var(--color-text-secondary)]">
              {label}
            </span>
            <div className="h-[3px] rounded-full bg-surface-inset">
              <div
                className={cn('h-full rounded-full transition-all duration-500')}
                style={{ width: `${percentage}%`, background: colorMap[label] }}
              />
            </div>
            <div className="flex shrink-0 items-center justify-end gap-2 tabular-nums">
              <span className="text-[11px] font-medium text-[var(--color-text-primary)] text-right">
                {count}
              </span>
              <span className="text-[11px] text-[var(--color-text-muted)] text-right">
                {Math.round(percentage)}%
              </span>
            </div>
          </div>
        )
      })}
    </div>
  )
}
