'use client'

import { cn } from '@/lib/utils'
import { LoadingSkeleton } from '@/components/ui/StateViews'
import type { AlertAction } from '@/features/alerts/contract'

export interface SourceIPSummary {
  ip: string
  count: number
  action: AlertAction | null
}

interface TopSourceIPsProps {
  ips: SourceIPSummary[]
  isPending?: boolean
}

const statusStyles: Record<AlertAction, string> = {
  BLOCKED: 'bg-[var(--color-severity-high-bg)] text-severity-high-text',
  THROTTLED: 'bg-[var(--color-severity-blocked-bg)] text-severity-blocked-text',
  ALLOWED: 'bg-[var(--color-severity-safe-bg)] text-severity-safe-text',
}

const actionLabels: Record<AlertAction, string> = {
  BLOCKED: 'Blocked',
  THROTTLED: 'Throttled',
  ALLOWED: 'Allowed',
}

export function TopSourceIPs({ ips, isPending = false }: TopSourceIPsProps) {
  if (isPending) {
    return <LoadingSkeleton rows={4} />
  }

  if (ips.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-6 gap-2">
        <p className="text-[11px] font-medium text-[var(--color-text-secondary)]">
          No source IPs in this window
        </p>
        <p className="text-[10px] text-[var(--color-text-muted)] text-center max-w-[160px] leading-relaxed">
          IPs appear when blocked or throttled traffic is detected
        </p>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-1.5">
      {ips.map((item) => (
        <div
          key={item.ip}
          className="flex items-center justify-between border-b border-surface-border py-3 text-[11px] last:border-0"
        >
          <span className="font-mono text-[var(--color-accent-analytic)]">{item.ip}</span>
          <div className="flex items-center gap-2">
            <span className="font-medium text-[var(--color-text-primary)]">{item.count}</span>
            {item.action && statusStyles[item.action as AlertAction] && (
              <span
                className={cn(
                  'text-[11px] px-1.5 py-0.5 rounded-full font-medium',
                  statusStyles[item.action as AlertAction]
                )}
              >
                {actionLabels[item.action as AlertAction]}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

