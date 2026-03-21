'use client'

import { useEffect, useRef } from 'react'
import { animate, motion } from 'motion/react'
import { cn } from '@/lib/utils'

interface StatCardProps {
  label: string
  value: string | number
  secondary?: string
  secondaryColor?: string
  borderColor?: string
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

function AnimatedNumber({ value }: { value: number }) {
  const ref = useRef<HTMLSpanElement>(null)
  const previousValueRef = useRef<number | null>(null)

  useEffect(() => {
    if (!ref.current) return
    const start = previousValueRef.current ?? value
    ref.current.textContent = Math.round(start).toString()
    const controls = animate(start, value, {
      duration: 0.55,
      ease: 'easeOut',
      onUpdate(latest) {
        if (ref.current) {
          ref.current.textContent = Math.round(latest).toString()
        }
      },
    })
    previousValueRef.current = value
    return () => controls.stop()
  }, [value])

  return <span ref={ref}>{value}</span>
}

export function StatCard({
  label,
  value,
  secondary,
  secondaryColor = 'text-[var(--color-text-secondary)]',
  borderColor,
  previousValue,
  deltaInverted = false,
  progressBar,
  hideDeltaWhenValueZero = false,
  delay = 0,
  onClick,
}: StatCardProps) {
  const isAlert = borderColor?.includes('border-l-red-700')
  const delta = typeof value === 'number' ? computeDelta(value, previousValue) : null
  const showDelta = !(hideDeltaWhenValueZero && typeof value === 'number' && value === 0)
  const deltaIsGood =
    delta != null &&
    ((delta.direction === 'down' && !deltaInverted) ||
      (delta.direction === 'up' && deltaInverted))

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut', delay }}
      onClick={onClick}
      className={cn(
        'flex flex-col gap-1 rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] p-3 transition-all',
        borderColor,
        onClick &&
          'cursor-pointer hover:border-violet-500/50 hover:bg-[var(--color-bg-panel)]/80'
      )}
    >
      <div className="text-[10px] font-medium uppercase tracking-wider text-[var(--color-text-secondary)]">
        {label}
      </div>
      <div
        className={cn(
          'text-[28px] font-semibold tracking-tight leading-none',
          isAlert ? 'text-red-400' : 'text-[var(--color-text-primary)]'
        )}
      >
        {typeof value === 'number' ? <AnimatedNumber value={value} /> : value}
      </div>
      {delta && showDelta ? (
        <div className={cn('text-[11px] font-medium', deltaIsGood ? 'text-emerald-400' : 'text-red-400')}>
          {delta.direction === 'up' ? '↑' : '↓'} {delta.diff} vs prev window
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
            className="h-full rounded-full bg-accent-purple transition-all duration-700"
            style={{ width: `${Math.min(progressBar, 100)}%` }}
          />
        </div>
      ) : null}
    </motion.div>
  )
}


