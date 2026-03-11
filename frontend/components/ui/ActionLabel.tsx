import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const actionVariants = cva('text-sm', {
  variants: {
    action: {
      BLOCKED:      'text-status-blocked font-bold',
      THROTTLED:    'text-status-throttled font-medium',
      LOGGED:       'text-status-logged font-medium',
      RATE_LIMITED: 'text-status-ratelimited font-medium',
    },
  },
})

type ActionLabelProps = VariantProps<typeof actionVariants> & {
  expiresAt?: string
}

export function ActionLabel({ action, expiresAt }: ActionLabelProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className={cn(actionVariants({ action }))}>
        {action}
      </span>
      {action === 'BLOCKED' && expiresAt && (
        <span className="text-[10px] text-text-muted">
          {expiresAt}
        </span>
      )}
    </div>
  )
}
