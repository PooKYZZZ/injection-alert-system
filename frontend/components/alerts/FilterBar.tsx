'use client'

import { useCallback, useRef } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'motion/react'
import { TRIAGE_STATUS_VALUES } from '@/features/alerts/schemas'
import {
  ALERT_SEVERITY_VALUES,
  ALERT_ACTION_TAKEN_VALUES,
} from '@/features/alerts/contract'

interface FilterBarProps {
  filteredCount?: number
}

const SEVERITY_CYCLE = ['ALL', ...ALERT_SEVERITY_VALUES] as const
const ACTION_CYCLE = ['ALL', ...ALERT_ACTION_TAKEN_VALUES] as const
const TRIAGE_CYCLE = ['ALL', ...TRIAGE_STATUS_VALUES] as const
const WINDOW_CYCLE = ['ALL', '1h', '6h', '24h', '7d'] as const

type SeverityValue = (typeof SEVERITY_CYCLE)[number]
type ActionValue = (typeof ACTION_CYCLE)[number]
type TriageValue = (typeof TRIAGE_CYCLE)[number]
type WindowValue = (typeof WINDOW_CYCLE)[number]

function FilterSelect<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string
  value: T
  options: readonly T[]
  onChange: (value: T) => void
}) {
  return (
    <label className="flex min-w-0 flex-col gap-1 rounded-md border border-border-light bg-bg-card px-2 py-1.5">
      <span className="text-[10px] leading-none text-[var(--color-text-secondary)]">{label}</span>
      <select
        value={value}
        onChange={(event) => onChange(event.target.value as T)}
        className="w-[96px] min-w-0 bg-transparent text-[11px] font-medium text-[var(--color-text-primary)] outline-none"
      >
        {options.map((option) => (
          <option key={option} value={option} className="bg-bg-card text-[var(--color-text-primary)]">
            {option}
          </option>
        ))}
      </select>
    </label>
  )
}

export function FilterBar({ filteredCount }: FilterBarProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const debounceRef = useRef<NodeJS.Timeout | null>(null)

  const currentSeverity = searchParams.get('severity') ?? 'ALL'
  const currentAction = searchParams.get('action') ?? 'ALL'
  const currentTriage = searchParams.get('triage_status') ?? 'ALL'
  const currentWindow = searchParams.get('window') ?? 'ALL'
  const activeFilterCount = [
    currentSeverity !== 'ALL',
    currentAction !== 'ALL',
    currentTriage !== 'ALL',
    currentWindow !== 'ALL',
  ].filter(Boolean).length

  const hasActiveFilters = activeFilterCount > 0

  const replaceWithParams = useCallback((mutator: (params: URLSearchParams) => void) => {
    if (debounceRef.current) {
      clearTimeout(debounceRef.current)
    }
    debounceRef.current = setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString())
      mutator(params)
      params.set('page', '1')
      const query = params.toString()
      router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
    }, 150)
  }, [router, pathname, searchParams])

  function handleSeverityChange(next: SeverityValue) {
    replaceWithParams((params) => {
      if (next === 'ALL') {
        params.delete('severity')
      } else {
        params.set('severity', next)
      }
    })
  }

  function handleActionChange(next: ActionValue) {
    replaceWithParams((params) => {
      if (next === 'ALL') {
        params.delete('action')
      } else {
        params.set('action', next)
      }
    })
  }

  function handleTriageChange(next: TriageValue) {
    replaceWithParams((params) => {
      if (next === 'ALL') {
        params.delete('triage_status')
      } else {
        params.set('triage_status', next)
      }
    })
  }

  function handleWindowChange(next: WindowValue) {
    replaceWithParams((params) => {
      if (next === 'ALL') {
        params.delete('window')
      } else {
        params.set('window', next)
      }
    })
  }

  

  function handleClearAll() {
    replaceWithParams((params) => {
      params.delete('severity')
      params.delete('action')
      params.delete('triage_status')
      params.delete('window')
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-3 rounded-lg border border-border-light bg-bg-card p-3"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="pt-2 text-[11px] font-medium text-[var(--color-text-secondary)]">Filters:</span>
          <FilterSelect
            label="Triage"
            value={currentTriage as TriageValue}
            options={TRIAGE_CYCLE}
            onChange={handleTriageChange}
          />
          <FilterSelect
            label="Time Window"
            value={currentWindow as WindowValue}
            options={WINDOW_CYCLE}
            onChange={handleWindowChange}
          />
          <FilterSelect
            label="Action Taken"
            value={currentAction as ActionValue}
            options={ACTION_CYCLE}
            onChange={handleActionChange}
          />
          <FilterSelect
            label="Confidence"
            value={currentSeverity as SeverityValue}
            options={SEVERITY_CYCLE}
            onChange={handleSeverityChange}
          />
        </div>

        <div className="flex items-center gap-3">
          {activeFilterCount > 0 && (
            <motion.span
              key={activeFilterCount}
              animate={{ scale: [1.2, 1] }}
              className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-accent-purple px-1.5 text-[10px] font-medium text-bg-page"
            >
              {activeFilterCount}
            </motion.span>
          )}
          {hasActiveFilters && (
            <button
              onClick={handleClearAll}
              className="text-[11px] text-accent-purple transition-colors hover:text-primary"
            >
              Clear all
            </button>
          )}
          {filteredCount !== undefined && (
            <span className="text-[11px] text-[var(--color-text-secondary)]">
              {filteredCount} results
            </span>
          )}
        </div>
      </div>
    </motion.div>
  )
}


