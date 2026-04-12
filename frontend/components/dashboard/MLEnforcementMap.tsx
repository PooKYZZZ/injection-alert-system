'use client'

import { motion } from 'motion/react'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'

interface MLEnforcementMapProps {
  high: number
  medium: number
  low: number
  isPending?: boolean
  unavailable?: boolean
}

export function MLEnforcementMap({
  high,
  medium,
  low,
  isPending = false,
  unavailable = false,
}: MLEnforcementMapProps) {
  if (isPending) {
    return <LoadingSkeleton rows={3} />
  }

  if (unavailable) {
    return (
      <EmptyState
        message="Enforcement map unavailable"
        subtext="Current stats API does not provide this data"
      />
    )
  }

  const total = high + medium + low

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut', delay: 0.1 }}
      className="flex flex-col gap-1.5"
    >
      {/* HIGH CONF */}
      <div className="flex items-center justify-between text-[10px]">
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-high-accent" />
          <span className="text-[var(--color-text-secondary)]">HIGH CONF</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{high}</span>
          <span className="rounded border border-severity-high-border bg-severity-high-bg px-1 py-0.5 text-[10px] font-bold text-severity-high-text">
            BLOCKED
          </span>
        </div>
      </div>
      <div className="h-1 bg-[var(--color-text-ghost)] rounded-full overflow-hidden">
        <div className="h-full bg-severity-high-accent" style={{ width: `${total > 0 ? (high / total) * 100 : 0}%` }} />
      </div>

      {/* MED CONF */}
      <div className="flex items-center justify-between text-[10px] mt-1">
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-blocked-accent" />
          <span className="text-[var(--color-text-secondary)]">MED CONF</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{medium}</span>
          <span className="rounded border border-severity-blocked-border bg-severity-blocked-bg px-1 py-0.5 text-[10px] font-bold text-severity-blocked-text">
            THROTTLED
          </span>
        </div>
      </div>
      <div className="h-1 bg-[var(--color-text-ghost)] rounded-full overflow-hidden">
        <div className="h-full bg-severity-blocked-accent" style={{ width: `${total > 0 ? (medium / total) * 100 : 0}%` }} />
      </div>

      {/* LOW CONF */}
      <div className="flex items-center justify-between text-[10px] mt-1">
        <div className="flex items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-safe-accent" />
          <span className="text-[var(--color-text-secondary)]">LOW CONF</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{low}</span>
          <span className="rounded border border-severity-safe-border bg-severity-safe-bg px-1 py-0.5 text-[10px] font-bold text-severity-safe-text">
            ALLOWED
          </span>
        </div>
      </div>
      <div className="h-1 bg-[var(--color-text-ghost)] rounded-full overflow-hidden">
        <div className="h-full bg-severity-safe-accent" style={{ width: `${total > 0 ? (low / total) * 100 : 0}%` }} />
      </div>

      <div className="mt-1 text-[11px] text-[var(--color-text-muted)] leading-tight italic">
        {`* Enforcement actions are strictly bound to model confidence tiers.`}
      </div>
    </motion.div>
  )
}

