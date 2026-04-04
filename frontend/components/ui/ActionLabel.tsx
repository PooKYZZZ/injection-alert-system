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
  BLOCKED: 'bg-transparent text-red-400',
  THROTTLED: 'bg-transparent text-amber-400',
  ALLOWED: 'bg-transparent text-emerald-400',
}

const borderedStyles: Record<AlertAction, string> = {
  BLOCKED: 'border border-red-500/30',
  THROTTLED: 'border border-amber-500/30',
  ALLOWED: 'border border-emerald-500/30',
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


