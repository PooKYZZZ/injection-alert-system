'use client'

import { cn } from '@/lib/utils'
import {
  ALERT_DISPLAY_ACTION_ALIASES,
  type AlertAction,
} from '@/features/alerts/contract'

interface ActionLabelProps {
  action: AlertAction | null
  bordered?: boolean
}

const styles: Record<AlertAction, string> = {
  BLOCKED: 'bg-transparent text-severity-high-text',
  THROTTLED: 'bg-transparent text-severity-blocked-text',
  ALLOWED: 'bg-transparent text-severity-safe-text',
}

const borderedStyles: Record<AlertAction, string> = {
  BLOCKED: 'border border-severity-high-border/30',
  THROTTLED: 'border border-severity-blocked-border/30',
  ALLOWED: 'border border-severity-safe-border/30',
}

export function ActionLabel({ action, bordered = true }: ActionLabelProps) {
  if (action === null) {
    return (
      <span className="inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium text-[var(--color-text-secondary)]">
        Unavailable
      </span>
    )
  }

  return (
    <span
      className={cn(
        'inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium',
        styles[action],
        bordered && borderedStyles[action]
      )}
    >
      {ALERT_DISPLAY_ACTION_ALIASES[action]}
    </span>
  )
}


