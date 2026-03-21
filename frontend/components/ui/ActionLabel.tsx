'use client'

import { cn } from '@/lib/utils'
import {
  ALERT_DISPLAY_ACTION_ALIASES,
  type AlertAction,
} from '@/features/alerts/contract'

interface ActionLabelProps {
  action: AlertAction | null
}

const styles: Record<AlertAction, string> = {
  BLOCKED: 'bg-transparent border border-red-500/30 text-red-400',
  THROTTLED: 'bg-transparent border border-amber-500/30 text-amber-400',
  ALLOWED: 'bg-transparent border border-emerald-500/30 text-emerald-400',
}

export function ActionLabel({ action }: ActionLabelProps) {
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
        'inline-flex items-center rounded-full px-1.5 py-0.5 text-[10px] font-medium border',
        styles[action]
      )}
    >
      {ALERT_DISPLAY_ACTION_ALIASES[action]}
    </span>
  )
}


