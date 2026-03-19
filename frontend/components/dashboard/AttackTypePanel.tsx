'use client'

import { cn } from '@/lib/utils'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'
import { ALERT_PREDICTION_VALUES, type AlertPrediction } from '@/features/alerts/contract'

interface AttackTypePanelProps {
  countsByLabel: Partial<Record<AlertPrediction, number>>
  isLoading?: boolean
}

const colorMap: Record<AlertPrediction, string> = {
  'SQL Injection': 'bg-violet-500',
  'Code Injection': 'bg-red-600',
  'Other Attacks': 'bg-red-500',
  'Normal': 'bg-gray-500',
}

const labelOrder: AlertPrediction[] = [
  'SQL Injection',
  'Code Injection',
  'Other Attacks',
  'Normal',
]

export function AttackTypePanel({ countsByLabel, isLoading = false }: AttackTypePanelProps) {
  if (isLoading) {
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
        const pct = total > 0 ? Math.round((count / total) * 100) : 0
        const width = total > 0 ? `${(count / total) * 100}%` : '0%'

        return (
          <div key={label} className="flex items-center gap-2 text-[11px]">
            <span className="w-24 truncate text-right text-[#8b949e]">{label}</span>
            <div className="flex-1 h-2 bg-[#21262d] rounded-full overflow-hidden">
              <div
                className={cn('h-full rounded-full transition-all duration-700', colorMap[label] || 'bg-gray-500')}
                style={{ width }}
              />
            </div>
            <span className="w-8 text-right font-medium">{count}</span>
            <span className="w-8 text-right text-[#484f58] text-[10px]">{pct}%</span>
          </div>
        )
      })}
    </div>
  )
}
