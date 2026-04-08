'use client'

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'
import { type AlertPrediction } from '@/features/alerts/contract'

interface AttackTypePanelProps {
  countsByLabel: Partial<Record<AlertPrediction, number>>
  isPending?: boolean
}

const colorMap: Record<AlertPrediction, string> = {
  'SQL Injection': 'var(--color-accent-purple)',
  'Code Injection': 'var(--color-severity-high-accent)',
  'Other Attacks': 'var(--color-severity-blocked-accent)',
  'Normal': 'var(--color-text-muted)',
}

const labelOrder: AlertPrediction[] = [
  'SQL Injection',
  'Code Injection',
  'Other Attacks',
  'Normal',
]

export function AttackTypePanel({ countsByLabel, isPending = false }: AttackTypePanelProps) {
  if (isPending) {
    return <LoadingSkeleton rows={4} />
  }

  const entries = labelOrder
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
    <div className="flex min-h-[220px] flex-col items-center gap-3">
      <div className="h-[196px] w-full max-w-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={entries}
              dataKey="count"
              nameKey="label"
              innerRadius={52}
              outerRadius={78}
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
                border: '1px solid #30363d',
                borderRadius: '0.375rem',
                backgroundColor: 'rgba(13,17,23,0.82)',
                boxShadow: '0 20px 25px -5px rgba(0,0,0,0.5)',
                backdropFilter: 'blur(12px)',
              }}
              itemStyle={{ color: '#f0f6fc', fontSize: '11px' }}
              labelStyle={{ color: '#7d8590', fontSize: '10px', marginBottom: '4px' }}
              formatter={(value, name) => {
                const numericValue = typeof value === 'number' ? value : Number(value ?? 0)
                const percentage = total > 0 ? Math.round((numericValue / total) * 100) : 0
                return [`${numericValue} (${percentage}%)`, String(name ?? '')]
              }}
            />
          </PieChart>
        </ResponsiveContainer>
      </div>

      <div className="grid w-full grid-cols-2 gap-x-4 gap-y-2.5">
        {entries.map(({ label, count }) => {
          const percentage = total > 0 ? Math.round((count / total) * 100) : 0

          return (
            <div key={label} className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: colorMap[label] }}
              />
              <span className="truncate text-[11px] text-[var(--color-text-secondary)]">
                {label}
              </span>
              <span className="text-[11px] text-[var(--color-text-muted)] tabular-nums text-right">
                {count} · {percentage}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

