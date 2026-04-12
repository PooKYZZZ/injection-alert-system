'use client'

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { cn } from '@/lib/utils'
import { EmptyState, LoadingSkeleton } from '@/components/ui/StateViews'
import type { AlertAction } from '@/features/alerts/contract'

export interface SourceIPSummary {
  ip: string
  count: number
  action: AlertAction | null
}

interface TopSourceIPsProps {
  ips: SourceIPSummary[]
  isPending?: boolean
}

const statusStyles: Record<AlertAction, string> = {
  BLOCKED: 'bg-[var(--color-severity-high-bg)] text-severity-high-text',
  THROTTLED: 'bg-[var(--color-severity-blocked-bg)] text-severity-blocked-text',
  ALLOWED: 'bg-[var(--color-severity-safe-bg)] text-severity-safe-text',
}

const actionLabels: Record<AlertAction, string> = {
  BLOCKED: 'Blocked',
  THROTTLED: 'Throttled',
  ALLOWED: 'Allowed',
}

const ipSliceColors = [
  'var(--color-severity-high-accent)',
  'var(--color-accent-blue)',
  'var(--color-accent-purple)',
  'var(--color-severity-blocked-accent)',
  'var(--color-severity-safe-accent)',
  'var(--color-accent-cyan)',
  'var(--color-accent-yellow)',
  'var(--color-severity-benign-accent)',
]

export function TopSourceIPs({ ips, isPending = false }: TopSourceIPsProps) {
  if (isPending) {
    return <LoadingSkeleton rows={4} />
  }

  if (ips.length === 0) {
    return <EmptyState message="No source IPs in this window" subtext="IPs appear when blocked or throttled traffic is detected" />
  }

  const total = ips.reduce((sum, item) => sum + item.count, 0)

  return (
    <div className="flex min-h-[220px] flex-col items-center gap-3">
      <div className="h-[196px] w-full max-w-[260px]">
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={ips}
              dataKey="count"
              nameKey="ip"
              innerRadius={52}
              outerRadius={78}
              paddingAngle={2}
              stroke="var(--color-bg-panel)"
              strokeWidth={2}
            >
              {ips.map((item, index) => (
                <Cell
                  key={item.ip}
                  fill={ipSliceColors[index % ipSliceColors.length]}
                />
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

      <div className="grid w-full gap-2.5">
        {ips.map((item, index) => {
          const percentage = total > 0 ? Math.round((item.count / total) * 100) : 0

          return (
            <div key={item.ip} className="grid grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-2 text-[11px]">
              <span
                className="h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: ipSliceColors[index % ipSliceColors.length] }}
              />
              <div className="flex min-w-0 items-center gap-2">
                <span className="truncate font-mono text-[var(--color-text-secondary)]">{item.ip}</span>
                {item.action ? (
                  <span
                    className={cn(
                      'rounded-full px-1.5 py-0.5 text-[10px] font-medium',
                      statusStyles[item.action]
                    )}
                  >
                    {actionLabels[item.action]}
                  </span>
                ) : null}
              </div>
              <span className="tabular-nums text-[var(--color-text-muted)] text-right">
                {item.count} · {percentage}%
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

