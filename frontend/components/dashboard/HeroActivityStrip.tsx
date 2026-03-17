'use client'

import { useMemo } from 'react'
import type { Alert } from '@/features/alerts/types'

interface HeroActivityStripProps {
  alerts: Alert[]
  isPending: boolean
}

function buildPolyline(values: number[], width: number, height: number): string {
  const maxValue = Math.max(...values, 1)

  return values
    .map((value, index) => {
      const normalizedValue = value / maxValue
      const x = 16 + (index / Math.max(values.length - 1, 1)) * (width - 32)
      const y = height - 4 - normalizedValue * (height - 8)
      return `${x},${y}`
    })
    .join(' ')
}

export default function HeroActivityStrip({ alerts, isPending }: HeroActivityStripProps) {
  const series = useMemo(() => {
    const bucketCount = 20
    if (alerts.length === 0) {
      return {
        loaded: Array(bucketCount).fill(0),
        blocked: Array(bucketCount).fill(0),
      }
    }

    const timestamps = alerts
      .map((alert) => new Date(alert.timestamp).getTime())
      .filter((value) => Number.isFinite(value))
      .sort((a, b) => a - b)

    if (timestamps.length === 0) {
      return {
        loaded: Array(bucketCount).fill(0),
        blocked: Array(bucketCount).fill(0),
      }
    }

    const min = timestamps[0]
    const max = timestamps[timestamps.length - 1]
    const span = Math.max(max - min, 1)
    const loaded = Array(bucketCount).fill(0)
    const blocked = Array(bucketCount).fill(0)

    for (const alert of alerts) {
      const time = new Date(alert.timestamp).getTime()
      const ratio = span === 0 ? 0 : (time - min) / span
      const index = Math.min(bucketCount - 1, Math.max(0, Math.floor(ratio * (bucketCount - 1))))
      loaded[index] += 1
      if (alert.action_taken === 'BLOCKED') blocked[index] += 1
    }

    return { loaded, blocked }
  }, [alerts])

  return (
    <section className="h-16 rounded-lg border border-border-light bg-bg-panel px-[14px] py-2 shadow-subtle">
      <div className="mb-1 flex items-center justify-between gap-4">
        <p className="text-[10px] uppercase tracking-[0.09em] text-text-muted">Loaded event activity</p>
        <div className="flex items-center gap-4 text-[10px] text-text-secondary">
          <span className="inline-flex items-center gap-1.5">
            <span className="h-[7px] w-[7px] rounded-full bg-accent-cyan" />
            Loaded records
          </span>
          <span className="inline-flex items-center gap-1.5">
            <span className="h-[7px] w-[7px] rounded-full bg-severity-high-accent" />
            Blocked
          </span>
        </div>
      </div>
      <div className="h-[34px]">
        {isPending ? (
          <div className="h-[34px] w-full rounded-md bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
        ) : (
          <svg viewBox="0 0 100 34" preserveAspectRatio="none" className="h-[34px] w-full">
            <polyline
              fill="none"
              stroke="var(--color-accent-cyan)"
              strokeWidth="2"
              opacity="1"
              points={buildPolyline(series.loaded, 100, 34)}
            />
            <polyline
              fill="none"
              stroke="var(--color-severity-high-accent)"
              strokeWidth="2"
              opacity="1"
              points={buildPolyline(series.blocked, 100, 34)}
            />
          </svg>
        )}
      </div>
    </section>
  )
}
