'use client'

import { useEffect, useRef, useState } from 'react'
import CountUp from 'react-countup'
import { motion } from 'motion/react'
import { cn } from '@/lib/utils'
import { InfoDisclosure } from '@/components/ui/InfoDisclosure'

interface StatCardProps {
  label: string
  info?: string
  value: string | number
  secondary?: string
  secondaryColor?: string
  previousValue?: number | null
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
  info,
  value,
  secondary,
  secondaryColor = 'text-text-secondary',
  previousValue,
  progressBar,
  hideDeltaWhenValueZero = false,
  delay = 0,
  onClick,
}: StatCardProps) {
  const delta = typeof value === 'number' ? computeDelta(value, previousValue) : null
  const showDelta = !(hideDeltaWhenValueZero && typeof value === 'number' && value === 0)
  const isZeroValue = typeof value === 'number' && value === 0
  const [flash, setFlash] = useState(false)
  const prevValueRef = useRef(value)

  useEffect(() => {
    if (prevValueRef.current !== value && typeof value === 'number') {
      const showTimer = setTimeout(() => setFlash(true), 0)
      const hideTimer = setTimeout(() => setFlash(false), 600)
      prevValueRef.current = value
      return () => {
        clearTimeout(showTimer)
        clearTimeout(hideTimer)
      }
    }
    prevValueRef.current = value
  }, [value])

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut', delay }}
      onClick={onClick}
      className={cn(
        'min-w-0 flex flex-col gap-1 p-3 transition-colors sm:p-4',
        onClick && 'cursor-pointer hover:bg-surface-inset'
      )}
    >
      {info ? (
        <div className="flex min-w-0 items-center gap-1.5 break-words text-xs font-medium text-[var(--color-text-secondary)]">
          <span className="min-w-0 break-words">{label}</span>
          <InfoDisclosure label={label}>{info}</InfoDisclosure>
        </div>
      ) : (
        <div className="break-words text-xs font-medium text-[var(--color-text-secondary)]">
          {label}
        </div>
      )}
      <div
        className={cn(
          'text-[28px] font-semibold tracking-tight leading-none transition-colors duration-300',
          isZeroValue || !flash ? 'text-text-primary' : 'text-accent-action'
        )}
      >
        {typeof value === 'number' ? (
          <CountUp end={value} duration={0.55} preserveValue useEasing />
        ) : (
          value
        )}
      </div>
      {delta && showDelta ? (
        <div className="flex min-w-0 items-center gap-1 overflow-hidden text-ellipsis whitespace-nowrap text-[11px] font-medium text-text-muted">
          <span>{delta.direction === 'up' ? '↑' : '↓'} {delta.diff} vs previous</span>
          <InfoDisclosure label={`${label} change vs previous`}>
            Compares this count in the selected rolling time window with the immediately preceding window of the same length. The arrow shows whether the current count is higher or lower; the number is the absolute difference, not a percentage or a measure of whether activity improved.
          </InfoDisclosure>
        </div>
      ) : null}
      {secondary && (
        <div className={cn('mt-0.5 break-words text-[11px] font-medium', secondaryColor)}>
          {secondary}
        </div>
      )}
      {typeof progressBar === 'number' ? (
        <div className="mt-2 h-0.5 w-full rounded-full bg-surface-border">
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{
              width: `${Math.min(progressBar, 100)}%`,
              background: 'var(--color-accent-action)',
            }}
          />
        </div>
      ) : null}
    </motion.div>
  )
}
