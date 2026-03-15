'use client'

import { Suspense } from 'react'
import { useMLHealth } from '@/features/ml-health/queries'

function formatPercentThreshold(value: number | null): string | null {
  if (value === null) {
    return null
  }

  return `${Math.round(value * 100)}%`
}

function formatLessThanThreshold(value: string | null): string {
  return value === null ? 'N/A' : `< ${value}`
}

function formatGreaterThanThreshold(value: string | null): string {
  return value === null ? 'N/A' : `> ${value}`
}

function MLHealthContent() {
  const { data, isPending, isError } = useMLHealth()

  if (isPending) {
    return (
      <div className="px-4 py-3 animate-pulse space-y-2">
        <div className="h-2 bg-blue-800 rounded w-3/4" />
        <div className="h-2 bg-blue-800 rounded w-1/2" />
      </div>
    )
  }

  if (isError || !data) {
    return (
      <div className="px-4 py-3">
        <p className="text-[11px] text-blue-400">Model unavailable</p>
      </div>
    )
  }

  const driftPct =
    data.drift_score === null ? 'N/A' : `${(data.drift_score * 100).toFixed(1)}%`
  const inferenceTime =
    `${data.latency_ms.toFixed(1)}ms`
  const lowThresholdLabel = formatPercentThreshold(data.thresholds.low)
  const mediumThresholdValue = formatPercentThreshold(data.thresholds.medium)
  const highThresholdLabel = formatPercentThreshold(data.thresholds.high)
  const mediumThresholdLabel =
    mediumThresholdValue ?? (
      lowThresholdLabel !== null && highThresholdLabel !== null
        ? `${lowThresholdLabel} - ${highThresholdLabel}`
        : null
    )
  const highThresholdBoundary = mediumThresholdValue ?? highThresholdLabel

  const statusColor =
    data.status === 'HEALTHY'
      ? 'text-green-400'
      : data.status === 'DEGRADED'
      ? 'text-yellow-400'
      : 'text-red-400'

  const statusDotColor =
    data.status === 'HEALTHY'
      ? 'bg-green-500'
      : data.status === 'DEGRADED'
      ? 'bg-yellow-500'
      : 'bg-red-500'

  const statusLabel =
    data.status === 'HEALTHY'
      ? 'Stable'
      : data.status === 'DEGRADED'
      ? 'Degraded'
      : 'Down'

  return (
    <div className="px-4 py-3">

      {/* Header */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider">
          ML Health
        </span>

        <div className="flex items-center gap-1">
          <div className={`w-1.5 h-1.5 rounded-full ${statusDotColor}`} />
          <span className={`text-[10px] font-medium ${statusColor}`}>
            {statusLabel}
          </span>
        </div>
      </div>

      {/* Model Info */}
      <div className="space-y-1 text-[10px]">

        <div className="flex justify-between">
          <span className="text-blue-300">Model:</span>
          <span className="text-blue-100 font-medium">
            DistilBERT {data.model_version}
          </span>
        </div>

        <div className="flex justify-between">
          <span className="text-blue-300">Drift:</span>
          <span className="text-orange-300 font-mono">{driftPct}</span>
        </div>

        <div className="flex justify-between">
          <span className="text-blue-300">Inference Time:</span>
          <span className="text-blue-200 font-mono">{inferenceTime}</span>
        </div>

        <div className="flex justify-between border-t border-[#2d4a77] pt-1 mt-1">
          <span className="text-blue-300">Last Retrain:</span>
          <span className="text-green-300 font-medium">Today 02:00</span>
        </div>

      </div>

      {/* Confidence Thresholds */}
      <div className="bg-[#11243d] rounded p-2 mt-3 border border-[#2d4a77]">
        <div className="text-[9px] text-blue-300 mb-1 font-bold">
          Confidence Thresholds
        </div>

        <div className="flex flex-col gap-0.5 text-[9px] font-mono">

          <div className="flex justify-between">
            <span className="text-status-low">LOW</span>
            <span className="text-blue-200">
              {formatLessThanThreshold(lowThresholdLabel)}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-status-medium">MED</span>
            <span className="text-blue-200">
              {mediumThresholdLabel ?? 'N/A'}
            </span>
          </div>

          <div className="flex justify-between">
            <span className="text-status-high">HIGH</span>
            <span className="text-blue-200">
              {formatGreaterThanThreshold(highThresholdBoundary)}
            </span>
          </div>

        </div>
      </div>

    </div>
  )
}

export function MLHealthWidget() {
  return (
    <Suspense
      fallback={
        <div className="px-4 py-3 animate-pulse space-y-2">
          <div className="h-2 bg-blue-800 rounded w-3/4" />
          <div className="h-2 bg-blue-800 rounded w-1/2" />
        </div>
      }
    >
      <MLHealthContent />
    </Suspense>
  )
}
