'use client'

import { motion } from 'motion/react'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'

interface MLConfidenceBandsProps {
  high: number
  medium: number
  low: number
  isPending?: boolean
  unavailable?: boolean
}

export function MLConfidenceBands({
  high,
  medium,
  low,
  isPending = false,
  unavailable = false,
}: MLConfidenceBandsProps) {
  if (isPending) {
    return <LoadingSkeleton rows={3} />
  }

  if (unavailable) {
    return (
      <EmptyState
        message="Confidence bands unavailable"
        subtext="Current stats API does not provide this data"
      />
    )
  }

  const total = high + medium + low

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="flex flex-col gap-2"
    >
      <div className="grid grid-cols-[1fr_96px_64px] items-center gap-2">
        <span className="truncate text-[11px] text-[var(--color-accent-analytic)]">{`High > 80%`}</span>
        <div className="h-[3px] rounded-full bg-[var(--color-border-light)]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${total > 0 ? (high / total) * 100 : 0}%`, background: 'var(--color-severity-high-accent)' }}
          />
        </div>
        <div className="flex items-center justify-end gap-2 tabular-nums">
          <span className="text-[11px] font-medium text-[var(--color-text-primary)] text-right">{high}</span>
          <span className="text-[11px] text-[var(--color-text-muted)] text-right">
            {total > 0 ? Math.round((high / total) * 100) : 0}%
          </span>
        </div>
      </div>
      <div className="grid grid-cols-[1fr_96px_64px] items-center gap-2">
        <span className="truncate text-[11px] text-[var(--color-accent-analytic)]">Medium 50–80%</span>
        <div className="h-[3px] rounded-full bg-[var(--color-border-light)]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${total > 0 ? (medium / total) * 100 : 0}%`, background: 'var(--color-accent-amber)' }}
          />
        </div>
        <div className="flex items-center justify-end gap-2 tabular-nums">
          <span className="text-[11px] font-medium text-[var(--color-text-primary)] text-right">{medium}</span>
          <span className="text-[11px] text-[var(--color-text-muted)] text-right">
            {total > 0 ? Math.round((medium / total) * 100) : 0}%
          </span>
        </div>
      </div>
      <div className="grid grid-cols-[1fr_96px_64px] items-center gap-2">
        <span className="truncate text-[11px] text-[var(--color-accent-analytic)]">{`Low < 50%`}</span>
        <div className="h-[3px] rounded-full bg-[var(--color-border-light)]">
          <div
            className="h-full rounded-full transition-all duration-500"
            style={{ width: `${total > 0 ? (low / total) * 100 : 0}%`, background: 'var(--color-severity-safe-accent)' }}
          />
        </div>
        <div className="flex items-center justify-end gap-2 tabular-nums">
          <span className="text-[11px] font-medium text-[var(--color-text-primary)] text-right">{low}</span>
          <span className="text-[11px] text-[var(--color-text-muted)] text-right">
            {total > 0 ? Math.round((low / total) * 100) : 0}%
          </span>
        </div>
      </div>
    </motion.div>
  )
}

