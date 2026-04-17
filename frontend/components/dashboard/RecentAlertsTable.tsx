'use client'

import Link from 'next/link'
import { LoadingSkeleton } from '@/components/ui/StateViews'
import { ActionLabel } from '@/components/ui/ActionLabel'
import { ConfidenceBar } from '@/components/ui/ConfidenceBar'
import { TriageBadge } from '@/components/ui/TriageBadge'
import type { Alert } from '@/features/alerts/types'

interface RecentAlertsTableProps {
  alerts: Alert[]
  isPending?: boolean
}

function formatTimestamp(timestamp: string): string {
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatCrsScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  return score.toFixed(2)
}

export function RecentAlertsTable({ alerts, isPending = false }: RecentAlertsTableProps) {
  if (isPending) {
    return (
      <div className="rounded-lg border border-surface-border bg-surface-card p-4">
        <LoadingSkeleton rows={4} />
      </div>
    )
  }

  const displayAlerts = alerts.slice(0, 4)

  return (
    <div className="rounded-lg border border-surface-border bg-surface-card p-4">
      <div className="flex items-center justify-between mb-3">
        <span className="mb-3 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">
          Recent alerts
        </span>
        <Link href="/alerts" className="text-[11px] text-[var(--color-accent-analytic)] hover:underline">
          View all →
        </Link>
      </div>
      <table className="w-full text-[11px] border-collapse">
        <thead>
          <tr className="text-[var(--color-text-muted)] uppercase tracking-wider text-[11px]">
            <th className="pb-2 text-left px-2">Triage</th>
            <th className="pb-2 text-left px-2">Timestamp</th>
            <th className="pb-2 text-left px-2">Source IP</th>
            <th className="pb-2 text-left px-2">Request</th>
            <th className="pb-2 text-left px-2">Prediction</th>
            <th className="pb-2 text-left px-2">Confidence</th>
            <th className="pb-2 text-left px-2">Action Taken</th>
            <th className="pb-2 text-left px-2">CRS Score</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-surface-border">
          {displayAlerts.map((alert) => (
            <tr
              key={alert.alert_id}
              className="transition-colors hover:bg-surface-inset"
            >
              <td className="p-2">
                <TriageBadge triage_status={alert.triage_status ?? null} />
              </td>
              <td className="p-2 font-mono text-[var(--color-text-secondary)]">{formatTimestamp(alert.timestamp)}</td>
              <td className="p-2 font-mono text-[var(--color-text-secondary)]">{alert.source_ip ?? '—'}</td>
              <td className="p-2 font-mono text-[var(--color-text-secondary)]">{alert.request_path ?? '—'}</td>
              <td className="p-2 text-[var(--color-text-primary)]">{alert.prediction}</td>
              <td className="p-2">
                <ConfidenceBar confidence={alert.confidence} prediction={alert.prediction} />
              </td>
              <td className="p-2">
                <ActionLabel action={alert.action_taken} bordered={false} />
              </td>
              <td className="p-2 font-mono text-[var(--color-text-secondary)]">{formatCrsScore(alert.crs_score)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}


