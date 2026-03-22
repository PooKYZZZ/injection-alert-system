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
  if (
    !countsByLabel ||
    (Object.keys(countsByLabel.baseline ?? {}).length === 0 &&
      Object.keys(countsByLabel.current ?? {}).length === 0)
  ) {
    return (
      <EmptyState
        message="Prediction distribution data was not returned by the backend"
        subtext="Model registry eval metadata may not include a distribution snapshot"
      />
    )
  }

  // Compute totals for percentage conversion
  const baselineTotal = Object.values(countsByLabel.baseline ?? {}).reduce(
    (sum, v) => sum + v,
    0
  )
  const currentTotal = Object.values(countsByLabel.current ?? {}).reduce(
    (sum, v) => sum + v,
    0
  )

  // Map data using ALERT_PREDICTION_VALUES for consistent ordering and display
  const data = ALERT_PREDICTION_VALUES.map((key) => {
    const baselineCount = countsByLabel.baseline[key] ?? 0
    const currentCount = countsByLabel.current[key] ?? 0
    const baselinePct = baselineTotal > 0 ? (baselineCount / baselineTotal) * 100 : 0
    const currentPct = currentTotal > 0 ? (currentCount / currentTotal) * 100 : 0
    return {
      name: key,
      baseline: Math.round(baselinePct * 10) / 10,
      current: Math.round(currentPct * 10) / 10,
      baselineCount,
      currentCount,
      deviation: Math.abs(currentPct - baselinePct),
    }
  })

  return (
    <>
      <div className="h-[140px] w-full mt-2">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 5, right: 5, bottom: 5, left: -25 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--color-text-ghost)"
              vertical={false}
              opacity={0.3}
            />
            <XAxis
              dataKey="name"
              tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
              axisLine={{ stroke: 'var(--color-text-ghost)' }}
            />
            <YAxis
              tick={{ fill: 'var(--color-text-muted)', fontSize: 10 }}
              axisLine={{ stroke: 'var(--color-text-ghost)' }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--color-bg-panel)',
                border: '1px solid var(--color-text-ghost)',
                fontSize: '10px',
                borderRadius: '4px',
              }}
              itemStyle={{ fontSize: '10px' }}
            />
            <Bar
              dataKey="baseline"
              fill="var(--color-text-ghost)"
              radius={[2, 2, 0, 0]}
              name="Baseline %"
            />
            <Bar dataKey="current" radius={[2, 2, 0, 0]} name="Current %">
              {data.map((entry, index) => (
                <Cell
                  key={`cell-${index}`}
                  fill={entry.deviation > 8 ? 'var(--color-accent-amber)' : 'var(--color-accent-purple)'}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <div className="mt-2 text-[11px] text-[var(--color-text-muted)]">
        Deviation {'>'}8pp from baseline may indicate traffic shift.
      </div>
    </>
  )
}




