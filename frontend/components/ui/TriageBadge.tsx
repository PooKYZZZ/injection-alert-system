'use client'

import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

interface TriageBadgeProps {
  triage_status: 'new' | 'in_review' | 'escalated' | 'resolved' | 'false_positive' | null | undefined
}

const TRIAGE_MAPPING: Record<string, { label: string; styles: string }> = {
  null: {
    label: 'New',
    styles: 'bg-[#1c2433] text-blue-400 border-[#1f3a5c]',
  },
  new: {
    label: 'New',
    styles: 'bg-[#1c2433] text-blue-400 border-[#1f3a5c]',
  },
  in_review: {
    label: 'In Review',
    styles: 'bg-[#2d2310] text-amber-400 border-amber-900',
  },
  escalated: {
    label: 'Escalated',
    styles: 'bg-[#2d1b1b] text-red-400 border-red-900',
  },
  resolved: {
    label: 'Resolved',
    styles: 'bg-[#0f2d1a] text-emerald-400 border-emerald-900',
  },
  false_positive: {
    label: 'False Positive',
    styles: 'bg-[#1c1c2e] text-[#6b7280] border-[#30363d]',
  },
}

export function TriageBadge({ triage_status }: TriageBadgeProps) {
  const key = triage_status ?? 'null'
  const config = TRIAGE_MAPPING[key] ?? TRIAGE_MAPPING['null']

  return (
    <motion.span
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.2 }}
      className={cn(
        'inline-flex items-center rounded border px-1.5 py-0.5 text-[10px] font-medium',
        config.styles
      )}
    >
      {config.label}
    </motion.span>
  )
}
