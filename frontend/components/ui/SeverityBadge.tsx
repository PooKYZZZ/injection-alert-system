import { cva, type VariantProps } from 'class-variance-authority'
import type { AlertPrediction } from '@/features/alerts/contract'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold',
  {
    variants: {
      severity: {
        BENIGN:
          'border-severity-benign-border bg-severity-benign-bg text-severity-benign-text',
        HIGH:
          'border-severity-high-border bg-severity-high-bg text-severity-high-text',
        MEDIUM:
          'border-severity-blocked-border bg-severity-blocked-bg text-severity-blocked-text',
        LOW:
          'border-severity-benign-border bg-severity-benign-bg text-severity-benign-text',
      },
    },
  }
)

type SeverityBadgeProps = VariantProps<typeof badgeVariants> & {
  needsReview?: boolean
  prediction?: AlertPrediction
}

export function SeverityBadge({ severity, needsReview, prediction }: SeverityBadgeProps) {
  const displaySeverity =
    prediction === 'Normal' ? 'BENIGN' : (severity ?? 'LOW')
  const label = prediction === 'Normal' ? 'Benign' : displaySeverity

  return (
    <div className="inline-flex flex-col items-start gap-0.5">
      <span className={cn(badgeVariants({ severity: displaySeverity }))}>
        {label}
      </span>
      {needsReview && (
        <span className="inline-flex items-center rounded-full border border-severity-blocked-border bg-severity-blocked-bg px-2 py-0.5 text-[10px] font-medium text-severity-blocked-text">
          Needs Review
        </span>
      )}
    </div>
  )
}
