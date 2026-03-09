import { cn } from '@/lib/utils'
import type { ShapFeature } from '@/features/alerts/types'

interface ShapChartProps {
  features: ShapFeature[]
}

export function ShapChart({ features }: ShapChartProps) {
  if (features.length === 0) return null

  const maxContribution = Math.max(...features.map(f => Math.abs(f.contribution)))

  return (
    <div className="flex flex-col gap-1.5">
      {features.map((feature) => {
        const widthPct = maxContribution > 0
          ? (Math.abs(feature.contribution) / maxContribution) * 100
          : 0
        const isPositive = feature.contribution >= 0
        const barColor = isPositive ? 'bg-status-high' : 'bg-status-medium'
        const sign = isPositive ? '+' : ''

        return (
          <div key={feature.feature_name} className="flex items-center gap-2">
            <span className="text-xs text-text-muted w-32 shrink-0 truncate text-right">
              {feature.feature_name}
            </span>
            <div className="flex-1 h-3 bg-gray-100 rounded-sm overflow-hidden">
              <div
                className={cn('h-full rounded-sm', barColor)}
                style={{ width: `${widthPct}%` }}
              />
            </div>
            <span className={cn(
              'text-xs tabular-nums w-10 shrink-0',
              isPositive ? 'text-status-high' : 'text-status-medium'
            )}>
              {sign}{feature.contribution.toFixed(1)}
            </span>
          </div>
        )
      })}
    </div>
  )
}
