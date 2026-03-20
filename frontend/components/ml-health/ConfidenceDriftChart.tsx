'use client'

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { EmptyState } from '@/components/ui/StateViews'

interface ConfidenceDriftChartProps {
  driftData?: Array<{ time: string; conf: number }> | null
}

export function ConfidenceDriftChart({ driftData }: ConfidenceDriftChartProps) {
  if (!driftData || driftData.length === 0) {
    return (
      <EmptyState
        message="Drift history not yet available from backend"
        subtext="Connect drift monitoring endpoint to populate this chart"
      />
    )
  }

  return (
    <>
      <div className="h-[100px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={driftData}
            margin={{ top: 5, right: 5, bottom: 0, left: -25 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#30363d"
              vertical={false}
              opacity={0.3}
            />
            <XAxis
              dataKey="time"
              tick={{ fill: '#484f58', fontSize: 9 }}
              axisLine={{ stroke: '#30363d' }}
            />
            <YAxis
              domain={[80, 100]}
              tick={{ fill: '#484f58', fontSize: 9 }}
              axisLine={{ stroke: '#30363d' }}
              tickFormatter={(v) => `${v}%`}
            />
            <Tooltip
              contentStyle={{
                backgroundColor: 'var(--color-bg-panel)',
                border: '1px solid #30363d',
                fontSize: '10px',
                borderRadius: '4px',
              }}
              formatter={(value) => [`${value}%`, 'Confidence']}
            />
            <ReferenceLine
              y={85}
              stroke="#f59e0b"
              strokeDasharray="3 3"
              label={{
                value: 'Warning',
                position: 'right',
                fill: '#f59e0b',
                fontSize: 9,
              }}
            />
            <Line
              type="monotone"
              dataKey="conf"
              stroke="#7c3aed"
              strokeWidth={1.5}
              dot={{ r: 3, fill: '#7c3aed' }}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}
