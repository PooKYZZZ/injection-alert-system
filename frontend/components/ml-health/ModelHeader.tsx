'use client'

import { motion } from 'motion/react'
import { cn } from '@/lib/utils'
import type { MLHealthData } from '@/features/ml-health/types'

interface ModelHeaderProps {
  health: MLHealthData
}

const STATUS_BADGE: Record<
  MLHealthData['status'],
  { bg: string; text: string; border: string }
> = {
  HEALTHY: {
    bg: 'bg-[#0f2d1a]',
    text: 'text-emerald-400',
    border: 'border-emerald-900',
  },
  DEGRADED: {
    bg: 'bg-[#2d2310]',
    text: 'text-amber-400',
    border: 'border-amber-900',
  },
  DOWN: {
    bg: 'bg-[#2d1b1b]',
    text: 'text-red-400',
    border: 'border-red-900',
  },
}

interface MetaItemProps {
  label: string
  value: string
  valueColor?: string
}

function MetaItem({ label, value, valueColor = 'text-[var(--color-text-primary)]' }: MetaItemProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-[10px] text-[var(--color-text-muted)] uppercase tracking-tight">{label}</span>
      <span className={cn('text-[13px] font-medium', valueColor)}>{value}</span>
    </div>
  )
}

export function ModelHeader({ health }: ModelHeaderProps) {
  const badge = STATUS_BADGE[health.status]
  const statusLabel =
    health.status === 'HEALTHY'
      ? 'Healthy'
      : health.status === 'DEGRADED'
        ? 'Degraded'
        : 'Down'

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-4 flex flex-col gap-3"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-[var(--color-bg-elevated)] border border-[var(--color-accent-blue-bg)] rounded-lg flex items-center justify-center text-xs font-bold text-[var(--color-accent-blue)]">
            ML
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-sm font-medium text-[var(--color-text-primary)]">
                {health.model_version}
              </span>
              <span
                className={cn(
                  'text-[11px] px-2 py-0.5 rounded-full border font-medium',
                  badge.bg,
                  badge.text,
                  badge.border,
                )}
              >
                {statusLabel}
              </span>
            </div>
            <div className="text-[10px] text-[var(--color-text-muted)] font-mono mt-0.5">
              {health.model_version}
            </div>
          </div>
        </div>

        <div className="flex gap-5 text-[11px] text-[var(--color-text-muted)]">
          <MetaItem label="Traffic processed" value={health.traffic_processed.toLocaleString()} />
          <MetaItem label="Avg latency" value={`${health.latency_ms}ms`} valueColor="text-amber-400" />
          <MetaItem
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
          />
          <MetaItem label="Calibration" value="Temp-scaled" valueColor="text-emerald-400" />
        </div>
      </div>

      <div className="pt-3 border-t border-[var(--color-text-ghost)]/30 flex items-center gap-3 text-[10px] text-[var(--color-text-muted)]">
        <span>Status: {statusLabel}</span>
        <span>·</span>
        <span>Version: {health.model_version}</span>
        <span>·</span>
        <span>
          Drift score:{' '}
          {health.drift_score !== null ? health.drift_score.toFixed(4) : '—'}
        </span>
      </div>
    </motion.div>
  )
}
