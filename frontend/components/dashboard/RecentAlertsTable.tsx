'use client'

import Link from 'next/link'
import { LoadingSkeleton } from '@/components/ui/StateViews'
import { ActionLabel } from '@/components/ui/ActionLabel'
import { ConfidenceSummary } from '@/components/ui/ConfidenceSummary'
import { TriageBadge } from '@/components/ui/TriageBadge'
import type { Alert } from '@/features/alerts/types'
import { formatAlertDateTime } from '@/lib/date-time'

interface RecentAlertsTableProps {
  alerts: Alert[]
  isPending?: boolean
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
        <h2 id="recent-alerts-title" className="text-sm font-semibold text-text-primary">
          Recent alerts
        </h2>
        <Link href="/alerts" className="text-[11px] text-[var(--color-accent-analytic)] hover:underline">
          View all →
        </Link>
      </div>
      <div className="space-y-3 xl:hidden" data-testid="recent-alerts-mobile">
        {displayAlerts.length > 0 ? (
          displayAlerts.map((alert) => (
            <article
              key={alert.alert_id}
              aria-label={`${alert.prediction} alert`}
              className="rounded-md border border-surface-border bg-surface-panel p-3"
            >
              <div className="flex min-w-0 items-start justify-between gap-3">
                <h3 className="min-w-0 break-words text-sm font-semibold text-text-primary">
                  {alert.prediction}
                </h3>
                <TriageBadge triage_status={alert.triage_status ?? null} />
              </div>
              <div className="mt-2 flex flex-wrap items-center justify-between gap-x-3 gap-y-2">
                <ConfidenceSummary
                  confidence={alert.confidence}
                  confidenceTier={alert.confidence_level}
                />
                <ActionLabel
                  action={alert.action_taken}
                  confidenceTier={alert.confidence_level}
                  prediction={alert.prediction}
                  bordered={false}
                />
              </div>
              <dl className="mt-3 grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-xs">
                <dt className="text-text-muted">Source IP</dt>
                <dd className="truncate text-right font-mono text-text-secondary">{alert.source_ip ?? '—'}</dd>
                <dt className="text-text-muted">Recorded</dt>
                <dd className="text-right text-text-secondary">
                  <time dateTime={alert.timestamp}>{formatAlertDateTime(alert.timestamp)}</time>
                </dd>
              </dl>
              <div className="mt-3 flex min-w-0 items-center justify-between gap-3 border-t border-surface-border pt-2">
                <span className="min-w-0 truncate font-mono text-[11px] text-text-secondary">
                  {alert.request_method ? `${alert.request_method.toUpperCase()} ` : ''}{alert.request_path ?? '—'}
                </span>
                <Link
                  href={`/alerts?alert_id=${encodeURIComponent(alert.alert_id)}`}
                  aria-label={`View details for ${alert.alert_id}`}
                  className="shrink-0 rounded px-1.5 py-1 text-xs font-medium text-[var(--color-accent-analytic)] hover:bg-surface-inset focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85"
                >
                  View details
                </Link>
              </div>
            </article>
          ))
        ) : (
          <p className="rounded-md border border-dashed border-surface-border px-3 py-6 text-center text-xs text-text-muted">
            No recent alerts in this window.
          </p>
        )}
      </div>
      <div
        data-testid="recent-alerts-scroll"
        role="region"
        aria-label="Recent alerts data"
        tabIndex={0}
        className="hidden min-w-0 overflow-x-auto rounded-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-card xl:block"
      >
        <table aria-labelledby="recent-alerts-title" className="min-w-[780px] w-full border-collapse text-xs">
          <thead>
            <tr className="text-[var(--color-text-secondary)] text-xs">
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Triage</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Timestamp</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Source IP</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Request</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Prediction</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Confidence</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">Recorded action</th>
              <th scope="col" className="whitespace-nowrap px-2 pb-2 text-left">View</th>
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
                  <td className="p-2 font-mono text-[var(--color-text-secondary)]">
                    <time dateTime={alert.timestamp}>{formatAlertDateTime(alert.timestamp)}</time>
                  </td>
                  <td className="p-2 font-mono text-[var(--color-text-secondary)]">{alert.source_ip ?? '—'}</td>
                  <td className="p-2 font-mono text-[var(--color-text-secondary)]">{alert.request_path ?? '—'}</td>
                  <td className="p-2 text-[var(--color-text-primary)]">{alert.prediction}</td>
                  <td className="p-2">
                    <ConfidenceSummary
                      confidence={alert.confidence}
                      confidenceTier={alert.confidence_level}
                    />
                  </td>
                  <td className="p-2">
                    <ActionLabel
                      action={alert.action_taken}
                      confidenceTier={alert.confidence_level}
                      prediction={alert.prediction}
                      bordered={false}
                    />
                  </td>
                  <td className="p-2">
                    <Link
                      href={`/alerts?alert_id=${encodeURIComponent(alert.alert_id)}`}
                      aria-label={`View details for ${alert.alert_id}`}
                      className="text-[var(--color-accent-analytic)] hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent-action/85"
                    >
                      View
                    </Link>
                  </td>
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
