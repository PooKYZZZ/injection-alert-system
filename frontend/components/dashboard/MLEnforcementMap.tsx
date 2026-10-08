'use client'

import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'
import { InfoDisclosure } from '@/components/ui/InfoDisclosure'
import type { ConfidenceBandCounts } from '@/features/alerts/confidenceBands'

const COUNT_HELP =
  'Counts stored actionable-detection records in this model-confidence tier and selected window. A count is not a count of guaranteed unique HTTP requests.'

const BLOCK_HELP =
  'For HIGH and CRITICAL detections, policy intends to block only when strong CRS evidence matches the predicted attack family and runtime checks pass. This label describes policy intent; it does not confirm an HTTP block.'

const THROTTLE_HELP =
  'Policy intends to throttle MEDIUM detections when matching strong CRS evidence or the repeated-suspicious-activity threshold is met and runtime checks pass. This label describes policy intent; it does not confirm throttling.'

const MONITOR_HELP =
  'For LOW and INFORMATIONAL detections, policy intent is monitoring without an ML block or throttle. This label does not prove the request was allowed by every system layer.'

interface MLEnforcementMapProps {
  nonNormalCounts: ConfidenceBandCounts
  isPending?: boolean
  unavailable?: boolean
}

export function MLEnforcementMap({
  nonNormalCounts,
  isPending = false,
  unavailable = false,
}: MLEnforcementMapProps) {
  const { critical, high, medium, low, informational } = nonNormalCounts
  if (isPending) {
    return <LoadingSkeleton rows={4} />
  }

  if (unavailable) {
    return (
      <EmptyState
        message="Response policy unavailable"
        subtext="Current stats API does not provide this data"
      />
    )
  }

  const total = critical + high + medium + low + informational

  return (
    <div className="min-w-0 flex flex-col gap-1.5">
      <div className="break-words text-[11px] font-medium text-[var(--color-text-primary)]">
        Configured response policy
      </div>
      <div className="break-words text-[11px] leading-tight text-[var(--color-text-muted)]">
        Normal predictions remain ALLOWED; INFORMATIONAL and LOW actionable detections are ALLOWED with MONITOR ONLY intent; out-of-scope labels do not enter this policy.
      </div>

      <div className="flex min-w-0 items-center justify-between gap-2 text-[10px]">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-high-accent" />
          <span className="truncate text-[var(--color-accent-analytic)]">CRITICAL actionable detections</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{critical}</span>
          <InfoDisclosure label="CRITICAL actionable detections">{COUNT_HELP}</InfoDisclosure>
          <span className="flex items-center gap-1">
            <span className="rounded border border-severity-high-border bg-severity-high-bg px-1 py-0.5 text-[10px] font-bold text-severity-high-text">
              BLOCK WITH EVIDENCE
            </span>
            <InfoDisclosure label="Block with evidence">
              {BLOCK_HELP}
            </InfoDisclosure>
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-border">
        <div className="h-full bg-severity-high-accent" style={{ width: `${total > 0 ? (critical / total) * 100 : 0}%` }} />
      </div>

      <div className="flex min-w-0 items-center justify-between gap-2 text-[10px]">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-high-accent" />
          <span className="truncate text-[var(--color-accent-analytic)]">HIGH actionable detections</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{high}</span>
          <InfoDisclosure label="HIGH actionable detections">{COUNT_HELP}</InfoDisclosure>
          <span className="flex items-center gap-1">
            <span className="rounded border border-severity-high-border bg-severity-high-bg px-1 py-0.5 text-[10px] font-bold text-severity-high-text">
              BLOCK WITH EVIDENCE
            </span>
            <InfoDisclosure label="Block with evidence">
              {BLOCK_HELP}
            </InfoDisclosure>
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-border">
        <div className="h-full bg-severity-high-accent" style={{ width: `${total > 0 ? (high / total) * 100 : 0}%` }} />
      </div>

      <div className="mt-1 flex min-w-0 items-center justify-between gap-2 text-[10px]">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-blocked-accent" />
          <span className="truncate text-[var(--color-accent-analytic)]">MEDIUM actionable detections</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{medium}</span>
          <InfoDisclosure label="MEDIUM actionable detections">{COUNT_HELP}</InfoDisclosure>
          <span className="flex items-center gap-1">
            <span className="rounded border border-severity-blocked-border bg-severity-blocked-bg px-1 py-0.5 text-[10px] font-bold text-severity-blocked-text">
              THROTTLE WITH EVIDENCE
            </span>
            <InfoDisclosure label="Throttle with evidence">
              {THROTTLE_HELP}
            </InfoDisclosure>
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-border">
        <div className="h-full bg-severity-blocked-accent" style={{ width: `${total > 0 ? (medium / total) * 100 : 0}%` }} />
      </div>

      <div className="mt-1 flex min-w-0 items-center justify-between gap-2 text-[10px]">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-severity-safe-accent" />
          <span className="truncate text-[var(--color-accent-analytic)]">LOW actionable detections</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{low}</span>
          <InfoDisclosure label="LOW actionable detections">{COUNT_HELP}</InfoDisclosure>
          <span className="flex items-center gap-1">
            <span className="rounded border border-severity-safe-border bg-severity-safe-bg px-1 py-0.5 text-[10px] font-bold text-severity-safe-text">
              MONITOR ONLY
            </span>
            <InfoDisclosure label="Monitor only">
              {MONITOR_HELP}
            </InfoDisclosure>
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-border">
        <div className="h-full bg-severity-safe-accent" style={{ width: `${total > 0 ? (low / total) * 100 : 0}%` }} />
      </div>

      <div className="mt-1 flex min-w-0 items-center justify-between gap-2 text-[10px]">
        <div className="flex min-w-0 flex-1 items-center gap-1.5">
          <div className="h-1.5 w-1.5 rounded-full bg-[var(--color-text-muted)]" />
          <span className="truncate text-[var(--color-accent-analytic)]">INFORMATIONAL actionable detections</span>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <span className="font-mono text-[var(--color-text-primary)]">{informational}</span>
          <InfoDisclosure label="INFORMATIONAL actionable detections">{COUNT_HELP}</InfoDisclosure>
          <span className="flex items-center gap-1">
            <span className="rounded border border-surface-border bg-surface-inset px-1 py-0.5 text-[10px] font-bold text-text-secondary">
              MONITOR ONLY
            </span>
            <InfoDisclosure label="Monitor only">
              {MONITOR_HELP}
            </InfoDisclosure>
          </span>
        </div>
      </div>
      <div className="h-1 overflow-hidden rounded-full bg-surface-border">
        <div className="h-full bg-[var(--color-text-muted)]" style={{ width: `${total > 0 ? (informational / total) * 100 : 0}%` }} />
      </div>

      <div className="mt-1 break-words text-[11px] leading-tight text-[var(--color-text-muted)] italic">
        Configured policy depends on prediction class and confidence tier; it does not prove a WAF action or HTTP outcome.
      </div>
    </div>
  )
}
