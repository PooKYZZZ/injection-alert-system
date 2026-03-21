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
          ? 'border-[var(--color-accent-blue-bg)] bg-[var(--color-bg-panel)] text-blue-400'
          : 'border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
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
          ? 'border-violet-500 bg-violet-600 text-white'
          : 'border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]'
      )}
    >
      {label}
    </button>
  )
}


