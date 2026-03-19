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
          ? 'border-[#1f3a5c] bg-[#1c2433] text-blue-400'
          : 'border-[#30363d] bg-[#161b22] text-[#7d8590] hover:text-[#e6edf3]'
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
          : 'border-[#30363d] bg-[#161b22] text-[#7d8590] hover:text-[#e6edf3]'
      )}
    >
      {label}
    </button>
  )
}
