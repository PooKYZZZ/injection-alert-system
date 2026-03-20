'use client'

import { motion } from 'motion/react'
import { useMLHealth } from '@/features/ml-health/queries'
import { ModelHeader } from '@/components/ml-health/ModelHeader'
import { PerClassF1Chart } from '@/components/ml-health/PerClassF1Chart'
import { ReliabilityDiagram } from '@/components/ml-health/ReliabilityDiagram'
import { ConfidenceDriftChart } from '@/components/ml-health/ConfidenceDriftChart'
import { PredictionDistribution } from '@/components/ml-health/PredictionDistribution'
import { ConfidenceThresholds } from '@/components/ml-health/ConfidenceThresholds'
import { LoadingSkeleton, ErrorState } from '@/components/ui/StateViews'
import type { MLHealthData } from '@/features/ml-health/types'

interface HealthStatProps {
  label: string
  value: string
  sub?: string
  valueColor?: string
  extra?: React.ReactNode
}

function HealthStat({ label, value, sub, valueColor = 'text-[var(--color-text-primary)]', extra }: HealthStatProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-3 flex flex-col gap-1"
    >
      <div className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider font-medium">
        {label}
      </div>
      <div className={cn('text-2xl font-semibold leading-none', valueColor)}>{value}</div>
      {extra ? (
        extra
      ) : sub ? (
        <div className="text-[10px] text-[var(--color-text-muted)] mt-1">{sub}</div>
      ) : null}
    </motion.div>
  )
}

// cn helper for simple class merging
function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ')
}

export default function MLHealthPage() {
  const { data: health, isLoading, isError, refetch } = useMLHealth()

  if (isLoading) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="p-4 px-5 flex flex-col gap-3 overflow-y-auto"
      >
        <LoadingSkeleton rows={10} />
      </motion.div>
    )
  }

  if (isError || !health) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        className="p-4 px-5 flex flex-col gap-3"
      >
        <ErrorState message="Failed to load ML health data" onRetry={refetch} />
      </motion.div>
    )
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className="p-4 px-5 flex flex-col gap-3 overflow-y-auto"
    >
      {/* Model Header */}
      <ModelHeader health={health} />

      {/* Stats Row */}
      <div className="grid grid-cols-4 gap-2">
        {/* Macro F1 — not in BFF yet */}
        <HealthStat label="Macro F1" value="—" sub="Waiting for backend" valueColor="text-violet-400" />
        {/* ECE — not in BFF yet */}
        <HealthStat label="ECE (calibration)" value="—" sub="Waiting for backend" valueColor="text-emerald-400" />
        {/* Avg latency — real data */}
        <HealthStat
          label="Avg inference latency"
          value={`${health.latency_ms}ms`}
          valueColor="text-amber-400"
          extra={
            <div className="flex flex-col gap-1 mt-1">
              <div className="text-[10px] text-[var(--color-text-muted)]">
                {`Target: <50ms · p95: <120ms`}
              </div>
            </div>
          }
        />
        {/* Drift status — real data */}
        <HealthStat
          label="Drift status"
          value={health.drift_status ?? '—'}
          valueColor={
            health.drift_status === 'NORMAL'
              ? 'text-emerald-400'
              : health.drift_status === 'WARNING'
                ? 'text-amber-400'
                : health.drift_status === 'CRITICAL'
                  ? 'text-red-400'
                  : 'text-[var(--color-text-muted)]'
          }
          extra={
            <div className="flex flex-col gap-1 mt-1">
              <div className="flex items-center gap-1.5 text-[10px]">
                <span
                  className={cn(
                    'font-medium',
                    health.drift_status === 'NORMAL' ? 'text-emerald-400' : 'text-[var(--color-text-muted)]'
                  )}
                >
                  Normal
                </span>
                <span className="text-[var(--color-text-muted)]">·</span>
                <span
                  className={cn(
                    'font-medium',
                    health.drift_status === 'WARNING' ? 'text-amber-400' : 'text-[var(--color-text-muted)]'
                  )}
                >
                  Warning
                </span>
                <span className="text-[var(--color-text-muted)]">·</span>
                <span
                  className={cn(
                    'font-medium',
                    health.drift_status === 'CRITICAL' ? 'text-red-400' : 'text-[var(--color-text-muted)]'
                  )}
                >
                  Critical
                </span>
              </div>
              <div className="text-[9px] text-[var(--color-text-muted)]">
                Warning if drift score {'>'} 0.05
              </div>
            </div>
          }
        />
      </div>

      <div className="grid grid-cols-12 gap-3">
        {/* Left Column */}
        <div className="col-span-7 flex flex-col gap-3">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
                Per-class F1 score
              </span>
              <span className="text-[10px] text-[var(--color-text-muted)]">
                Not yet available
              </span>
            </div>
            <PerClassF1Chart perClassF1={null} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 }}
            className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-[11px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
                Prediction Distribution
              </span>
              <span className="text-[10px] text-[var(--color-text-muted)]">
                Current session vs baseline
              </span>
            </div>
            <PredictionDistribution countsByLabel={null} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-[11px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
                Confidence thresholds
              </span>
              <span className="text-[10px] text-[var(--color-text-muted)]">
                Enforcement tiers
              </span>
            </div>
            <ConfidenceThresholds thresholds={health.thresholds} />
          </motion.div>
        </div>

        {/* Right Column */}
        <div className="col-span-5 flex flex-col gap-3">
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.1 }}
            className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
                Reliability diagram
              </span>
              <span className="text-[10px] text-[var(--color-text-muted)]">
                Calibration quality
              </span>
            </div>
            <ReliabilityDiagram bins={null} ece={null} />
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 }}
            className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-4"
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-[11px] font-medium text-[var(--color-text-muted)] uppercase tracking-wider">
                Confidence drift
              </span>
              <span className="text-[10px] text-[var(--color-text-muted)]">Last 6h</span>
            </div>
            <ConfidenceDriftChart driftData={null} />
          </motion.div>
        </div>
      </div>
    </motion.div>
  )
}
