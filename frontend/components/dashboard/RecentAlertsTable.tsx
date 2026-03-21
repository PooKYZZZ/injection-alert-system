'use client'

import Link from 'next/link'
import { motion } from 'motion/react'
import { LoadingSkeleton } from '@/components/ui/StateViews'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { ActionLabel } from '@/components/ui/ActionLabel'
import { ConfidenceBar } from '@/components/ui/ConfidenceBar'
import { TriageBadge } from '@/components/ui/TriageBadge'
import type { Alert } from '@/features/alerts/types'

interface RecentAlertsTableProps {
  alerts: Alert[]
  isPending?: boolean
}

function formatTimestamp(timestamp: string): string {
  const date = new Date(timestamp)
  // Use UTC methods to avoid server/client timezone mismatch during Next.js hydration
  const month = date.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' })
  const day = date.getUTCDate()
  const hours = date.getUTCHours()
  const minutes = date.getUTCMinutes().toString().padStart(2, '0')
  const period = hours >= 12 ? 'PM' : 'AM'
  const displayHour = hours % 12 || 12
  return `${month} ${day}, ${displayHour}:${minutes} ${period}`
}

export function RecentAlertsTable({ alerts, isPending = false }: RecentAlertsTableProps) {
  if (isPending) {
    return (
      <div className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-4">
        <LoadingSkeleton rows={4} />
      </div>
    )
  }

  const displayAlerts = alerts.slice(0, 4)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: 'easeOut' }}
      className="bg-[var(--color-bg-panel)] border border-[var(--color-text-ghost)] rounded-lg p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--color-text-muted)] mb-3">
          Recent alerts
        </span>
        <Link href="/alerts" className="text-[11px] text-blue-400 hover:underline">
          View all →
        </Link>
      </div>
      <table className="w-full text-[11px] border-collapse">
        <thead>
          <tr className="text-[var(--color-text-muted)] uppercase tracking-wider text-[11px]">
            <th className="pb-2 text-left px-2">
              <input type="checkbox" className="accent-violet-600" />
            </th>
            <th className="pb-2 text-left px-2">Triage</th>
            <th className="pb-2 text-left px-2">Severity</th>
            <th className="pb-2 text-left px-2">Timestamp</th>
            <th className="pb-2 text-left px-2">Source IP</th>
            <th className="pb-2 text-left px-2">Target path</th>
            <th className="pb-2 text-left px-2">Attack type</th>
            <th className="pb-2 text-left px-2">ML confidence</th>
            <th className="pb-2 text-left px-2">Action</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-text-ghost)]">
          {displayAlerts.map((alert) => (
            <tr key={alert.alert_id} className="hover:bg-[var(--color-bg-base)] transition-colors">
              <td className="p-2">
                <input type="checkbox" className="accent-violet-600" />
              </td>
              <td className="p-2">
                <TriageBadge triage_status={alert.triage_status ?? null} />
              </td>
              <td className="p-2">
                <SeverityBadge severity={alert.confidence_level} prediction={alert.prediction} />
              </td>
              <td className="p-2 font-mono text-[var(--color-text-secondary)]">{formatTimestamp(alert.timestamp)}</td>
              <td className="p-2 font-mono text-violet-400">{alert.source_ip ?? '—'}</td>
              <td className="p-2 font-mono text-[var(--color-text-secondary)]">{alert.request_path ?? '—'}</td>
              <td className="p-2 text-[var(--color-text-primary)]">{alert.prediction}</td>
              <td className="p-2">
                <ConfidenceBar confidence={alert.confidence} prediction={alert.prediction} />
              </td>
              <td className="p-2">
                <ActionLabel action={alert.action_taken} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </motion.div>
  )
}


