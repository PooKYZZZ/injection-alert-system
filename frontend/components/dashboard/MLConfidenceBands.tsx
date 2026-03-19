'use client'

import { motion } from 'motion/react'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'

interface MLConfidenceBandsProps {
  high: number
  medium: number
  low: number
  isLoading?: boolean
  unavailable?: boolean
}

export function MLConfidenceBands({
  high,
  medium,
  low,
  isLoading = false,
  unavailable = false,
}: MLConfidenceBandsProps) {
  if (isLoading) {
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
      <div className="flex items-center gap-2 text-[11px]">
        <span className="w-24 text-[#8b949e]">{`High > 80%`}</span>
        <div className="flex-1 h-1.5 bg-[#21262d] rounded-full overflow-hidden">
          <div
            className="h-full bg-violet-500 rounded-full"
            style={{ width: `${total > 0 ? (high / total) * 100 : 0}%` }}
          />
        </div>
        <span className="w-6 text-right font-medium">{high}</span>
        <span className="w-8 text-right text-[#484f58] text-[10px]">
          {total > 0 ? Math.round((high / total) * 100) : 0}%
        </span>
      </div>
      <div className="flex items-center gap-2 text-[11px]">
        <span className="w-24 text-[#8b949e]">Medium 50–80%</span>
        <div className="flex-1 h-1.5 bg-[#21262d] rounded-full overflow-hidden">
          <div
            className="h-full bg-amber-500 rounded-full"
            style={{ width: `${total > 0 ? (medium / total) * 100 : 0}%` }}
          />
        </div>
        <span className="w-6 text-right font-medium">{medium}</span>
        <span className="w-8 text-right text-[#484f58] text-[10px]">
          {total > 0 ? Math.round((medium / total) * 100) : 0}%
        </span>
      </div>
      <div className="flex items-center gap-2 text-[11px]">
        <span className="w-24 text-[#8b949e]">{`Low < 50%`}</span>
        <div className="flex-1 h-1.5 bg-[#21262d] rounded-full overflow-hidden">
          <div
            className="h-full bg-emerald-500 rounded-full"
            style={{ width: `${total > 0 ? (low / total) * 100 : 0}%` }}
          />
        </div>
        <span className="w-6 text-right font-medium">{low}</span>
        <span className="w-8 text-right text-[#484f58] text-[10px]">
          {total > 0 ? Math.round((low / total) * 100) : 0}%
        </span>
      </div>
    </motion.div>
  )
}
