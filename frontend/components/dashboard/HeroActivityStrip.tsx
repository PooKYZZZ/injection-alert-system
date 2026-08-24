'use client'
import { useMemo, useEffect } from 'react'
import { Alert } from '@/features/alerts/types'
import type { ActivityBucket } from '@/features/stats/types'
import { parseApiTimestamp } from '@/lib/date-time'

interface Props {
  alerts?: Alert[]
  activityBuckets?: ActivityBucket[]
  isPending?: boolean
  /** Callback to report the actual data source used for rendering */
  onDataSourceDetected?: (isDbBacked: boolean) => void
}

export function HeroActivityStrip({ alerts, activityBuckets, isPending, onDataSourceDetected }: Props) {
  const BUCKETS = 24
  const VB_W = 1200
  const VB_H = 28
  const PAD_X = 80
  const PAD_Y = 4

  // Determine if we're using real DB-backed data
  const isDbBacked = !!(activityBuckets && activityBuckets.length > 0)

  // Report the actual data source to parent for subtitle alignment
  useEffect(() => {
    if (onDataSourceDetected) {
      onDataSourceDetected(isDbBacked)
    }
  }, [isDbBacked, onDataSourceDetected])

  const { allPoints, blockedPoints } = useMemo(() => {
    // Priority: use activity_buckets from stats if available (real DB data)
    // Otherwise fall back to computing from alerts
    if (activityBuckets && activityBuckets.length > 0) {
      // activity_buckets has 24 buckets with real counts
      const allCounts = activityBuckets.map(b => b.total_count)
      const blockedCounts = activityBuckets.map(b => b.blocked_count)

      // FIX: Use shared y-scale for both lines so they are visually comparable
      const sharedMax = Math.max(...allCounts, ...blockedCounts, 1)

      const toPoints = (counts: number[], maxVal: number) =>
        counts
          .map((v, i) => {
            const x = PAD_X + (i / (BUCKETS - 1)) * (VB_W - PAD_X * 2)
            const y = VB_H - PAD_Y - (v / maxVal) * (VB_H - PAD_Y * 2)
            return `${x.toFixed(1)},${y.toFixed(1)}`
          })
          .join(' ')

      return {
        allPoints: toPoints(allCounts, sharedMax),
        blockedPoints: toPoints(blockedCounts, sharedMax),
      }
    }

    // Fall back to alerts-based computation
    if (!alerts || alerts.length === 0) {
      const flat = Array.from({ length: BUCKETS }, (_, i) => {
        const x = PAD_X + (i / (BUCKETS - 1)) * (VB_W - PAD_X * 2)
        return `${x.toFixed(1)},${(VB_H / 2).toFixed(1)}`
      }).join(' ')
      return { allPoints: flat, blockedPoints: flat }
    }

    const times = alerts
      .map((alert) => parseApiTimestamp(alert.timestamp)?.getTime() ?? Number.NaN)
      .filter(Number.isFinite)
    if (times.length === 0) {
      const flat = Array.from({ length: BUCKETS }, (_, i) => {
        const x = PAD_X + (i / (BUCKETS - 1)) * (VB_W - PAD_X * 2)
        return `${x.toFixed(1)},${(VB_H / 2).toFixed(1)}`
      }).join(' ')
      return { allPoints: flat, blockedPoints: flat }
    }

    const min = Math.min(...times)
    const max = Math.max(...times)
    const range = max - min || 1

    const allBuckets = new Array(BUCKETS).fill(0)
    const blockedBuckets = new Array(BUCKETS).fill(0)

    alerts.forEach(a => {
      const timestampMs = parseApiTimestamp(a.timestamp)?.getTime()
      if (timestampMs == null || Number.isNaN(timestampMs)) return
      const idx = Math.min(
        Math.floor(((timestampMs - min) / range) * BUCKETS),
        BUCKETS - 1
      )
      allBuckets[idx]++
      if (a.action_taken === 'BLOCKED') blockedBuckets[idx]++
    })

    // FIX: Use shared y-scale for both lines so they are visually comparable
    const sharedMax = Math.max(...allBuckets, ...blockedBuckets, 1)

    const toPoints = (buckets: number[], maxVal: number) =>
      buckets
        .map((v, i) => {
          const x = PAD_X + (i / (BUCKETS - 1)) * (VB_W - PAD_X * 2)
          const y = VB_H - PAD_Y - (v / maxVal) * (VB_H - PAD_Y * 2)
          return `${x.toFixed(1)},${y.toFixed(1)}`
        })
        .join(' ')

    return {
      allPoints: toPoints(allBuckets, sharedMax),
      blockedPoints: toPoints(blockedBuckets, sharedMax),
    }
  }, [alerts, activityBuckets])

  return (
    <div
      style={{
        height: '56px',
        minHeight: '56px',
        maxHeight: '56px',
        background: 'var(--color-bg-panel)',
        border: '1px solid var(--color-text-ghost)',
        borderRadius: '8px',
        padding: '8px 14px 6px',
        display: 'flex',
        flexDirection: 'column',
        gap: '6px',
        marginBottom: '12px',
        overflow: 'hidden',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexShrink: 0 }}>
        <span style={{
          fontSize: '10px',
          textTransform: 'uppercase',
          letterSpacing: '0.08em',
          color: 'var(--color-text-muted)',
          fontWeight: 600,
        }}>
          Loaded event activity
        </span>
        <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
          {[
            { color: 'var(--color-accent-blue)', label: 'Loaded records' },
            { color: 'var(--color-severity-high-accent)', label: 'Blocked' },
          ].map(({ color, label }) => (
            <span key={label} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '10px', color: 'var(--color-text-muted)' }}>
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: color, flexShrink: 0 }} />
              {label}
            </span>
          ))}
        </div>
      </div>

      {isPending ? (
        <div style={{
          flex: 1,
          background: 'var(--color-bg-elevated)',
          borderRadius: '3px',
          animation: 'skeleton-pulse 1.5s ease-in-out infinite',
        }} />
      ) : (
        <svg
          width="100%"
          height="22"
          viewBox={`0 0 ${VB_W} ${VB_H}`}
          preserveAspectRatio="none"
          style={{ display: 'block', flexShrink: 0 }}
        >
          <polyline
            points={allPoints}
            fill="none"
            stroke="var(--color-accent-blue)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="1"
          />
          <polyline
            points={blockedPoints}
            fill="none"
            stroke="var(--color-severity-high-accent)"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="1"
          />
        </svg>
      )}
    </div>
  )
}

export default HeroActivityStrip

