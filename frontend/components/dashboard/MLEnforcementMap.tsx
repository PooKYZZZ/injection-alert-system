'use client'

import { motion } from 'motion/react'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'
import type { ConfidenceBandCounts } from '@/features/alerts/confidenceBands'

interface MLEnforcementMapProps {
  nonNormalCounts: ConfidenceBandCounts
  isPending?: boolean
  unavailable?: boolean
}

export function MLEnforcementMap({
  nonNormalCounts,
  isPending = false,
  unavailable = false,
}: MLEnforcementMapProps) {
  const { critical, high, medium, low } = nonNormalCounts
  if (isPending) {
    return <LoadingSkeleton rows={4} />
  }

  if (unavailable) {
    return (
      <EmptyState
        message="Enforcement map unavailable"
        subtext="Current stats API does not provide this data"
      />
    )
  }

  const total = critical + high + medium + low

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut', delay: 0.1 }}
      className="min-w-0 flex flex-col gap-1.5"
    >
      <div className="break-words text-[11px] font-medium text-[var(--color-text-primary)]">
        Action policy for non-Normal predictions
      </div>
      <div className="break-words text-[11px] leading-tight text-[var(--color-text-muted)]">
        Normal predictions remain ALLOWED for all valid confidence tiers.
      </div>

      <div className="flex min-w-0 items-center justify-between gap-2 text-[10px]">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-high-accent" />
          <span className="truncate text-[var(--color-accent-analytic)]">CRITICAL non-Normal</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{critical}</span>
          <span className="rounded border border-severity-high-border bg-severity-high-bg px-1 py-0.5 text-[10px] font-bold text-severity-high-text">
            BLOCKED
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-border">
        <div className="h-full bg-severity-high-accent" style={{ width: `${total > 0 ? (critical / total) * 100 : 0}%` }} />
      </div>

      <div className="flex min-w-0 items-center justify-between gap-2 text-[10px]">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-high-accent" />
          <span className="truncate text-[var(--color-accent-analytic)]">HIGH non-Normal</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{high}</span>
          <span className="rounded border border-severity-high-border bg-severity-high-bg px-1 py-0.5 text-[10px] font-bold text-severity-high-text">
            BLOCKED
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-border">
        <div className="h-full bg-severity-high-accent" style={{ width: `${total > 0 ? (high / total) * 100 : 0}%` }} />
      </div>

      <div className="mt-1 flex min-w-0 items-center justify-between gap-2 text-[10px]">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-blocked-accent" />
          <span className="truncate text-[var(--color-accent-analytic)]">MEDIUM non-Normal</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{medium}</span>
          <span className="rounded border border-severity-blocked-border bg-severity-blocked-bg px-1 py-0.5 text-[10px] font-bold text-severity-blocked-text">
            THROTTLED
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-border">
        <div className="h-full bg-severity-blocked-accent" style={{ width: `${total > 0 ? (medium / total) * 100 : 0}%` }} />
      </div>

      <div className="mt-1 flex min-w-0 items-center justify-between gap-2 text-[10px]">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-safe-accent" />
          <span className="truncate text-[var(--color-accent-analytic)]">LOW non-Normal</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{low}</span>
          <span className="rounded border border-severity-safe-border bg-severity-safe-bg px-1 py-0.5 text-[10px] font-bold text-severity-safe-text">
            ALLOWED
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-border">
        <div className="h-full bg-severity-safe-accent" style={{ width: `${total > 0 ? (low / total) * 100 : 0}%` }} />
      </div>

      <div className="mt-1 break-words text-[11px] leading-tight text-[var(--color-text-muted)] italic">
        {`* Enforcement actions depend on prediction class plus confidence tier.`}
      </div>
    </motion.div>
  )
}
