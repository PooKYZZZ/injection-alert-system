'use client'

import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

interface TriageBadgeProps {
  triage_status: 'new' | 'in_review' | 'escalated' | 'resolved' | 'false_positive' | null | undefined
}

const TRIAGE_MAPPING: Record<string, { label: string; styles: string }> = {
  null: { label: 'New', styles: 'bg-transparent text-blue-400 border-blue-500/30' },
  new: { label: 'New', styles: 'bg-transparent text-blue-400 border-blue-500/30' },
  in_review: { label: 'In Review', styles: 'bg-transparent text-amber-400 border-amber-500/30' },
  escalated: { label: 'Escalated', styles: 'bg-transparent text-red-400 border-red-500/30' },
  resolved: { label: 'Resolved', styles: 'bg-transparent text-emerald-400 border-emerald-500/30' },
  false_positive: { label: 'False Positive', styles: 'bg-transparent text-[#7d8590] border-[#30363d]' },
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
