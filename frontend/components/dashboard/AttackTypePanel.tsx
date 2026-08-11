'use client'

import { useState } from 'react'
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { cn } from '@/lib/utils'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'
import { type AlertPrediction } from '@/features/alerts/contract'

interface AttackTypePanelProps {
  countsByLabel: Partial<Record<AlertPrediction, number>>
  isPending?: boolean
}

type AttackTypeView = 'bar' | 'pie'

interface AttackTypeEntry {
  label: AlertPrediction
  count: number
}

const colorMap: Record<AlertPrediction, string> = {
  'SQL Injection': 'var(--color-chart-primary)',
  'Code Injection': 'var(--color-chart-secondary)',
  'Other Attacks': 'var(--color-chart-tertiary)',
  'Normal': 'var(--color-severity-safe-accent)',
}

const labelOrder: AlertPrediction[] = [
  'SQL Injection',
  'Code Injection',
  'Other Attacks',
  'Normal',
]

const viewButtonClasses =
  'inline-flex min-h-7 items-center justify-center rounded px-2 text-[10px] font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-1 focus-visible:ring-offset-surface-card'

export function AttackTypePanel({ countsByLabel, isPending = false }: AttackTypePanelProps) {
  const [view, setView] = useState<AttackTypeView>('bar')

  if (isPending) {
    return <LoadingSkeleton rows={4} />
  }

  const entries: AttackTypeEntry[] = labelOrder
    .filter((label) => countsByLabel[label] !== undefined && countsByLabel[label]! > 0)
    .map((label) => ({
      label,
      count: countsByLabel[label] ?? 0,
    }))

  const total = entries.reduce((sum, { count }) => sum + count, 0)

  if (entries.length === 0) {
    return <EmptyState message="No attack data" subtext="Distribution unavailable" />
  }

  return (
    <div className="min-w-0 flex flex-col gap-3">
      <div className="flex justify-end">
        <div
          role="group"
          aria-label="Attack type chart view"
          className="inline-flex rounded-md border border-border-light bg-surface-inset p-0.5"
        >
          <button
            type="button"
            aria-pressed={view === 'bar'}
            onClick={() => setView('bar')}
            className={cn(
              viewButtonClasses,
              view === 'bar'
                ? 'bg-surface-card text-text-primary shadow-subtle'
                : 'text-text-muted hover:text-text-primary'
            )}
          >
            Bar chart
          </button>
          <button
            type="button"
            aria-pressed={view === 'pie'}
            onClick={() => setView('pie')}
            className={cn(
              viewButtonClasses,
              view === 'pie'
                ? 'bg-surface-card text-text-primary shadow-subtle'
                : 'text-text-muted hover:text-text-primary'
            )}
          >
            Pie chart
          </button>
        </div>
      </div>

      {view === 'bar' ? (
        <div className="flex min-w-0 flex-col gap-2">
          {entries.map(({ label, count }) => {
            const percentage = total > 0 ? (count / total) * 100 : 0

            return (
              <div key={label} className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(48px,96px)_auto] items-center gap-2">
                <span className="min-w-0 truncate text-[11px] text-[var(--color-text-secondary)]">
                  {label}
                </span>
                <div className="h-[3px] min-w-0 rounded-full bg-surface-inset">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${percentage}%`, background: colorMap[label] }}
                  />
                </div>
                <div className="flex shrink-0 items-center justify-end gap-2 tabular-nums">
                  <span className="text-right text-[11px] font-medium text-[var(--color-text-primary)]">
                    {count}
                  </span>
                  <span className="text-right text-[11px] text-[var(--color-text-muted)]">
                    {Math.round(percentage)}%
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <>
          <div
            role="img"
            aria-label="Attack type distribution pie chart"
            className="flex h-[196px] min-h-[160px] w-full min-w-0 max-w-[260px] self-center"
          >
            <ResponsiveContainer width="100%" height="100%">
              <PieChart accessibilityLayer>
                <Pie
                  data={entries}
                  dataKey="count"
                  nameKey="label"
                  innerRadius="52%"
                  outerRadius="78%"
                  paddingAngle={2}
                  stroke="var(--color-bg-panel)"
                  strokeWidth={2}
                >
                  {entries.map(({ label }) => (
                    <Cell key={label} fill={colorMap[label]} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    border: '1px solid var(--color-border-light)',
                    borderRadius: '0.375rem',
                    backgroundColor: 'var(--color-bg-card)',
                    boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5)',
                    backdropFilter: 'blur(12px)',
                  }}
                  itemStyle={{ color: 'var(--color-text-primary)', fontSize: '11px' }}
                  labelStyle={{ color: 'var(--color-text-soft)', fontSize: '10px', marginBottom: '4px' }}
                  formatter={(value, name) => {
                    const numericValue = typeof value === 'number' ? value : Number(value ?? 0)
                    const percentage = total > 0 ? Math.round((numericValue / total) * 100) : 0
                    return [`${numericValue} (${percentage}%)`, String(name ?? '')]
                  }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="flex w-full min-w-0 flex-col gap-2.5">
            {entries.map(({ label, count }) => {
              const percentage = total > 0 ? Math.round((count / total) * 100) : 0

              return (
                <div key={label} className="grid min-w-0 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="h-2.5 w-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: colorMap[label] }}
                  />
                  <span className="min-w-0 truncate text-[11px] text-[var(--color-text-secondary)]">
                    {label}
                  </span>
                  <span className="shrink-0 text-right text-[11px] tabular-nums text-[var(--color-text-muted)]">
                    {count} · {percentage}%
                  </span>
                </div>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
