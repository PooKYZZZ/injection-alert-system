'use client'

import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'

interface MLConfidenceBandsProps {
  high: number
  critical: number
  medium: number
  low: number
  informational: number
  isPending?: boolean
  unavailable?: boolean
}

export function MLConfidenceBands({
  high,
  critical,
  medium,
  low,
  informational,
  isPending = false,
  unavailable = false,
}: MLConfidenceBandsProps) {
  if (isPending) {
    return <LoadingSkeleton rows={5} />
  }

  if (unavailable) {
    return (
      <EmptyState
        message="Confidence bands unavailable"
        subtext="Current stats API does not provide this data"
      />
    )
  }

  const total = critical + high + medium + low + informational

  return (
    <div className="flex flex-col gap-2">
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(48px,96px)_auto] items-center gap-2">
        <span className="min-w-0 truncate text-[11px] text-[var(--color-accent-analytic)]">Critical confidence tier</span>
        <div className="h-[3px] rounded-full bg-surface-border">
          <div
            className="h-full w-full origin-left rounded-full"
            style={{ transform: `scaleX(${total > 0 ? critical / total : 0})`, background: 'var(--color-severity-high-accent)' }}
          />
        </div>
        <div className="flex shrink-0 items-center justify-end gap-2 tabular-nums">
          <span className="text-[11px] font-medium text-[var(--color-text-primary)] text-right">{critical}</span>
          <span className="text-[11px] text-[var(--color-text-muted)] text-right">
            {total > 0 ? Math.round((critical / total) * 100) : 0}%
          </span>
        </div>
      </div>
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(48px,96px)_auto] items-center gap-2">
        <span className="min-w-0 truncate text-[11px] text-[var(--color-accent-analytic)]">High confidence tier</span>
        <div className="h-[3px] rounded-full bg-surface-border">
          <div
            className="h-full w-full origin-left rounded-full"
            style={{ transform: `scaleX(${total > 0 ? high / total : 0})`, background: 'var(--color-severity-high-accent)' }}
          />
        </div>
        <div className="flex shrink-0 items-center justify-end gap-2 tabular-nums">
          <span className="text-[11px] font-medium text-[var(--color-text-primary)] text-right">{high}</span>
          <span className="text-[11px] text-[var(--color-text-muted)] text-right">
            {total > 0 ? Math.round((high / total) * 100) : 0}%
          </span>
        </div>
      </div>
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(48px,96px)_auto] items-center gap-2">
        <span className="min-w-0 truncate text-[11px] text-[var(--color-accent-analytic)]">Medium confidence tier</span>
        <div className="h-[3px] rounded-full bg-surface-border">
          <div
            className="h-full w-full origin-left rounded-full"
            style={{ transform: `scaleX(${total > 0 ? medium / total : 0})`, background: 'var(--color-severity-blocked-accent)' }}
          />
        </div>
        <div className="flex shrink-0 items-center justify-end gap-2 tabular-nums">
          <span className="text-[11px] font-medium text-[var(--color-text-primary)] text-right">{medium}</span>
          <span className="text-[11px] text-[var(--color-text-muted)] text-right">
            {total > 0 ? Math.round((medium / total) * 100) : 0}%
          </span>
        </div>
      </div>
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(48px,96px)_auto] items-center gap-2">
        <span className="min-w-0 truncate text-[11px] text-[var(--color-accent-analytic)]">Low confidence tier</span>
        <div className="h-[3px] rounded-full bg-surface-border">
          <div
            className="h-full w-full origin-left rounded-full"
            style={{ transform: `scaleX(${total > 0 ? low / total : 0})`, background: 'var(--color-severity-safe-accent)' }}
          />
        </div>
        <div className="flex shrink-0 items-center justify-end gap-2 tabular-nums">
          <span className="text-[11px] font-medium text-[var(--color-text-primary)] text-right">{low}</span>
          <span className="text-[11px] text-[var(--color-text-muted)] text-right">
            {total > 0 ? Math.round((low / total) * 100) : 0}%
          </span>
        </div>
      </div>
      <div className="grid min-w-0 grid-cols-[minmax(0,1fr)_minmax(48px,96px)_auto] items-center gap-2">
        <span className="min-w-0 truncate text-[11px] text-[var(--color-accent-analytic)]">Informational confidence tier</span>
        <div className="h-[3px] rounded-full bg-surface-border">
          <div
            className="h-full w-full origin-left rounded-full"
            style={{ transform: `scaleX(${total > 0 ? informational / total : 0})`, background: 'var(--color-text-muted)' }}
          />
        </div>
        <div className="flex shrink-0 items-center justify-end gap-2 tabular-nums">
          <span className="text-[11px] font-medium text-[var(--color-text-primary)] text-right">{informational}</span>
          <span className="text-[11px] text-[var(--color-text-muted)] text-right">
            {total > 0 ? Math.round((informational / total) * 100) : 0}%
          </span>
        </div>
      </div>
    </div>
  )
}
