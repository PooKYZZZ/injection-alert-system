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
      <section
        aria-label="Recent alerts table"
        className="min-w-0 rounded-lg border border-surface-border bg-surface-card p-4"
      >
        <LoadingSkeleton rows={4} />
      </section>
    )
  }

  const displayAlerts = alerts.slice(0, 4)

  return (
    <section
      aria-label="Recent alerts table"
      className="min-w-0 rounded-lg border border-surface-border bg-surface-card p-4"
    >
      <div className="mb-3 flex items-center justify-between gap-3">
        <h2 id="recent-alerts-title" className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)]">
          Recent alerts
        </h2>
        <Link href="/alerts" className="text-[11px] text-[var(--color-accent-analytic)] hover:underline">
          View all →
        </Link>
      </div>
      <div
        data-testid="recent-alerts-scroll"
        role="region"
        aria-label="Recent alerts data"
        tabIndex={0}
        className="min-w-0 overflow-x-auto rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-card"
      >
        <table aria-labelledby="recent-alerts-title" className="min-w-[720px] w-full border-collapse text-[11px]">
          <thead>
            <tr className="text-[var(--color-text-muted)] uppercase tracking-wider text-[11px]">
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Triage</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Timestamp</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Source IP</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Request</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Prediction</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Confidence</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Action Taken</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">CRS Score</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-surface-border">
            {displayAlerts.length > 0 ? (
              displayAlerts.map((alert) => (
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
              ))
            ) : (
              <tr>
                <td colSpan={8} className="px-2 py-8 text-center text-xs text-text-muted">
                  No recent alerts in this window.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  )
}
