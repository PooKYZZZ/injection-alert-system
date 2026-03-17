'use client'

import { useMemo } from 'react'
import { useSearchParams } from 'next/navigation'
import { useAlerts } from '@/features/alerts/queries'
import { useMLHealth } from '@/features/ml-health/queries'
import type { Alert } from '@/features/alerts/types'
import type { DashboardFilters, SeverityFilter, TimeRange } from '@/lib/searchParams'

interface DistributionRow {
  label: string
  value: number
}

interface ChartPanelProps {
  title: string
  description: string
  children: React.ReactNode
}

function ChartPanel({ title, description, children }: ChartPanelProps) {
  return (
    <section className="rounded-sm border border-border-light bg-surface-light p-4 shadow-subtle">
      <div className="mb-4">
        <h2 className="text-[13px] font-semibold uppercase tracking-wider text-text-muted">
          {title}
        </h2>
        <p className="mt-1 text-xs text-text-muted">{description}</p>
      </div>
      {children}
    </section>
  )
}

function EmptyChartState({ message }: { message: string }) {
  return (
    <div className="flex min-h-44 items-center justify-center rounded-sm border border-dashed border-border-light px-4 text-center text-sm text-text-muted">
      {message}
    </div>
  )
}

function HorizontalBars({
  rows,
  barClassName,
  emptyMessage,
  valueFormatter = (value: number) => value.toString(),
}: {
  rows: DistributionRow[]
  barClassName: string
  emptyMessage: string
  valueFormatter?: (value: number) => string
}) {
  const maxValue = rows.length > 0 ? Math.max(...rows.map((row) => row.value)) : 0

  if (rows.length === 0 || maxValue === 0) {
    return <EmptyChartState message={emptyMessage} />
  }

  return (
    <div className="space-y-3">
      {rows.map((row) => (
        <div key={row.label} className="grid grid-cols-[minmax(0,160px)_1fr_auto] items-center gap-3">
          <span className="truncate text-xs text-text-main">{row.label}</span>
          <div className="h-3 overflow-hidden rounded-full bg-[#1B2940]">
            <div
              className={`h-full rounded-full ${barClassName}`}
              style={{ width: `${(row.value / maxValue) * 100}%` }}
            />
          </div>
          <span className="text-xs tabular-nums text-text-muted">{valueFormatter(row.value)}</span>
        </div>
      ))}
    </div>
  )
}

function formatBandLabel(value: number | null, prefix: '< ' | '> '): string {
  return value === null ? 'Unavailable' : `${prefix}${Math.round(value * 100)}%`
}

function buildFilters(searchParams: Pick<URLSearchParams, 'get'> | null): DashboardFilters {
  return {
    severity: (searchParams?.get('severity') ?? 'ALL') as SeverityFilter,
    timeRange: (searchParams?.get('timeRange') ?? '24h') as TimeRange,
    search: searchParams?.get('search') ?? '',
  }
}

function buildDistribution(
  alerts: Alert[],
  getValue: (alert: Alert) => string | null | undefined,
  limit = 5
): DistributionRow[] {
  const counts = new Map<string, number>()

  for (const alert of alerts) {
    const value = getValue(alert)?.trim()
    if (!value) continue
    counts.set(value, (counts.get(value) ?? 0) + 1)
  }

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([label, value]) => ({ label, value }))
}

export default function DashboardAlertAnalytics() {
  const searchParams = useSearchParams()
  const filters = buildFilters(searchParams)
  const { data, isPending, isError, error } = useAlerts(filters)
  const { data: mlHealth } = useMLHealth()

  const alerts = data?.items ?? []

  const actionBreakdown = useMemo(() => {
    const blocked = alerts.filter((alert) => alert.action_taken === 'BLOCKED').length
    const allowed = alerts.filter((alert) => alert.action_taken === 'ALLOWED').length
    const throttled = alerts.filter((alert) => alert.action_taken === 'THROTTLED').length
    const total = blocked + allowed

    return {
      blocked,
      allowed,
      throttled,
      total,
      blockedPct: total > 0 ? Math.round((blocked / total) * 100) : 0,
    }
  }, [alerts])

  const predictionDistribution = useMemo(
    () => buildDistribution(alerts, (alert) => alert.prediction, 6),
    [alerts]
  )

  const topPaths = useMemo(
    () => buildDistribution(alerts, (alert) => alert.request_path, 5),
    [alerts]
  )

  const confidenceBands = useMemo(() => {
    const lowBoundary = mlHealth?.thresholds.low ?? null
    const highBoundary = mlHealth?.thresholds.high ?? mlHealth?.thresholds.medium ?? null

    if (lowBoundary === null || highBoundary === null) {
      return null
    }

    const counts = { low: 0, medium: 0, high: 0 }
    for (const alert of alerts) {
      if (alert.confidence < lowBoundary) {
        counts.low += 1
      } else if (alert.confidence > highBoundary) {
        counts.high += 1
      } else {
        counts.medium += 1
      }
    }

    return {
      rows: [
        { label: formatBandLabel(highBoundary, '> '), value: counts.high },
        {
          label: `${Math.round(lowBoundary * 100)}%\u2013${Math.round(highBoundary * 100)}%`,
          value: counts.medium,
        },
        { label: formatBandLabel(lowBoundary, '< '), value: counts.low },
      ],
    }
  }, [alerts, mlHealth?.thresholds.high, mlHealth?.thresholds.low, mlHealth?.thresholds.medium])

  if (isPending) {
    return (
      <div className="grid gap-4 xl:grid-cols-2">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="h-72 animate-pulse rounded-sm border border-border-light bg-surface-light shadow-subtle"
          />
        ))}
      </div>
    )
  }

  if (isError) {
    return (
      <div className="rounded-sm border border-status-high/50 bg-status-high/10 p-4">
        <p className="text-sm font-medium text-status-high">Failed to load dashboard analytics</p>
        <p className="mt-1 text-xs text-text-muted">
          {error instanceof Error ? error.message : 'Unknown error'}
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <p className="text-xs text-text-muted">
        These panels are derived from the alerts currently loaded in this view, not backend-wide aggregate analytics.
      </p>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartPanel
          title="Blocked vs Allowed"
          description="Action counts from the currently loaded alerts."
        >
          {actionBreakdown.total > 0 ? (
            <div className="flex min-h-44 flex-col items-center justify-center gap-4">
              <div
                className="relative flex h-40 w-40 items-center justify-center rounded-full"
                style={{
                  background: `conic-gradient(#DC6803 0 ${actionBreakdown.blockedPct}%, #2E90FA ${actionBreakdown.blockedPct}% 100%)`,
                }}
              >
                <div className="flex h-24 w-24 flex-col items-center justify-center rounded-full bg-surface-light">
                  <span className="text-2xl font-semibold text-text-main">
                    {actionBreakdown.blockedPct}%
                  </span>
                  <span className="text-xs text-text-muted">blocked</span>
                </div>
              </div>

              <div className="flex flex-wrap items-center justify-center gap-4 text-xs text-text-muted">
                <span className="inline-flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#DC6803]" />
                  Blocked {actionBreakdown.blocked}
                </span>
                <span className="inline-flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#2E90FA]" />
                  Allowed {actionBreakdown.allowed}
                </span>
              </div>

              {actionBreakdown.throttled > 0 && (
                <p className="text-xs text-text-muted">
                  {actionBreakdown.throttled} throttled alert{actionBreakdown.throttled === 1 ? '' : 's'} omitted from this blocked-vs-allowed split.
                </p>
              )}
            </div>
          ) : (
            <EmptyChartState message="No blocked or allowed alerts are present in the current loaded set." />
          )}
        </ChartPanel>

        <ChartPanel
          title="Attack Type Distribution"
          description="Prediction labels across the currently loaded alerts."
        >
          <HorizontalBars
            rows={predictionDistribution}
            barClassName="bg-status-high"
            emptyMessage="No prediction labels are available in the current loaded alerts."
          />
        </ChartPanel>

        <ChartPanel
          title="Top Targeted Paths"
          description="Request paths ranked from the currently loaded alerts."
        >
          {topPaths.length > 0 ? (
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_220px]">
              <HorizontalBars
                rows={topPaths}
                barClassName="bg-[#2E90FA]"
                emptyMessage="No request paths are available in the current loaded alerts."
              />

              <div className="rounded-sm border border-border-light bg-[#16233A] p-3">
                <h3 className="text-xs font-semibold uppercase tracking-wider text-text-muted">
                  Top Targeted Paths
                </h3>
                <ol className="mt-3 space-y-2">
                  {topPaths.map((row, index) => (
                    <li key={row.label} className="flex items-start justify-between gap-3 text-xs">
                      <span className="inline-flex min-w-0 items-start gap-2 text-text-main">
                        <span className="tabular-nums text-text-muted">{index + 1}.</span>
                        <span className="truncate font-mono">{row.label}</span>
                      </span>
                      <span className="tabular-nums text-text-muted">{row.value}</span>
                    </li>
                  ))}
                </ol>
              </div>
            </div>
          ) : (
            <EmptyChartState message="No request paths are available in the current loaded alerts." />
          )}
        </ChartPanel>

        <ChartPanel
          title="ML Confidence Bands"
          description="Band counts using the current ML health thresholds."
        >
          {confidenceBands ? (
            <HorizontalBars
              rows={[
                { label: `High ${confidenceBands.rows[0].label}`, value: confidenceBands.rows[0].value },
                { label: `Medium ${confidenceBands.rows[1].label}`, value: confidenceBands.rows[1].value },
                { label: `Low ${confidenceBands.rows[2].label}`, value: confidenceBands.rows[2].value },
              ]}
              barClassName="bg-[#7F56D9]"
              emptyMessage="No confidence values are available in the current loaded alerts."
            />
          ) : (
            <EmptyChartState message="Confidence bands are unavailable because current threshold values were not returned by ML health." />
          )}
        </ChartPanel>
      </div>
    </div>
  )
}
