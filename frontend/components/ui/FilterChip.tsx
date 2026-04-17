'use client'

import { cn } from '@/lib/utils'

interface FilterChipProps {
  label: string
  active: boolean
  onClick: () => void
}

interface ConfidencePillProps {
  label: string
  active: boolean
  onClick: () => void
}

export function FilterChip({ label, active, onClick }: FilterChipProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'cursor-pointer rounded-full border px-2.5 py-0.5 text-[11px] transition-all',
        active
          ? 'border-accent-action bg-surface-inset text-accent-action'
          : 'border-surface-border bg-surface-card text-text-secondary hover:bg-surface-inset hover:text-text-primary'
      )}
    >
      {label} {active && '▾'}
    </button>
  )
}

export function ConfidencePill({ label, active, onClick }: ConfidencePillProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'cursor-pointer rounded border px-2 py-0.5 text-[10px] transition-all',
        active
          ? 'border-accent-action bg-surface-inset text-accent-action'
          : 'border-surface-border bg-surface-card text-text-secondary hover:bg-surface-inset hover:text-text-primary'
      )}
    >
      {label}
    </button>
  )
}


