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

interface PredictionDistributionProps {
  countsByLabel?: {
    baseline: Record<string, number>
    current: Record<string, number>
  } | null
}

export function PredictionDistribution({
  countsByLabel,
}: PredictionDistributionProps) {
  if (!countsByLabel) {
    return (
      <EmptyState
        message="Distribution data not yet available from backend"
        subtext="Connect ML eval metadata endpoint to populate this chart"
      />
    )
  }

  // Map data using ALERT_PREDICTION_VALUES for consistent ordering and display
  const data = ALERT_PREDICTION_VALUES.map((key) => ({
    name: key,
    baseline: countsByLabel.baseline[key] ?? 0,
    current: countsByLabel.current[key] ?? 0,
    deviation: Math.abs(
      (countsByLabel.current[key] ?? 0) - (countsByLabel.baseline[key] ?? 0)
    ),
  }))

  return (
    <>
      <div className="h-[140px] w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: -25 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#30363d"
              vertical={false}
              opacity={0.3}
            />
            <XAxis
              dataKey="name"
              tick={{ fill: '#484f58', fontSize: 8 }}
              axisLine={{ stroke: '#30363d' }}
            />
            <YAxis
              tick={{ fill: '#484f58', fontSize: 9 }}
              axisLine={{ stroke: '#30363d' }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: '#111827',
                border: '1px solid #30363d',
                fontSize: '10px',
                borderRadius: '4px',
              }}
              itemStyle={{ fontSize: '10px' }}
            />
            <Bar
              dataKey="baseline"
              fill="#30363d"
              radius={[2, 2, 0, 0]}
              name="Baseline %"
            />
            <Bar dataKey="current" radius={[2, 2, 0, 0]} name="Current %">
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.deviation > 8 ? '#f59e0b' : '#7c3aed'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 text-[9px] text-[var(--color-text-muted)]">
        Deviation {'>'}8pp from baseline may indicate traffic shift.
      </div>
    </>
  )
}
