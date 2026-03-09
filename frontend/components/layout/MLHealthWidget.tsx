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
        <div className="h-2 bg-blue-800 rounded w-2/3" />
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

  const driftPct = `${(data.drift_score * 100).toFixed(1)}%`
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
    data.status === 'HEALTHY' ? 'Stable' : data.status === 'DEGRADED' ? 'Degraded' : 'Down'

  return (
    <div className="px-4 py-3">
      {/* Header row */}
      <div className="flex items-center justify-between mb-2">
        <span className="text-[10px] font-bold text-blue-400 uppercase tracking-wider">
          ML Health
        </span>
        <div className="flex items-center gap-1">
          <div className={`w-1.5 h-1.5 rounded-full ${statusDotColor} animate-pulse`} />
          <span className={`text-[10px] font-medium ${statusColor}`}>{statusLabel}</span>
        </div>
      </div>

      {/* Model info */}
      <div className="mb-2 space-y-1">
        <div className="text-xs text-blue-100 font-medium">DistilBERT {data.model_version}</div>
        <div className="text-[9px] text-blue-400 font-mono mb-2">
          Model Hash: 9fa3b2d {/* placeholder */}
        </div>

        <div className="flex justify-between items-center text-[10px]">
          <span className="text-blue-300">Drift:</span>
          <span className="text-orange-300 font-mono">{driftPct}</span>
        </div>
        <div className="flex justify-between items-center text-[10px]">
          <span className="text-blue-300">ECE (10-bin):</span>
          <span className="text-blue-200 font-mono">0.021 {/* placeholder */}</span>
        </div>
        <div className="flex justify-between items-center text-[10px]">
          <span className="text-blue-300">Brier Score:</span>
          <span className="text-blue-200 font-mono">0.084 {/* placeholder */}</span>
        </div>
        <div className="flex justify-between items-center text-[10px]">
          <span className="text-blue-300">OOD Retention:</span>
          <span className="text-green-300 font-mono">94% {/* placeholder */}</span>
        </div>
        <div className="flex justify-between items-center text-[10px] mt-1 pt-1 border-t border-[#2d4a77]">
          <span className="text-blue-300">Failover Mode:</span>
          <span className="text-yellow-400 font-medium">CRS-only {/* placeholder */}</span>
        </div>
      </div>

      {/* Confidence thresholds */}
      <div className="bg-[#11243d] rounded p-2 mb-2 border border-[#2d4a77]">
        <div className="text-[9px] text-blue-300 mb-1 font-bold">Confidence Thresholds</div>
        <div className="flex flex-col gap-0.5 text-[9px] font-mono">
          <div className="flex justify-between">
            <span className="text-status-low">LOW</span>
            <span className="text-blue-200">
              &lt; {Math.round(data.thresholds.low * 100)}%
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-status-medium">MED</span>
            <span className="text-blue-200">
              {Math.round(data.thresholds.low * 100)}-{Math.round(data.thresholds.medium * 100)}%
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-status-high">HIGH</span>
            <span className="text-blue-200">
              &gt; {Math.round(data.thresholds.medium * 100)}%
            </span>
          </div>
        </div>
      </div>

      {/* Sparkline */}
      <div className="h-6 w-full bg-[#1e3a5f] rounded-sm relative overflow-hidden mb-2 border border-[#2d4a77]">
        <svg
          className="absolute bottom-0 left-0 w-full h-full"
          preserveAspectRatio="none"
          viewBox="0 0 100 20"
        >
          <path
            d="M0,15 L10,12 L20,16 L30,10 L40,14 L50,8 L60,12 L70,5 L80,10 L90,8 L100,12"
            fill="none"
            stroke="#60a5fa"
            strokeWidth="1.5"
          />
          <path
            d="M0,15 L10,12 L20,16 L30,10 L40,14 L50,8 L60,12 L70,5 L80,10 L90,8 L100,12 V20 H0 Z"
            fill="rgba(96, 165, 250, 0.2)"
            stroke="none"
          />
        </svg>
      </div>

      {/* Pending / FP Rev counts */}
      <div className="grid grid-cols-2 gap-2 text-[10px] border-t border-[#2d4a77] pt-2 mt-1">
        <div className="text-center">
          <span className="block text-blue-100 font-bold">32 {/* placeholder */}</span>
          <span className="block text-blue-400">Pending</span>
        </div>
        <div className="text-center border-l border-[#2d4a77]">
          <span className="block text-blue-100 font-bold">8 {/* placeholder */}</span>
          <span className="block text-blue-400">FP Rev.</span>
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
          <div className="h-2 bg-blue-800 rounded w-2/3" />
        </div>
      }
    >
      <MLHealthContent />
    </Suspense>
  )
}
