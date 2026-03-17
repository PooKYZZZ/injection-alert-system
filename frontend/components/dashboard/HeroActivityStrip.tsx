'use client'
import { useMemo } from 'react'
import { Alert } from '@/features/alerts/types'

interface Props {
  alerts: Alert[]
  isLoading?: boolean
}

export function HeroActivityStrip({ alerts, isLoading }: Props) {
  const BUCKETS = 24
  const VB_W = 1200
  const VB_H = 28
  const PAD_X = 60
  const PAD_Y = 4

  const { allPoints, blockedPoints } = useMemo(() => {
    if (alerts.length === 0) {
      const flat = Array.from({ length: BUCKETS }, (_, i) => {
        const x = PAD_X + (i / (BUCKETS - 1)) * (VB_W - PAD_X * 2)
        return `${x.toFixed(1)},${(VB_H / 2).toFixed(1)}`
      }).join(' ')
      return { allPoints: flat, blockedPoints: flat }
    }

    const times = alerts.map(a => new Date(a.timestamp).getTime())
    const min = Math.min(...times)
    const max = Math.max(...times)
    const range = max - min || 1

    const allBuckets = new Array(BUCKETS).fill(0)
    const blockedBuckets = new Array(BUCKETS).fill(0)

    alerts.forEach(a => {
      const idx = Math.min(
        Math.floor(((new Date(a.timestamp).getTime() - min) / range) * BUCKETS),
        BUCKETS - 1
      )
      allBuckets[idx]++
      if (a.action_taken === 'BLOCKED') blockedBuckets[idx]++
    })

    const allMax = Math.max(...allBuckets, 1)
    const blockedMax = Math.max(...blockedBuckets, 1)

    const toPoints = (buckets: number[], maxVal: number) =>
      buckets
        .map((v, i) => {
          const x = PAD_X + (i / (BUCKETS - 1)) * (VB_W - PAD_X * 2)
          const y = VB_H - PAD_Y - (v / maxVal) * (VB_H - PAD_Y * 2)
          return `${x.toFixed(1)},${y.toFixed(1)}`
        })
        .join(' ')

    return {
      allPoints: toPoints(allBuckets, allMax),
      blockedPoints: toPoints(blockedBuckets, blockedMax),
    }
  }, [alerts])

  return (
    <div
      style={{
        height: '56px',
        minHeight: '56px',
        maxHeight: '56px',
        background: 'var(--color-bg-panel)',
        border: '1px solid #1e2a3d',
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
            { color: '#38bdf8', label: 'Loaded records' },
            { color: '#ef4444', label: 'Blocked' },
          ].map(({ color, label }) => (
            <span key={label} style={{ display: 'flex', alignItems: 'center', gap: '5px', fontSize: '10px', color: 'var(--color-text-muted)' }}>
              <span style={{ width: '7px', height: '7px', borderRadius: '50%', background: color, flexShrink: 0 }} />
              {label}
            </span>
          ))}
        </div>
      </div>

      {isLoading ? (
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
            stroke="#38bdf8"
            strokeWidth="4"
            strokeLinecap="round"
            strokeLinejoin="round"
            opacity="1"
          />
          <polyline
            points={blockedPoints}
            fill="none"
            stroke="#ef4444"
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
