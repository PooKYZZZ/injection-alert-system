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
import { LoadingSkeleton } from '@/components/ui/StateViews'
import type { ActivityBucket } from '@/features/stats/types'

export type TimeWindow = '1h' | '6h' | '24h' | '7d'

interface TimelineChartProps {
  buckets: ActivityBucket[]
  timeWindow?: TimeWindow
  isPending?: boolean
  hasEvents?: boolean
  consistencyWarning?: string | null
}

function CustomTooltip({
  active,
  payload,
  label,
  timeWindow,
}: {
  active?: boolean
  payload?: ReadonlyArray<{
    dataKey?: string | number
    color?: string
    name?: string | number
    value?: string | number
    payload?: { timestampEndMs?: number | null }
  }>
  label?: string | number
  timeWindow: TimeWindow
}) {
  if (!active || !payload?.length) return null

  const timestampStart = typeof label === 'number' ? label : Number(label)
  const timestampEnd = payload[0]?.payload?.timestampEndMs ?? null
  const hasValidStart = Number.isFinite(timestampStart)
  const hasValidEnd = typeof timestampEnd === 'number' && Number.isFinite(timestampEnd) && timestampEnd > timestampStart

  const formatDateTime = (value: number) =>
    new Date(value).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    })

  const displayLabel =
    hasValidStart && hasValidEnd && timeWindow === '7d'
      ? `${formatDateTime(timestampStart)} - ${new Date(timestampEnd).toLocaleTimeString('en-US', {
          hour: '2-digit',
          minute: '2-digit',
          hour12: true,
        })}`
      : hasValidStart
        ? formatDateTime(timestampStart)
        : String(label)

  return (
    <div className="w-[156px] border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] px-3 py-2">
      <p className="mb-2 text-[11px] font-semibold text-[var(--color-text-primary)]">{displayLabel}</p>
      {payload.map((entry) => (
        <div
          key={String(entry.dataKey)}
          className="grid grid-cols-[1fr_auto] items-center gap-2 text-[11px] leading-5 tabular-nums"
          style={{ color: entry.color as string }}
        >
          <span className="truncate">{String(entry.name)}</span>
          <span className="text-right font-medium">{entry.value}</span>
        </div>
      ))}
    </div>
  )
}

export function TimelineChart({
  buckets,
  timeWindow = '24h',
  isPending = false,
  hasEvents,
  consistencyWarning,
}: TimelineChartProps) {
  const processedData = useMemo(() => {
    if (!buckets || buckets.length === 0) return []

    return buckets
      .map((bucket) => {
        const timestampMs = new Date(bucket.timestamp_start).getTime()
        const timestampEndMs = bucket.timestamp_end
          ? new Date(bucket.timestamp_end).getTime()
          : bucket.bucket_width_seconds
            ? timestampMs + bucket.bucket_width_seconds * 1000
            : null
        return {
          timestampMs,
          timestampEndMs,
          allowed: bucket.allowed_count || 0,
          blocked: bucket.blocked_count || 0,
          throttled: bucket.throttled_count || 0,
        }
      })
      .sort((a, b) => a.timestampMs - b.timestampMs)
  }, [buckets])

  const formatXAxisTick = (timestampMs: number) => {
    const date = new Date(timestampMs)
    if (timeWindow === '7d') {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
    }
    return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
  }

  const inferredHasEvents = processedData.some(
    (point) => (point.allowed ?? 0) + (point.blocked ?? 0) + (point.throttled ?? 0) > 0
  )
  const hasWindowDataMismatch = Boolean(consistencyWarning)
  const isEmpty = hasEvents != null ? !hasEvents : !inferredHasEvents

  if (isPending) {
    return (
      <div className="h-[140px] w-full">
        <LoadingSkeleton rows={4} />
      </div>
    )
  }

  return (
    <div className="relative h-[140px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={processedData} margin={{ top: 5, right: 5, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="gradBlocked" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-severity-high-accent)" stopOpacity={0.32} />
              <stop offset="95%" stopColor="var(--color-severity-high-accent)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradThrottled" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-accent-amber)" stopOpacity={0.32} />
              <stop offset="95%" stopColor="var(--color-accent-amber)" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradAllowed" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="var(--color-severity-safe-accent)" stopOpacity={0.32} />
              <stop offset="95%" stopColor="var(--color-severity-safe-accent)" stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--color-text-ghost)"
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
            tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
            tickFormatter={formatXAxisTick}
            tickMargin={10}
            minTickGap={40}
          />
          <YAxis
            axisLine={false}
            tickLine={false}
            tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
            width={28}
            tickMargin={5}
          />
          <Tooltip
            offset={12}
            content={(props) => (
              <CustomTooltip
                active={props.active}
                payload={props.payload as unknown as ReadonlyArray<{
                  dataKey?: string | number
                  color?: string
                  name?: string | number
                  value?: string | number
                  payload?: { timestampEndMs?: number | null }
                }>}
                label={props.label as string | number}
                timeWindow={timeWindow}
              />
            )}
            cursor={{ stroke: 'var(--color-text-primary)', strokeOpacity: 0.2, strokeWidth: 1, strokeDasharray: '3 3' }}
          />
          {!isEmpty ? (
            <>
              <Area
                type="monotone"
                dataKey="allowed"
                stroke="var(--color-severity-safe-accent)"
                strokeWidth={1.5}
                fill="url(#gradAllowed)"
                fillOpacity={1}
                name="allowed"
                dot={false}
                activeDot={{ r: 3, fill: 'var(--color-severity-safe-accent)' }}
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="blocked"
                stroke="var(--color-severity-high-accent)"
                strokeWidth={1.5}
                fill="url(#gradBlocked)"
                fillOpacity={1}
                name="blocked"
                dot={false}
                activeDot={{ r: 3, fill: 'var(--color-severity-high-accent)' }}
                isAnimationActive={false}
              />
              <Area
                type="monotone"
                dataKey="throttled"
                stroke="var(--color-accent-amber)"
                strokeWidth={1.5}
                fill="url(#gradThrottled)"
                fillOpacity={1}
                name="throttled"
                dot={false}
                activeDot={{ r: 3, fill: 'var(--color-accent-amber)' }}
                isAnimationActive={false}
              />
            </>
          ) : null}
        </AreaChart>
      </ResponsiveContainer>
      {hasWindowDataMismatch ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-[var(--color-bg-panel)]">
          <p className="text-[11px] text-[var(--color-text-secondary)]">Data sync in progress</p>
          <p className="text-[10px] text-[var(--color-text-muted)]">{consistencyWarning}</p>
        </div>
      ) : isEmpty ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1 bg-[var(--color-bg-panel)]">
          <p className="text-[11px] text-text-muted">No events in this window</p>
          <p className="text-[10px] text-text-muted">Traffic was quiet during this period</p>
        </div>
      ) : null}
    </div>
  )
}
