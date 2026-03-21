'use client'

import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { motion } from 'motion/react'
import { FilterChip, ConfidencePill } from '@/components/ui/FilterChip'
import { TRIAGE_STATUS_VALUES } from '@/features/alerts/schemas'
import { ALERT_SEVERITY_VALUES, ALERT_ACTION_TAKEN_VALUES } from '@/features/alerts/contract'

interface FilterBarProps {
  filteredCount?: number
}

const SEVERITY_CYCLE = ['ALL', ...ALERT_SEVERITY_VALUES] as const
const ACTION_CYCLE = ['ALL', ...ALERT_ACTION_TAKEN_VALUES] as const
const TRIAGE_CYCLE = ['ALL', ...TRIAGE_STATUS_VALUES] as const
const WINDOW_CYCLE = ['ALL', '1h', '6h', '24h', '7d'] as const

const CONFIDENCE_LEVELS = [
  { value: 'HIGH', label: 'High >80%' },
  { value: 'MEDIUM', label: 'Med 50–80%' },
  { value: 'LOW', label: 'Low <50%' },
] as const

export function FilterBar({ filteredCount }: FilterBarProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()

  const currentSeverity = searchParams.get('severity') ?? 'ALL'
  const currentAction = searchParams.get('action') ?? 'ALL'
  const currentTriage = searchParams.get('triage_status') ?? 'ALL'
  const currentWindow = searchParams.get('window') ?? 'ALL'
  const currentConfidence = searchParams.getAll('confidence_level')

  const activeFilterCount = [
    currentSeverity !== 'ALL',
    currentAction !== 'ALL',
    currentTriage !== 'ALL',
    currentWindow !== 'ALL',
    currentConfidence.length > 0,
  ].filter(Boolean).length

  const hasActiveFilters = activeFilterCount > 0

  function replaceWithParams(mutator: (params: URLSearchParams) => void) {
    const params = new URLSearchParams(searchParams.toString())
    mutator(params)
    params.set('page', '1')
    const query = params.toString()
    router.replace(query ? `${pathname}?${query}` : pathname, { scroll: false })
  }

  function cycleValue<T extends string>(current: string, cycle: readonly T[]): T {
    const index = cycle.indexOf(current as T)
    const nextIndex = (index + 1) % cycle.length
    return cycle[nextIndex]
  }

  function handleSeverityClick() {
    replaceWithParams((params) => {
      const next = cycleValue(currentSeverity, SEVERITY_CYCLE)
      if (next === 'ALL') {
        params.delete('severity')
      } else {
        params.set('severity', next)
      }
    })
  }

  function handleActionClick() {
    replaceWithParams((params) => {
      const next = cycleValue(currentAction, ACTION_CYCLE)
      if (next === 'ALL') {
        params.delete('action')
      } else {
        params.set('action', next)
      }
    })
  }

  function handleTriageClick() {
    replaceWithParams((params) => {
      const next = cycleValue(currentTriage, TRIAGE_CYCLE)
      if (next === 'ALL') {
        params.delete('triage_status')
      } else {
        params.set('triage_status', next)
      }
    })
  }

  function handleWindowClick() {
    replaceWithParams((params) => {
      const next = cycleValue(currentWindow, WINDOW_CYCLE)
      if (next === 'ALL') {
        params.delete('window')
      } else {
        params.set('window', next)
      }
    })
  }

  function handleConfidenceToggle(value: string) {
    replaceWithParams((params) => {
      params.delete('confidence_level')
      const isCurrentlySelected = currentConfidence.includes(value)
      const newValues = isCurrentlySelected
        ? currentConfidence.filter((v) => v !== value)
        : [...currentConfidence, value]
      for (const v of newValues) {
        params.append('confidence_level', v)
      }
    })
  }

  function handleClearAll() {
    replaceWithParams((params) => {
      params.delete('severity')
      params.delete('action')
      params.delete('triage_status')
      params.delete('window')
      params.delete('confidence_level')
    })
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex flex-col gap-3 rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] p-3"
    >
      {/* Row 1: Filter chips */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-[11px] text-[var(--color-text-secondary)]">Filter:</span>
          <FilterChip
            label={`Severity: ${currentSeverity}`}
            active={currentSeverity !== 'ALL'}
            onClick={handleSeverityClick}
          />
          <FilterChip
            label={`Action: ${currentAction}`}
            active={currentAction !== 'ALL'}
            onClick={handleActionClick}
          />
          <FilterChip
            label={`Triage: ${currentTriage}`}
            active={currentTriage !== 'ALL'}
            onClick={handleTriageClick}
          />
          <FilterChip
            label={`Window: ${currentWindow}`}
            active={currentWindow !== 'ALL'}
            onClick={handleWindowClick}
          />
        </div>

        <div className="flex items-center gap-3">
          {activeFilterCount > 0 && (
            <motion.span
              key={activeFilterCount}
              animate={{ scale: [1.2, 1] }}
              className="flex h-5 min-w-[20px] items-center justify-center rounded-full bg-blue-500 px-1.5 text-[10px] font-medium text-white"
            >
              {activeFilterCount}
            </motion.span>
          )}
          {hasActiveFilters && (
            <button
              onClick={handleClearAll}
              className="text-[11px] text-blue-400 hover:text-blue-300"
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

      {/* Row 2: Confidence pills */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] text-[var(--color-text-secondary)]">Confidence:</span>
        {CONFIDENCE_LEVELS.map(({ value, label }) => (
          <ConfidencePill
            key={value}
            label={label}
            active={currentConfidence.includes(value)}
            onClick={() => handleConfidenceToggle(value)}
          />
        ))}
      </div>
    </motion.div>
  )
}


