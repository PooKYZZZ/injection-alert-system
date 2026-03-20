'use client'

import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts'
import { EmptyState } from '@/components/ui/StateViews'

interface ReliabilityDiagramProps {
  bins?: Array<{ bin_center: number; accuracy: number }> | null
  ece?: number | null
}

export function ReliabilityDiagram({ bins, ece }: ReliabilityDiagramProps) {
  if (!bins || bins.length === 0) {
    return (
      <EmptyState
        message="Calibration data not yet available from backend"
        subtext="Connect ML eval metadata endpoint to populate this diagram"
      />
    )
  }

  return (
    <>
      <div className="h-[170px] w-full">
        <ResponsiveContainer width="100%" height="100%">
          <ScatterChart margin={{ top: 5, right: 5, bottom: 5, left: -25 }}>
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#30363d"
              vertical={false}
            />
            <XAxis
              type="number"
              dataKey="bin_center"
              name="Mean confidence"
              domain={[0, 1]}
              tick={{ fill: '#484f58', fontSize: 9 }}
              axisLine={{ stroke: '#30363d' }}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <YAxis
              type="number"
              dataKey="accuracy"
              name="Actual accuracy"
              domain={[0, 1]}
              tick={{ fill: '#484f58', fontSize: 9 }}
              axisLine={{ stroke: '#30363d' }}
              tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            />
            <Tooltip
              cursor={{ strokeDasharray: '3 3' }}
              contentStyle={{
                backgroundColor: 'var(--color-bg-panel)',
                border: '1px solid #30363d',
                fontSize: '10px',
                borderRadius: '4px',
              }}
              itemStyle={{ fontSize: '10px' }}
              formatter={(value, name) => {
                const v = typeof value === 'number' ? value : parseFloat(String(value))
                return [`${(v * 100).toFixed(1)}%`, name]
              }}
            />
            <Scatter
              name="Model"
              data={bins}
              fill="#7c3aed"
              line={{ stroke: '#7c3aed', strokeWidth: 1.5 }}
            />
            <ReferenceLine
              segment={[{ x: 0, y: 0 }, { x: 1, y: 1 }]}
              stroke="#30363d"
              strokeDasharray="4 4"
            />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <div className="text-[10px] text-[var(--color-text-muted)] text-center mt-2">
        Mean confidence vs actual accuracy per bin
        {ece !== null && ece !== undefined ? ` · ECE ${ece.toFixed(3)}` : ''}
      </div>
    </>
  )
}
