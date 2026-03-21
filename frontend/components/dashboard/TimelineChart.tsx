'use client'

import { useMemo } from 'react'
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts'
import type { TooltipContentProps } from 'recharts'
import { motion } from 'motion/react'
import { LoadingSkeleton } from '@/components/ui/StateViews'
import type { ActivityBucket } from '@/features/stats/types'

export type TimeWindow = '1h' | '6h' | '24h' | '7d'

interface TimelineChartProps {
  buckets: ActivityBucket[]
  timeWindow?: TimeWindow
  isLoading?: boolean
}

const SERIES = [
  { key: 'allowed',   color: '#4ade80', label: 'allowed'   },
  { key: 'blocked',   color: '#f87171', label: 'blocked'   },
  { key: 'throttled', color: '#fbbf24', label: 'throttled' },
] as const

const CustomTooltip = ({ active, payload, label }: TooltipContentProps) => {
  if (!active || !payload?.length) return null
  return (
    <div
      style={{
        background: '#111827',
        border: '1px solid #1e2a3d',
        borderRadius: 6,
        padding: '8px 12px',
        fontSize: 11,
        minWidth: 130,
      }}
    >
      <p style={{ color: '#475569', marginBottom: 6, fontSize: 10 }}>{label}</p>
      {payload.map((entry) => (
        <div
          key={String(entry.dataKey)}
          style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 3 }}
        >
          <div
            style={{
              width: 7,
              height: 7,
              borderRadius: '50%',
              background: entry.color as string,
              flexShrink: 0,
            }}
          />
          <span style={{ color: '#94a3b8', textTransform: 'capitalize' }}>
            {entry.name}
          </span>
          <span
            style={{
              color: entry.color as string,
              fontWeight: 500,
              marginLeft: 'auto',
              paddingLeft: 12,
            }}
          >
            {entry.value}
          </span>
        </div>
      ))}
    </div>
  )
}

export function TimelineChart({
  buckets,
  timeWindow = '24h',
  isLoading = false,
}: TimelineChartProps) {
  if (isLoading) {
    return (
      <div className="h-[140px] w-full">
        <LoadingSkeleton rows={4} />
      </div>
    )
  }

  const processedData = useMemo(() => {
    if (!buckets || buckets.length === 0) return []

    return buckets
      .map((bucket) => ({
        timestampMs: new Date(bucket.timestamp_start).getTime(),
        allowed: bucket.allowed_count || 0,
        blocked: bucket.blocked_count || 0,
        throttled: bucket.throttled_count || 0,
      }))
      .sort((a, b) => a.timestampMs - b.timestampMs)
  }, [buckets])

  const formatXAxisTick = (timestampMs: number) => {
    const date = new Date(timestampMs)
    if (timeWindow === '7d') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="h-[140px] w-full"
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={processedData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            {SERIES.map(({ key, color }) => (
              <linearGradient key={key} id={`grad-${key}`} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={color} stopOpacity={0.08} />
                <stop offset="95%" stopColor={color} stopOpacity={0}    />
              </linearGradient>
            ))}
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#1e2a3d"
            vertical={false}
            strokeOpacity={0.5}
          />
          <XAxis
            dataKey="timestampMs"
            type="number"
            domain={['dataMin', 'dataMax']}
            scale="time"
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#475569', fontSize: 10 }}
            tickFormatter={formatXAxisTick}
            tickMargin={10}
            minTickGap={40}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: '#475569', fontSize: 10 }}
            width={28}
            tickMargin={5}
          />
          <Tooltip
            labelFormatter={(label) =>
              typeof label === 'number'
                ? new Date(label).toLocaleString('en-US', {
                    month: 'short',
                    day: 'numeric',
                    hour: 'numeric',
                    minute: '2-digit',
                  })
                : label
            }
            content={CustomTooltip}
            cursor={{ stroke: '#ffffff', strokeOpacity: 0.2, strokeWidth: 1, strokeDasharray: '3 3' }}
          />

          {SERIES.map(({ key, color, label }) => (
            <Area
              key={key}
              type="monotone"
              dataKey={key}
              stroke={color}
              strokeWidth={1.5}
              fill={`url(#grad-${key})`}
              fillOpacity={1}
              name={label}
              dot={false}
              activeDot={{ r: 4, strokeWidth: 2, stroke: '#ffffff', fill: color }}
              isAnimationActive={false}
            />
          ))}
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  )
}
