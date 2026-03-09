import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold',
  {
    variants: {
      severity: {
        CRITICAL: 'bg-red-100 text-red-800 border border-red-200',
        HIGH:     'bg-red-100 text-red-800 border border-red-200',
        MEDIUM:   'bg-gray-200 text-gray-700 border border-gray-300',
        LOW:      'bg-gray-200 text-gray-500 border border-gray-300',
      },
    },
  }
)

type SeverityBadgeProps = VariantProps<typeof badgeVariants> & {
  needsReview?: boolean
}

export function SeverityBadge({ severity, needsReview }: SeverityBadgeProps) {
  return (
    <div className="inline-flex flex-col items-start gap-0.5">
      <span className={cn(badgeVariants({ severity }))}>
        {severity}
      </span>
      {needsReview && (
        <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-medium bg-amber-100 text-amber-800 border border-amber-200">
          Needs Review
        </span>
      )}
    </div>
  )
}
