'use client'

import { cn } from '@/lib/utils'

interface TriageBadgeProps {
  triage_status: 'new' | 'in_review' | 'escalated' | 'resolved' | 'false_positive' | null | undefined
}

const TRIAGE_MAPPING: Record<string, { label: string; styles: string }> = {
  null: { label: 'New', styles: 'bg-transparent text-accent-action border-accent-action/30' },
  new: { label: 'New', styles: 'bg-transparent text-accent-action border-accent-action/30' },
  in_review: { label: 'In Review', styles: 'bg-transparent text-severity-blocked-text border-severity-blocked-border/30' },
  escalated: { label: 'Escalated', styles: 'bg-transparent text-severity-high-text border-severity-high-border/30' },
  resolved: { label: 'Resolved', styles: 'bg-transparent text-severity-safe-text border-severity-safe-border/30' },
  false_positive: { label: 'False Positive', styles: 'bg-transparent text-text-secondary border-surface-border' },
}

export function TriageBadge({ triage_status }: TriageBadgeProps) {
  const key = triage_status ?? 'null'
  const config = TRIAGE_MAPPING[key] ?? TRIAGE_MAPPING['null']

  return (
    <span
      className={cn(
        'inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium',
        config.styles
      )}
    >
      {config.label}
    </span>
  )
}


