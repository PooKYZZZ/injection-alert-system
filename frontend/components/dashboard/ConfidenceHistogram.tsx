import { cn } from 'lib/utils'

interface HistogramBin {
  label: string
  count: number
  pct: number
  colorClass: string
}

interface ConfidenceHistogramProps {
  bins: HistogramBin[]
}

export default function ConfidenceHistogram({ bins }: ConfidenceHistogramProps) {
  return (
    <div className="bg-surface-light border border-border-light rounded-sm shadow-subtle p-4">
      <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-4">
        ML Confidence Distribution
      </h3>
      <div className="flex items-end gap-2 h-32">
        {bins.map((bin) => (
          <div key={bin.label} className="flex flex-col items-center flex-1 gap-1 h-full">
            <div className="relative flex-1 w-full">
              <div
                className={cn('absolute bottom-0 w-full', bin.colorClass)}
                style={{ height: `${bin.pct}%` }}
              />
            </div>
            <span className="text-[10px] text-text-muted text-center leading-tight">
              {bin.label}
            </span>
            <span className="text-[10px] font-medium text-text-main tabular-nums">
              {bin.count}
            </span>
          </div>
        ))}
      </div>
    </div>
  )
}
