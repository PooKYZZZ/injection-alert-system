import { cn } from '@/lib/utils'
import {
  ALERT_DISPLAY_ACTION_ALIASES,
  type AlertAction,
} from '@/features/alerts/contract'

const ACTION_CLASS_NAMES: Record<AlertAction, string> = {
  BLOCKED: 'text-severity-blocked-text font-semibold',
  THROTTLED: 'text-severity-blocked-text font-medium',
  ALLOWED: 'text-severity-safe-text font-medium',
}

type ActionLabelProps = {
  action: AlertAction | null
  expiresAt?: string
}

export function ActionLabel({ action, expiresAt }: ActionLabelProps) {
  if (action === null) {
    return <span className="text-sm text-text-secondary">Unavailable</span>
  }

  return (
    <div className="flex flex-col gap-0.5">
      <span className={cn('text-sm', ACTION_CLASS_NAMES[action])}>
        {ALERT_DISPLAY_ACTION_ALIASES[action]}
      </span>
      {action === 'BLOCKED' && expiresAt && (
        <span className="text-[10px] text-text-muted">
          {expiresAt}
        </span>
      )}
    </div>
  )
}
