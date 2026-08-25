'use client'

import { StatusBadge, type StatusTone } from './StatusBadge'

interface TriageBadgeProps {
  triage_status: 'new' | 'in_review' | 'escalated' | 'resolved' | 'false_positive' | null | undefined
}

const TRIAGE_MAPPING: Record<string, { label: string; tone: StatusTone }> = {
  null: { label: 'New', tone: 'info' },
  new: { label: 'New', tone: 'info' },
  in_review: { label: 'In review', tone: 'warning' },
  escalated: { label: 'Escalated', tone: 'danger' },
  resolved: { label: 'Resolved', tone: 'success' },
  false_positive: { label: 'False positive', tone: 'neutral' },
}

export function TriageBadge({ triage_status }: TriageBadgeProps) {
  const key = triage_status ?? 'null'
  const config = TRIAGE_MAPPING[key] ?? TRIAGE_MAPPING['null']

  return (
    <StatusBadge label={config.label} tone={config.tone} domain="workflow" />
  )
}

