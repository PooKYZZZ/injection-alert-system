'use client'

import { Suspense } from 'react'
import { useMLHealth } from '@/features/ml-health/queries'

function MLHealthContent() {
  const { data, isPending, isError } = useMLHealth()

  if (isPending) {
    return (
      <div className="flex items-center gap-3 px-4 py-3" aria-hidden="true">
        <div className="h-[7px] w-[7px] rounded-full bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
        <div className="h-3 w-20 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
        <div className="h-2.5 w-10 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
      </div>
    )
  }

  const statusLabel =
    isError || !data
      ? 'Unavailable'
      : data.status === 'HEALTHY'
        ? 'Healthy'
        : data.status === 'DEGRADED'
          ? 'Degraded'
          : 'Down'

  const statusDotClass =
    isError || !data
      ? 'bg-bg-elevated'
      : data.status === 'HEALTHY'
        ? 'bg-severity-safe-accent'
        : data.status === 'DEGRADED'
          ? 'bg-accent-yellow'
          : 'bg-severity-high-accent'

  // Extract short model name (e.g., "distilbert_v3" from "distilbert_v3_907k_cleaned_...")
  const getShortModelName = (version: string | undefined): string => {
    if (!version || version === 'mock-model-service') return 'Model'
    const parts = version.split('_')
    // Return first two parts (e.g., "distilbert_v3")
    return parts.length >= 2 ? `${parts[0]}_${parts[1]}` : version
  }

  const modelLabel = isError || !data ? 'Model' : getShortModelName(data.model_version)

  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <span className={`h-[7px] w-[7px] rounded-full ${statusDotClass}`} aria-hidden="true" />
      <span className="text-[11px] font-medium text-text-secondary">{modelLabel}</span>
      <span className="text-[10px] text-text-muted">{statusLabel}</span>
    </div>
  )
}

export function MLHealthWidget() {
  return (
    <Suspense
      fallback={
        <div className="flex items-center gap-3 px-4 py-3" aria-hidden="true">
          <div className="h-[7px] w-[7px] rounded-full bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          <div className="h-3 w-20 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          <div className="h-2.5 w-10 rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
        </div>
      }
    >
      <MLHealthContent />
    </Suspense>
  )
}
