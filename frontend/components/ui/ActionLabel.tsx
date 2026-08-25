'use client'

import {
  ALERT_DISPLAY_ACTION_ALIASES,
  type AlertAction,
} from '@/features/alerts/contract'
import { StatusBadge, type StatusTone } from './StatusBadge'

interface ActionLabelProps {
  action: AlertAction | null
  bordered?: boolean
}

const tones: Record<AlertAction, StatusTone> = {
  BLOCKED: 'danger',
  THROTTLED: 'warning',
  ALLOWED: 'success',
}

export function ActionLabel({ action, bordered = true }: ActionLabelProps) {
  if (action === null) {
    return <StatusBadge label="Unavailable" tone="neutral" domain="enforcement" bordered={bordered} />
  }

  return <StatusBadge label={ALERT_DISPLAY_ACTION_ALIASES[action]} tone={tones[action]} domain="enforcement" bordered={bordered} />
}

