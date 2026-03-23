'use client'

import { useMemo } from 'react'
import {
  ComposedChart,
  Area,
  Line,
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

interface TooltipEntry {
  dataKey?: string | number
  color?: string
  name?: string | number
  value?: string | number
  payload?: { timestampEndMs?: number | null }
}

export function dedupeTooltipPayload(payload: ReadonlyArray<TooltipEntry>): TooltipEntry[] {
  const seen = new Map<string | number, TooltipEntry>()
  const passthrough: TooltipEntry[] = []

  for (const entry of payload) {
    if (entry.dataKey == null) {
      passthrough.push(entry)
      continue
    }
    seen.set(entry.dataKey, entry)
  }

  return [...passthrough, ...seen.values()]
}

export function buildUniqueDayTicks(timestamps: number[]): number[] {
  const dayToRange = new Map<string, { min: number; max: number }>()
  for (const timestampMs of timestamps) {
    if (!Number.isFinite(timestampMs)) continue
    const date = new Date(timestampMs)
    const dayKey = `${date.getFullYear()}-${date.getMonth()}-${date.getDate()}`
    const existing = dayToRange.get(dayKey)
    if (!existing) {
      dayToRange.set(dayKey, { min: timestampMs, max: timestampMs })
    } else {
      if (timestampMs < existing.min) existing.min = timestampMs
      if (timestampMs > existing.max) existing.max = timestampMs
    }
  }
  return Array.from(dayToRange.values())
    .map(({ min, max }) => min + Math.floor((max - min) / 2))
    .sort((a, b) => a - b)
}

function useCSSColor(variable: string): string {
  if (typeof window === 'undefined') return '#888888'
  try {
    const value = getComputedStyle(document.documentElement).getPropertyValue(variable).trim()
    return value || '#888888'
  } catch {
    return '#888888'
  }
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean
  payload?: ReadonlyArray<TooltipEntry>
  label?: string | number
}) {
  if (!active || !payload?.length) return null

  const uniquePayload = dedupeTooltipPayload(payload)

  const timestampStart = typeof label === 'number' ? label : Number(label)
  const timestampEnd = payload[0]?.payload?.timestampEndMs ?? null
  const hasValidStart = Number.isFinite(timestampStart)
  const hasValidEnd = typeof timestampEnd === 'number' && Number.isFinite(timestampEnd) && timestampEnd > timestampStart

  const startDate = hasValidStart ? new Date(timestampStart) : null
  const endDate = hasValidEnd ? new Date(timestampEnd) : null

  const formatDateTime = (value: Date) =>
    value.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    })

  const formatTime = (value: Date) =>
    value.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      hour12: true,
    })

  const displayLabel =
    startDate && endDate
      ? `${formatDateTime(startDate)} - ${formatTime(endDate)}`
      : startDate
        ? formatDateTime(startDate)
        : String(label)

  return (
    <div className="w-[170px] rounded-md border border-[#30363d] bg-[rgba(13,17,23,0.82)] px-2.5 py-2 shadow-[0_20px_25px_-5px_rgba(0,0,0,0.5)] backdrop-blur-md">
      <p className="mb-1.5 border-b border-[#30363d] pb-1 text-[10px] font-medium text-[#7d8590]">{displayLabel}</p>
      {uniquePayload.map((entry) => (
        <div
          key={String(entry.dataKey)}
          className="grid grid-cols-[1fr_auto] items-center gap-2 py-0.5 text-[11px] leading-4 tabular-nums"
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

  const xAxisConfig = useMemo(() => {
    const formatTick = (timestampMs: number) => {
      const date = new Date(timestampMs)
      if (timeWindow === '7d') {
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      }
      return date.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true })
    }

    if (timeWindow !== '7d') {
      return {
        tickFormatter: formatTick,
        ticks: undefined as number[] | undefined,
        interval: undefined as number | undefined,
        domain: ['dataMin', 'dataMax'] as [string, string],
      }
    }

    const uniqueDayTicks = buildUniqueDayTicks(processedData.map((point) => point.timestampMs))

    return {
      tickFormatter: formatTick,
      ticks: uniqueDayTicks,
      interval: 0,
      domain: ['dataMin', 'dataMax'] as [string, string],
    }
  }, [processedData, timeWindow])

  const colorBlocked = useCSSColor('--color-severity-high-accent')
  const colorThrottled = useCSSColor('--color-accent-amber')
  const colorAllowed = useCSSColor('--color-severity-safe-accent')

  if (isPending) {
    return (
      <div className="h-[140px] w-full">
        <LoadingSkeleton rows={4} />
      </div>
    )
  }

  const inferredHasEvents = processedData.some(
    (point) => (point.allowed ?? 0) + (point.blocked ?? 0) + (point.throttled ?? 0) > 0
  )
  const hasWindowDataMismatch = Boolean(consistencyWarning)
  const isEmpty = hasEvents != null ? !hasEvents : !inferredHasEvents
  const chartMargin =
    timeWindow === '7d'
      ? { top: 5, right: 5, left: -20, bottom: 0 }
      : { top: 5, right: 5, left: -20, bottom: 0 }

  return (
    <div className="relative h-[140px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={processedData} margin={chartMargin}>
          <defs>
            <linearGradient id="gradBlocked" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colorBlocked} stopOpacity={0.05} />
              <stop offset="95%" stopColor={colorBlocked} stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradThrottled" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colorThrottled} stopOpacity={0.05} />
              <stop offset="95%" stopColor={colorThrottled} stopOpacity={0} />
            </linearGradient>
            <linearGradient id="gradAllowed" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor={colorAllowed} stopOpacity={0.05} />
              <stop offset="95%" stopColor={colorAllowed} stopOpacity={0} />
            </linearGradient>
          </defs>

          <CartesianGrid
            strokeDasharray="3 3"
            stroke="var(--color-text-ghost)"
            vertical={false}
            strokeOpacity={0.15}
          />
          <XAxis
            dataKey="timestampMs"
            type="number"
            domain={xAxisConfig.domain}
            scale="time"
            axisLine={false}
            tickLine={false}
            tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
            tickFormatter={xAxisConfig.tickFormatter}
            ticks={xAxisConfig.ticks}
            interval={xAxisConfig.interval}
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
                payload={props.payload as ReadonlyArray<{
                  dataKey?: string | number
                  color?: string
                  name?: string | number
                  value?: string | number
                  payload?: { timestampEndMs?: number | null }
                }>}
                label={props.label as string | number}
              />
            )}
            cursor={{ stroke: 'var(--color-text-primary)', strokeOpacity: 0.2, strokeWidth: 1, strokeDasharray: '3 3' }}
          />
          {!isEmpty ? (
            <>
              <Area
                type="monotone"
                dataKey="blocked"
                stroke="transparent"
                fill="url(#gradBlocked)"
                fillOpacity={1}
                name="blocked"
                dot={false}
                isAnimationActive
                animationDuration={550}
                animationEasing="ease-out"
                connectNulls={false}
              />
              <Area
                type="monotone"
                dataKey="throttled"
                stroke="transparent"
                fill="url(#gradThrottled)"
                fillOpacity={1}
                name="throttled"
                dot={false}
                isAnimationActive
                animationDuration={550}
                animationEasing="ease-out"
                connectNulls={false}
              />
              <Area
                type="monotone"
                dataKey="allowed"
                stroke="transparent"
                fill="url(#gradAllowed)"
                fillOpacity={1}
                name="allowed"
                dot={false}
                isAnimationActive
                animationDuration={550}
                animationEasing="ease-out"
                connectNulls={false}
              />
              <Line
                type="monotone"
                dataKey="blocked"
                stroke={colorBlocked}
                strokeWidth={2.25}
                dot={false}
                activeDot={{ r: 4, fill: colorBlocked, stroke: '#0f172a', strokeWidth: 2 }}
                connectNulls={false}
                isAnimationActive
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <Line
                type="monotone"
                dataKey="throttled"
                stroke={colorThrottled}
                strokeWidth={2.25}
                dot={false}
                activeDot={{ r: 4, fill: colorThrottled, stroke: '#0f172a', strokeWidth: 2 }}
                connectNulls={false}
                isAnimationActive
                strokeLinecap="round"
                strokeLinejoin="round"
              />
              <Line
                type="monotone"
                dataKey="allowed"
                stroke={colorAllowed}
                strokeWidth={2.25}
                dot={false}
                activeDot={{ r: 4, fill: colorAllowed, stroke: '#0f172a', strokeWidth: 2 }}
                connectNulls={false}
                isAnimationActive
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </>
          ) : null}
        </ComposedChart>
      </ResponsiveContainer>
      {hasWindowDataMismatch ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
          <p className="text-[11px] text-[var(--color-text-secondary)]">Data sync in progress</p>
          <p className="text-[10px] text-[var(--color-text-muted)]">{consistencyWarning}</p>
        </div>
      ) : isEmpty ? (
        <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
          <p className="text-[11px] text-[var(--color-text-secondary)]">No events in this window</p>
          <p className="text-[10px] text-[var(--color-text-muted)]">Traffic was quiet during this period</p>
        </div>
      ) : null}
    </div>
  )
}
