import { cn } from '@/lib/utils'

export type StatusTone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'
export type StatusDomain = 'workflow' | 'enforcement' | 'lifecycle' | 'auth' | 'health'

interface StatusBadgeProps {
  label: string
  tone?: StatusTone
  domain?: StatusDomain
  bordered?: boolean
  className?: string
}

const toneClasses: Record<StatusTone, string> = {
  neutral: 'border-border-light bg-surface-inset text-text-secondary',
  info: 'border-action-border/50 bg-action-bg text-action-accent',
  success: 'border-severity-safe-border/60 bg-severity-safe-bg text-severity-safe-text',
  warning: 'border-severity-blocked-border/60 bg-severity-blocked-bg text-severity-blocked-text',
  danger: 'border-severity-high-border/60 bg-severity-high-bg text-severity-high-text',
}

const toneTextClasses: Record<StatusTone, string> = {
  neutral: 'text-text-secondary',
  info: 'text-action-accent',
  success: 'text-severity-safe-text',
  warning: 'text-severity-blocked-text',
  danger: 'text-severity-high-text',
}

export function StatusBadge({ label, tone = 'neutral', domain, bordered = true, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center rounded px-2 py-0.5 text-xs font-medium leading-5',
        bordered ? `border ${toneClasses[tone]}` : toneTextClasses[tone],
        className
      )}
      data-status-domain={domain}
    >
      {label}
    </span>
  )
}
