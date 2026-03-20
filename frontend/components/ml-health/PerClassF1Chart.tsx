'use client'

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
} from 'recharts'
import { EmptyState } from '@/components/ui/StateViews'
import { ALERT_PREDICTION_VALUES } from '@/features/alerts/contract'

interface PerClassF1ChartProps {
  perClassF1?: Record<string, number> | null
}

// Color map keyed by prediction label, matching AI Studio treatment
const COLOR_MAP: Record<string, { bar: string; text: string }> = {
  'SQL Injection':  { bar: '#7c3aed', text: 'text-violet-400' },
  'Other Attacks':  { bar: '#ef4444', text: 'text-red-400' },
  Normal:           { bar: '#4ade80', text: 'text-emerald-400' },
  'Code Injection': { bar: '#f59e0b', text: 'text-amber-400' },
}

const FALLBACK_COLOR = '#475569'

export function PerClassF1Chart({ perClassF1 }: PerClassF1ChartProps) {
  if (!perClassF1) {
    return (
      <EmptyState
        message="Per-class F1 not yet available from backend"
        subtext="Connect ML eval metadata endpoint to populate this chart"
      />
    )
  }

  // Order by ALERT_PREDICTION_VALUES for consistency with contract
  const data = ALERT_PREDICTION_VALUES.map((label) => ({
    label,
    f1: perClassF1[label] ?? 0,
    color: COLOR_MAP[label]?.bar ?? FALLBACK_COLOR,
  }))

  return (
    <div className="h-[160px] w-full">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ top: 4, right: 40, bottom: 4, left: 0 }}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="#30363d"
            horizontal={false}
            opacity={0.4}
          />
          <XAxis
            type="number"
            domain={[0, 1]}
            tick={{ fill: '#484f58', fontSize: 9 }}
            axisLine={{ stroke: '#30363d' }}
            tickFormatter={(v: number) => v.toFixed(1)}
          />
          <YAxis
            type="category"
            dataKey="label"
            width={90}
            tick={{ fill: '#94a3b8', fontSize: 10 }}
            axisLine={{ stroke: '#30363d' }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: 'var(--color-bg-panel)',
              border: '1px solid #30363d',
              fontSize: '10px',
              borderRadius: '4px',
            }}
            formatter={(value) => [typeof value === 'number' ? value.toFixed(3) : String(value), 'F1']}
            labelStyle={{ color: '#94a3b8' }}
          />
          <Bar dataKey="f1" radius={[0, 2, 2, 0]}>
            {data.map((entry) => (
              <Cell key={entry.label} fill={entry.color} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
