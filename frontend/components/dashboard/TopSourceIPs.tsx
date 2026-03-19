'use client'

import { cn } from '@/lib/utils'
import { LoadingSkeleton, EmptyState } from '@/components/ui/StateViews'
import type { AlertAction } from '@/features/alerts/contract'

export interface SourceIPSummary {
  ip: string
  count: number
  action: AlertAction
}

interface TopSourceIPsProps {
  ips: SourceIPSummary[]
  isLoading?: boolean
}

const statusStyles: Record<AlertAction, string> = {
  BLOCKED: 'bg-[#2d1b1b] text-red-400',
  THROTTLED: 'bg-[#2d2310] text-amber-400',
  ALLOWED: 'bg-[#0f2d1a] text-emerald-400',
}

const actionLabels: Record<AlertAction, string> = {
  BLOCKED: 'Blocked',
  THROTTLED: 'Throttled',
  ALLOWED: 'Allowed',
}

export function TopSourceIPs({ ips, isLoading = false }: TopSourceIPsProps) {
  if (isLoading) {
    return <LoadingSkeleton rows={4} />
  }

  if (ips.length === 0) {
    return <EmptyState message="No source IP data" subtext="Top IPs will appear here when available" />
  }

  return (
    <div className="flex flex-col gap-1.5">
      {ips.map((item) => (
        <div
          key={item.ip}
          className="flex items-center justify-between py-1 border-b border-[#21262d] last:border-0 text-[11px]"
        >
          <span className="font-mono text-violet-400">{item.ip}</span>
          <div className="flex items-center gap-2">
            <span className="font-medium">{item.count}</span>
            <span
              className={cn(
                'text-[10px] px-1.5 py-0.5 rounded-full font-medium',
                statusStyles[item.action]
              )}
            >
              {actionLabels[item.action]}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
