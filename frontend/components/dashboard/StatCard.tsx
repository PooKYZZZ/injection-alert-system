'use client'

import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  secondary?: string
  secondaryColor?: string
  borderColor?: string
  onClick?: () => void
}

export function StatCard({
  label,
  value,
  secondary,
  secondaryColor = 'text-[#7d8590]',
  borderColor,
  onClick,
}: StatCardProps) {
  const isAlert = borderColor === 'border-l-red-700'

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      onClick={onClick}
      className={cn(
        'flex flex-col gap-1 rounded-lg border border-[#30363d] bg-[#161b22] p-3 transition-all',
        borderColor,
        onClick &&
          'cursor-pointer hover:border-violet-500/50 hover:bg-[#161b22]/80'
      )}
    >
      <div className="text-[10px] font-medium uppercase tracking-wider text-[#7d8590]">
        {label}
      </div>
      <div
        className={cn(
          'text-2xl font-semibold leading-none',
          isAlert ? 'text-red-400' : 'text-[#e6edf3]'
        )}
      >
        {value}
      </div>
      {secondary && (
        <div className={cn('mt-0.5 text-[10px] font-medium', secondaryColor)}>
          {secondary}
        </div>
      )}
    </motion.div>
  )
}
