'use client'

import { Suspense } from 'react'
import { useMLHealth } from '@/features/ml-health/queries'

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
  const modelVersion = data.model_version.trim()
  const modelLabel = modelVersion.toLowerCase().startsWith('distilbert')
    ? modelVersion
    : `DistilBERT ${modelVersion}`

  return (
    <div className="px-4 py-3">
      <div className="flex items-center gap-2">
        <div className={`h-2 w-2 rounded-full ${statusDotColor}`} />
        <div className="min-w-0">
          <p className="truncate text-[10px] font-semibold uppercase tracking-wider text-blue-300">
            {modelLabel}
          </p>
          <p className={`text-[11px] font-medium ${statusColor}`}>
            {statusLabel}
          </p>
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
