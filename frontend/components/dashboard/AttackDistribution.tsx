import { cn } from 'lib/utils'

interface DistributionItem {
  label: string
  pct: number
  colorClass: string
}

interface AttackDistributionProps {
  distribution: DistributionItem[]
}

export default function AttackDistribution({ distribution }: AttackDistributionProps) {
  return (
    <div className="bg-surface-light border border-border-light rounded-sm shadow-subtle p-4">
      <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-4">
        Detected Attack Types
      </h3>
      <div className="flex flex-col gap-3">
        {distribution.map((item) => (
          <div key={item.label} className="flex flex-col gap-1">
            <div className="flex justify-between items-center">
              <span className="text-xs font-medium text-text-main">{item.label}</span>
              <span className="text-xs text-text-muted tabular-nums">{item.pct.toFixed(1)}%</span>
            </div>
            <div className="h-2 w-full bg-gray-100 rounded-full overflow-hidden">
              <div
                className={cn('h-2 rounded-full', item.colorClass)}
                style={{ width: `${item.pct}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
