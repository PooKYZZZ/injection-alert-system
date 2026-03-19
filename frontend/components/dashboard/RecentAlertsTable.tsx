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
  isLoading?: boolean
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

export function RecentAlertsTable({ alerts, isLoading = false }: RecentAlertsTableProps) {
  if (isLoading) {
    return (
      <div className="bg-[#161b22] border border-[#30363d] rounded-lg p-4">
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
      className="bg-[#161b22] border border-[#30363d] rounded-lg p-4"
    >
      <div className="flex items-center justify-between mb-3">
        <span className="text-[12px] font-medium text-[#7d8590] uppercase tracking-wider">
          Recent alerts
        </span>
        <Link href="/alerts" className="text-[10px] text-blue-400 hover:underline">
          View all →
        </Link>
      </div>
      <table className="w-full text-[11px] border-collapse">
        <thead>
          <tr className="text-[#484f58] uppercase tracking-wider text-[10px]">
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
        <tbody className="divide-y divide-[#21262d]">
          {displayAlerts.map((alert) => (
            <tr key={alert.alert_id} className="hover:bg-[#0d1117] transition-colors">
              <td className="p-2">
                <input type="checkbox" className="accent-violet-600" />
              </td>
              <td className="p-2">
                <TriageBadge triage_status={alert.triage_status ?? null} />
              </td>
              <td className="p-2">
                <SeverityBadge severity={alert.confidence_level} prediction={alert.prediction} />
              </td>
              <td className="p-2 font-mono text-[#8b949e]">{formatTimestamp(alert.timestamp)}</td>
              <td className="p-2 font-mono text-violet-400">{alert.source_ip ?? '—'}</td>
              <td className="p-2 font-mono text-[#8b949e]">{alert.request_path ?? '—'}</td>
              <td className="p-2 text-[#e6edf3]">{alert.prediction}</td>
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
