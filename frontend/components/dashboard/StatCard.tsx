'use client'

import { useEffect, useRef, useState } from 'react'
import CountUp from 'react-countup'
import { motion } from 'motion/react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  secondary?: string
  secondaryColor?: string
  previousValue?: number | null
  deltaInverted?: boolean
  progressBar?: number
  hideDeltaWhenValueZero?: boolean
  delay?: number
  onClick?: () => void
}

function computeDelta(current: number, previous: number | null | undefined) {
  if (previous == null) return null
  const diff = current - previous
  if (diff === 0) return null
  return { diff: Math.abs(diff), direction: diff > 0 ? 'up' : 'down' }
}

export function StatCard({
  label,
  value,
  secondary,
  secondaryColor = 'text-[var(--color-text-secondary)]',
  previousValue,
  deltaInverted = false,
  progressBar,
  hideDeltaWhenValueZero = false,
  delay = 0,
  onClick,
}: StatCardProps) {
  const delta = typeof value === 'number' ? computeDelta(value, previousValue) : null
  const showDelta = !(hideDeltaWhenValueZero && typeof value === 'number' && value === 0)
  const deltaIsGood =
    delta != null &&
    ((delta.direction === 'down' && !deltaInverted) ||
      (delta.direction === 'up' && deltaInverted))
  const [flash, setFlash] = useState(false)
  const prevValueRef = useRef(value)

  useEffect(() => {
    if (prevValueRef.current !== value && typeof value === 'number') {
      setFlash(true)
      const timer = setTimeout(() => setFlash(false), 600)
      prevValueRef.current = value
      return () => clearTimeout(timer)
    }
  }, [value])

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut', delay }}
      onClick={onClick}
      className={cn(
        'flex flex-col gap-1 rounded-xl border border-[#1e2a3d] bg-[#0c1120] p-4 transition-all',
        onClick && 'cursor-pointer hover:border-violet-500/30 hover:bg-[#0c1120]/85'
      )}
    >
      <div className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-text-secondary)]">
        {label}
      </div>
      <div
        className={cn(
          'text-[28px] font-semibold tracking-tight leading-none transition-colors duration-300',
          flash
            ? deltaIsGood
              ? 'text-emerald-200'
              : 'text-red-200'
            : deltaIsGood
              ? 'text-emerald-400'
              : delta
                ? 'text-red-400'
                : 'text-[var(--color-text-primary)]'
        )}
      >
        {typeof value === 'number' ? (
          <CountUp end={value} duration={0.55} preserveValue useEasing />
        ) : (
          value
        )}
      </div>
      {delta && showDelta ? (
        <div
          className={cn(
            'text-[10px] font-medium whitespace-nowrap overflow-hidden text-ellipsis',
            deltaIsGood ? 'text-emerald-500/80' : 'text-red-500/80'
          )}
        >
          {delta.direction === 'up' ? '↑' : '↓'} {delta.diff} vs prev
        </div>
      ) : null}
      {secondary && (
        <div className={cn('mt-0.5 text-[10px] font-medium', secondaryColor)}>
          {secondary}
        </div>
      )}
      {typeof progressBar === 'number' ? (
        <div className="mt-2 h-0.5 w-full rounded-full bg-[var(--color-text-ghost)]">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${Math.min(progressBar, 100)}%`,
              background: 'var(--color-accent-purple)',
            }}
          />
        </div>
      ) : null}
    </motion.div>
  )
}
