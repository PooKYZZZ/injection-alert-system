'use client'

import { motion } from 'motion/react'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'

interface MLEnforcementMapProps {
  high: number
  medium: number
  low: number
  isLoading?: boolean
  unavailable?: boolean
}

export function MLEnforcementMap({
  high,
  medium,
  low,
  isLoading = false,
  unavailable = false,
}: MLEnforcementMapProps) {
  if (isLoading) {
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
          <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
          <span className="text-[#8b949e]">HIGH CONF</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[#e6edf3]">{high}</span>
          <span className="px-1 py-0.5 rounded bg-red-900/30 text-red-400 border border-red-500/20 text-[8px] font-bold">
            BLOCKED
          </span>
        </div>
      </div>
      <div className="h-1 bg-[#21262d] rounded-full overflow-hidden">
        <div className="h-full bg-red-500" style={{ width: `${total > 0 ? (high / total) * 100 : 0}%` }} />
      </div>

      {/* MED CONF */}
      <div className="flex items-center justify-between text-[10px] mt-1">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
          <span className="text-[#8b949e]">MED CONF</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[#e6edf3]">{medium}</span>
          <span className="px-1 py-0.5 rounded bg-amber-900/30 text-amber-400 border border-amber-500/20 text-[8px] font-bold">
            THROTTLED
          </span>
        </div>
      </div>
      <div className="h-1 bg-[#21262d] rounded-full overflow-hidden">
        <div className="h-full bg-amber-500" style={{ width: `${total > 0 ? (medium / total) * 100 : 0}%` }} />
      </div>

      {/* LOW CONF */}
      <div className="flex items-center justify-between text-[10px] mt-1">
        <div className="flex items-center gap-1.5">
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
          <span className="text-[#8b949e]">LOW CONF</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-[#e6edf3]">{low}</span>
          <span className="px-1 py-0.5 rounded bg-emerald-900/30 text-emerald-400 border border-emerald-500/20 text-[8px] font-bold">
            ALLOWED
          </span>
        </div>
      </div>
      <div className="h-1 bg-[#21262d] rounded-full overflow-hidden">
        <div className="h-full bg-emerald-500" style={{ width: `${total > 0 ? (low / total) * 100 : 0}%` }} />
      </div>

      <div className="mt-1 text-[9px] text-[#484f58] leading-tight italic">
        {`* Enforcement actions are strictly bound to model confidence tiers.`}
      </div>
    </motion.div>
  )
}
