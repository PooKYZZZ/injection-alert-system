'use client'

import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts'
import { motion } from 'motion/react'
import { LoadingSkeleton } from '@/components/ui/StateViews'
import type { ActivityBucket } from '@/features/stats/types'

export type TimeWindow = '1h' | '6h' | '24h' | '7d'

interface TimelineChartProps {
  buckets: ActivityBucket[]
  timeWindow?: TimeWindow
  isLoading?: boolean
}

function formatBucketTime(timestamp: Date): string {
  const date = new Date(timestamp)
  // Use UTC methods to avoid server/client timezone mismatch during Next.js hydration
  const hours = date.getUTCHours()
  const period = hours >= 12 ? 'pm' : 'am'
  const displayHour = hours % 12 || 12
  return `${displayHour}${period}`
}

export function TimelineChart({ buckets, timeWindow = '24h', isLoading = false }: TimelineChartProps) {
  if (isLoading) {
    return (
      <div className="h-[120px] w-full">
        <LoadingSkeleton rows={4} />
      </div>
    )
  }

  const data = buckets.map((bucket) => ({
    time: formatBucketTime(bucket.timestamp_start),
    total_count: bucket.total_count,
    blocked_count: bucket.blocked_count,
  }))

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="h-[120px] w-full"
    >
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="colorTotal" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#38bdf8" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#38bdf8" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="colorBlocked" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f87171" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#f87171" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#30363d" vertical={false} />
          <XAxis
            dataKey="time"
            axisLine={{ stroke: '#30363d' }}
            tickLine={false}
            tick={{ fill: '#484f58', fontSize: 10 }}
          />
          <YAxis
            axisLine={{ stroke: '#30363d' }}
            tickLine={false}
            tick={{ fill: '#484f58', fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{ backgroundColor: '#161b22', border: '1px solid #30363d', fontSize: '11px' }}
            itemStyle={{ fontSize: '11px' }}
            labelStyle={{ color: '#8b949e', fontSize: '10px' }}
          />
          <Area
            type="monotone"
            dataKey="total_count"
            stroke="#38bdf8"
            fillOpacity={1}
            fill="url(#colorTotal)"
            strokeWidth={1.5}
            name="Total"
          />
          <Area
            type="monotone"
            dataKey="blocked_count"
            stroke="#f87171"
            fillOpacity={1}
            fill="url(#colorBlocked)"
            strokeWidth={1.5}
            name="Blocked"
          />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
  )
}
