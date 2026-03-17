'use client'

import { useMemo } from 'react'
import type { Alert } from '@/features/alerts/types'

interface DashboardAlertAnalyticsProps {
  alerts: Alert[]
  alertsPending: boolean
  alertsError?: Error | null
}

interface ChartPanelProps {
  title: string
  description: string
  children: React.ReactNode
}

interface DistributionRow {
  label: string
  value: number
  colorClassName?: string
  labelClassName?: string
}

function ChartPanel({ title, description, children }: ChartPanelProps) {
  return (
    <section className="h-[220px] overflow-hidden rounded-lg border border-border-light bg-bg-panel p-4 shadow-subtle">
      <div className="mb-4">
        <h2 className="text-[13px] font-semibold uppercase tracking-wider text-text-secondary">
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
    <div className="flex min-h-44 items-center justify-center rounded-lg border border-dashed border-border-light px-4 text-center text-sm text-text-secondary">
      {message}
    </div>
  )
}

function HorizontalBars({
  rows,
  emptyMessage,
  valueFormatter = (value: number) => value.toString(),
  showStub = false,
}: {
  rows: DistributionRow[]
  emptyMessage: string
  valueFormatter?: (value: number) => string
  showStub?: boolean
}) {
  const maxValue = rows.length > 0 ? Math.max(...rows.map((row) => row.value), 0) : 0

  if (rows.length === 0) {
    return <EmptyChartState message={emptyMessage} />
  }

  if (maxValue === 0 && !showStub) {
    return <EmptyChartState message={emptyMessage} />
  }

  return (
    <div className="space-y-3">
      {rows.map((row) => {
        const width =
          maxValue === 0
            ? showStub
              ? '3px'
              : '0%'
            : row.value === 0 && showStub
              ? '3px'
              : `${Math.max((row.value / maxValue) * 100, 0)}%`

        return (
          <div key={row.label} className="grid grid-cols-[minmax(0,160px)_1fr_auto] items-center gap-3">
            <span className={row.labelClassName ?? 'truncate text-xs text-text-primary'}>{row.label}</span>
            <div className="h-3 overflow-hidden rounded-full bg-bg-elevated">
              <div
                className={`h-full rounded-full ${row.colorClassName ?? 'bg-accent-blue'}`}
                style={{ width }}
              />
            </div>
            <span className="text-xs tabular-nums text-text-secondary">{valueFormatter(row.value)}</span>
          </div>
        )
      })}
    </div>
  )
}

function DashboardAlertAnalyticsSkeleton() {
  return (
    <div className="grid gap-4 xl:grid-cols-2">
      {Array.from({ length: 4 }).map((_, index) => (
        <section key={index} className="rounded-lg border border-border-light bg-bg-panel p-4 shadow-subtle">
          <div className="mb-4">
            <div className="h-4 w-36 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
            <div className="mt-2 h-3 w-52 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </div>
          <div className="space-y-3">
            {Array.from({ length: 4 }).map((__, rowIndex) => (
              <div key={rowIndex} className="grid grid-cols-[minmax(0,160px)_1fr_auto] items-center gap-3">
                <div className="h-3 w-24 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
                <div className="h-3 rounded-full bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
                <div className="h-3 w-8 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
              </div>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}

function buildDistribution(
  alerts: Alert[],
  getValue: (alert: Alert) => string | null | undefined,
  limit = 5
): DistributionRow[] {
  const counts = alerts.reduce((acc, alert) => {
    const value = getValue(alert)?.trim()
    if (!value) return acc
    acc.set(value, (acc.get(value) ?? 0) + 1)
    return acc
  }, new Map<string, number>())

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0]))
    .slice(0, limit)
    .map(([label, value]) => ({ label, value }))
}

export default function DashboardAlertAnalytics({
  alerts,
  alertsPending,
  alertsError,
}: DashboardAlertAnalyticsProps) {
  const { highThreshold, mediumThreshold } = useMemo(() => {
    let high = 0.8
    let medium = 0.5

    const sampleWithThresholds = alerts.find(
      (a) => (a as any)?.mlHealthData?.thresholds != null
    ) as any

    const thresholds = sampleWithThresholds?.mlHealthData?.thresholds
    if (thresholds) {
      if (typeof thresholds.high === 'number') high = thresholds.high
      if (typeof thresholds.medium === 'number') medium = thresholds.medium
    }

    return { highThreshold: high, mediumThreshold: medium }
  }, [alerts])

  const actionBreakdown = useMemo(() => {
    const blocked = alerts.filter((alert) => alert.action_taken === 'BLOCKED').length
    const allowed = alerts.filter((alert) => alert.action_taken === 'ALLOWED').length
    const total = blocked + allowed
    const blockedPct = total > 0 ? (blocked / total) * 100 : 0

    return { blocked, allowed, total, blockedPct }
  }, [alerts])

  const predictionDistribution = useMemo(() => {
    return buildDistribution(alerts, (alert) => alert.prediction, 6).map((row) => ({
      ...row,
      colorClassName:
        row.label === 'Normal'
          ? 'bg-slate-700'
          : row.label === 'SQL Injection'
            ? 'bg-accent-purple'
            : 'bg-severity-high-accent',
    }))
  }, [alerts])

  const topPaths = useMemo(
    () =>
      buildDistribution(alerts, (alert) => alert.request_path, 5).map((row) => ({
        ...row,
        colorClassName: 'bg-accent-blue',
        labelClassName: 'truncate font-mono text-xs text-text-primary',
      })),
    [alerts]
  )

  const confidenceBands = useMemo(() => {
    const counts = { high: 0, medium: 0, low: 0 }
    for (const alert of alerts) {
      if (alert.confidence > highThreshold) {
        counts.high += 1
      } else if (alert.confidence >= mediumThreshold) {
        counts.medium += 1
      } else {
        counts.low += 1
      }
    }

    const highPct = Math.round(highThreshold * 100)
    const mediumPct = Math.round(mediumThreshold * 100)

    return [
      { label: `High > ${highPct}%`, value: counts.high, colorClassName: 'bg-accent-purple' },
      { label: `Medium ${mediumPct}–${highPct}%`, value: counts.medium, colorClassName: 'bg-accent-yellow' },
      { label: `Low < ${mediumPct}%`, value: counts.low, colorClassName: 'bg-severity-safe-accent' },
    ]
  }, [alerts, highThreshold, mediumThreshold])

  if (alertsPending) {
    return <DashboardAlertAnalyticsSkeleton />
  }

  if (alertsError) {
    return (
      <div className="rounded-lg border border-severity-high-border bg-severity-high-bg p-4">
        <p className="text-sm font-medium text-severity-high-text">Failed to load dashboard analytics.</p>
        <p className="mt-1 text-xs text-text-secondary">{alertsError.message}</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="grid gap-4 xl:grid-cols-2">
        <ChartPanel
          title="Blocked vs Allowed"
          description="Action counts from the currently loaded alerts."
        >
          {actionBreakdown.total > 0 ? (
            <div className="flex min-h-36 items-center justify-between gap-6">
              <div
                className="relative flex h-28 w-28 items-center justify-center rounded-full"
                style={{
                  background: `conic-gradient(var(--color-severity-blocked-accent) 0 ${actionBreakdown.blockedPct}%, var(--color-severity-safe-accent) ${actionBreakdown.blockedPct}% 100%)`,
                }}
              >
                <div className="flex h-16 w-16 flex-col items-center justify-center rounded-full bg-bg-panel text-sm font-semibold text-text-primary">
                  <span>
                    {actionBreakdown.total > 0 ? `${Math.round(actionBreakdown.blockedPct)}%` : '—'}
                  </span>
                  <span className="text-[10px] font-normal text-text-muted">blocked</span>
                </div>
              </div>
              <div className="space-y-3 text-sm">
                <div className="flex items-center gap-2 text-text-primary">
                  <span className="h-2.5 w-2.5 rounded-full bg-severity-blocked-accent" />
                  <span>Blocked</span>
                  <span className="tabular-nums text-text-secondary">{actionBreakdown.blocked}</span>
                </div>
                <div className="flex items-center gap-2 text-text-primary">
                  <span className="h-2.5 w-2.5 rounded-full bg-severity-safe-accent" />
                  <span>Allowed</span>
                  <span className="tabular-nums text-text-secondary">{actionBreakdown.allowed}</span>
                </div>
              </div>
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
            emptyMessage="No prediction labels are available in the current loaded alerts."
          />
        </ChartPanel>

        <ChartPanel
          title="Top Targeted Paths"
          description="Request paths ranked from the currently loaded alerts."
        >
          <HorizontalBars
            rows={topPaths}
            emptyMessage="No request paths are available in the current loaded alerts."
          />
        </ChartPanel>

        <ChartPanel
          title="ML Confidence Bands"
          description="Confidence score distribution across loaded alerts."
        >
          <HorizontalBars
            rows={confidenceBands}
            emptyMessage="No confidence values are available in the current loaded alerts."
            showStub
          />
          {alerts.length > 0 && confidenceBands[0].value === alerts.length ? (
            <p className="mt-3 text-[9px] text-text-muted">
              All {alerts.length} requests scored high confidence.
            </p>
          ) : null}
        </ChartPanel>
      </div>
    </div>
  )
}
