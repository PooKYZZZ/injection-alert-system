'use client'

import type { UseQueryResult } from '@tanstack/react-query'
import { useEffect, useRef, useState, Suspense } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useShallow } from 'zustand/react/shallow'
import { useAlerts } from 'features/alerts/queries'
import type { Alert, PaginatedAlerts } from 'features/alerts/types'
import { useDashboardStore } from 'store/dashboardStore'
import {
  DEFAULT_FILTERS,
  type DashboardFilters,
  type SeverityFilter,
  type TimeRange,
} from 'lib/searchParams'
import { cn } from 'lib/utils'
import { SeverityBadge } from 'components/ui/SeverityBadge'
import { ConfidenceBar } from 'components/ui/ConfidenceBar'
import { ActionLabel } from 'components/ui/ActionLabel'
import BulkActionBar from 'components/dashboard/AlertsTable/BulkActionBar'

type TriageStatus = 'New' | 'In Progress' | 'Closed'
type TriageDisposition =
  | 'Confirmed Threat'
  | 'False Positive'
  | 'Benign / Expected'
  | 'Needs Follow-up'

interface TriageEntry {
  status: TriageStatus
  disposition: TriageDisposition | null
}

interface DashboardStoreState {
  selectedAlertIds: Set<string>
  toggleAlertSelection: (id: string) => void
  selectAll: (ids: string[]) => void
  clearSelection: () => void
  setActiveIncident: (id: string | null) => void
}

const TRIAGE_STORAGE_KEY = 'cybertrace.localTriageStatus'
const TRIAGE_STATUS_OPTIONS: TriageStatus[] = ['New', 'In Progress', 'Closed']
const TRIAGE_DISPOSITION_OPTIONS: TriageDisposition[] = [
  'Confirmed Threat',
  'False Positive',
  'Benign / Expected',
  'Needs Follow-up',
]
const AUTO_SAVE_DELAY_MS = 450
const SAVE_CONFIRMED_DURATION_MS = 1800
const ALERT_TABLE_COLUMN_COUNT = 11
const ALERT_TABLE_HEADERS = [
  'Triage Status (Local)',
  'Confidence Level',
  'Timestamp',
  'Source IP',
  'CRS Score',
  'Target Path',
  'Rule IDs',
  'Attack Type',
  'ML Confidence',
  'Action',
] as const
const FOCUS_RING_CLASS =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-light'
const CHECKBOX_CLASS = cn(
  'h-6 w-6 cursor-pointer rounded border-border-light bg-surface-light text-primary',
  FOCUS_RING_CLASS
)

type SaveState = 'idle' | 'saving' | 'saved'

function formatRuleIds(ruleIds: string[] | null | undefined): string {
  if (!ruleIds || ruleIds.length === 0) return '—'
  if (ruleIds.length === 1) return ruleIds[0]
  return `${ruleIds[0]} +${ruleIds.length - 1}`
}

function formatCrsScore(score: number | null | undefined): string {
  return score === null || score === undefined ? '—' : Number(score).toFixed(2)
}

function defaultTriageEntry(): TriageEntry {
  return { status: 'New', disposition: null }
}

function formatLoadedAt(timestamp: number): string | null {
  if (!Number.isFinite(timestamp) || timestamp <= 0) {
    return null
  }

  return new Date(timestamp).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
}

function sanitizeTriageRecord(value: unknown): Record<string, TriageEntry> {
  if (!value || typeof value !== 'object') {
    return {}
  }

  const entries = Object.entries(value as Record<string, unknown>)
  const sanitized: Record<string, TriageEntry> = {}

  for (const [alertId, entry] of entries) {
    if (!entry || typeof entry !== 'object') continue

    const status = (entry as { status?: unknown }).status
    const disposition = (entry as { disposition?: unknown }).disposition

    if (status !== 'New' && status !== 'In Progress' && status !== 'Closed') {
      continue
    }

    sanitized[alertId] = {
      status,
      disposition:
        disposition === 'Confirmed Threat' ||
        disposition === 'False Positive' ||
        disposition === 'Benign / Expected' ||
        disposition === 'Needs Follow-up'
          ? disposition
          : null,
    }
  }

  return sanitized
}

function AlertsTableSkeletonRows({ rowCount = 3 }: { rowCount?: number }) {
  return (
    <>
      {Array.from({ length: rowCount }).map((_, index) => (
        <tr key={index} aria-hidden="true" className="border-l-[3px] border-l-border-light">
          <td className="p-3">
            <div className="h-4 w-4 animate-pulse rounded-sm bg-border-light" />
          </td>
          <td className="p-3 align-top">
            <div className="flex min-w-[180px] flex-col gap-2">
              <div className="h-8 w-full animate-pulse rounded-sm bg-border-light" />
              <div className="h-7 w-36 animate-pulse rounded-sm bg-border-light" />
              <div className="h-7 w-14 animate-pulse rounded-sm bg-border-light" />
            </div>
          </td>
          <td className="p-3">
            <div className="h-6 w-28 animate-pulse rounded-full bg-border-light" />
          </td>
          <td className="p-3">
            <div className="h-4 w-32 animate-pulse rounded-sm bg-border-light" />
          </td>
          <td className="p-3">
            <div className="h-4 w-24 animate-pulse rounded-sm bg-border-light" />
          </td>
          <td className="p-3">
            <div className="h-4 w-12 animate-pulse rounded-sm bg-border-light" />
          </td>
          <td className="p-3">
            <div className="h-4 w-40 animate-pulse rounded-sm bg-border-light" />
          </td>
          <td className="p-3">
            <div className="h-4 w-20 animate-pulse rounded-sm bg-border-light" />
          </td>
          <td className="p-3">
            <div className="h-4 w-24 animate-pulse rounded-sm bg-border-light" />
          </td>
          <td className="p-3">
            <div className="h-3 w-24 animate-pulse rounded-full bg-border-light" />
          </td>
          <td className="p-3">
            <div className="h-5 w-20 animate-pulse rounded-full bg-border-light" />
          </td>
        </tr>
      ))}
    </>
  )
}

function AlertsTableShell({
  selectedIds,
  alerts,
  selectAll,
  clearSelection,
  children,
}: {
  selectedIds: string[]
  alerts: Alert[]
  selectAll: (ids: string[]) => void
  clearSelection: () => void
  children: React.ReactNode
}) {
  return (
    <div className="bg-surface-light border border-border-light rounded-sm shadow-subtle overflow-hidden">
      <div className="flex items-start justify-between gap-4 border-b border-border-light p-4">
        <div>
          <h2 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider">
            Alerts
          </h2>
          <p className="mt-1 text-xs text-text-muted">
            Triage status is stored locally in this browser for demo purposes only.
          </p>
        </div>
        {selectedIds.length > 0 && <BulkActionBar />}
      </div>
      <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-light bg-sidebar-active">
              <th className="p-3 w-10">
                <input
                  type="checkbox"
                  checked={alerts.length > 0 && selectedIds.length === alerts.length}
                  onChange={(e) => {
                    if (e.target.checked) {
                      selectAll(alerts.map((a) => a.alert_id))
                    } else {
                      clearSelection()
                    }
                  }}
                  className={CHECKBOX_CLASS}
                  aria-label="Select all alerts"
                />
              </th>
              {ALERT_TABLE_HEADERS.map((header) => (
                <th
                  key={header}
                  className="p-3 text-left text-[10px] font-semibold text-text-muted uppercase tracking-wider"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-light">{children}</tbody>
        </table>
      </div>
    </div>
  )
}

function AlertsTableStateRow({
  title,
  detail,
  meta,
  action,
}: {
  title: string
  detail?: string
  meta?: string | null
  action?: React.ReactNode
}) {
  return (
    <tr>
      <td colSpan={ALERT_TABLE_COLUMN_COUNT} className="p-8">
        <div className="flex flex-col items-center justify-center gap-2 text-center">
          <p className="text-sm font-medium text-text-main">{title}</p>
          {detail ? <p className="text-xs text-text-muted">{detail}</p> : null}
          {meta ? <p className="text-[11px] text-text-muted">{meta}</p> : null}
          {action ? <div className="pt-1">{action}</div> : null}
        </div>
      </td>
    </tr>
  )
}

function AlertsTableContent() {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [hydrated, setHydrated] = useState(false)
  const [savedTriage, setSavedTriage] = useState<Record<string, TriageEntry>>({})
  const [draftTriage, setDraftTriage] = useState<Record<string, TriageEntry>>({})
  const [saveStates, setSaveStates] = useState<Record<string, SaveState>>({})
  const saveTimeoutsRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({})
  const saveResetTimeoutsRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  const filters: DashboardFilters = {
    severity: (searchParams?.get('severity') ?? 'ALL') as SeverityFilter,
    timeRange: (searchParams?.get('timeRange') ?? '24h') as TimeRange,
    search: searchParams?.get('search') ?? '',
  }

  const { toggleAlertSelection, selectAll, clearSelection, setActiveIncident } = useDashboardStore()
  const selectedIds = useDashboardStore(useShallow((s: DashboardStoreState) => [...s.selectedAlertIds]))

  useEffect(() => {
    if (selectedIds.length > 0) clearSelection()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.severity, filters.timeRange, filters.search])

  const alertsQuery: UseQueryResult<PaginatedAlerts, Error> = useAlerts(filters)
  const { data, isPending, isError, error, dataUpdatedAt } = alertsQuery

  const alerts = data?.items ?? []
  const hasFilter =
    filters.search.trim().length > 0 ||
    filters.severity !== DEFAULT_FILTERS.severity ||
    filters.timeRange !== DEFAULT_FILTERS.timeRange
  const lastLoadedAt = formatLoadedAt(dataUpdatedAt)
  const retryAlerts = () => {
    void alertsQuery.refetch()
  }

  useEffect(() => {
    setHydrated(true)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return

    try {
      const storedValue = window.localStorage.getItem(TRIAGE_STORAGE_KEY)
      const parsedValue = storedValue ? JSON.parse(storedValue) : {}
      const sanitized = sanitizeTriageRecord(parsedValue)
      setSavedTriage(sanitized)
      setDraftTriage(sanitized)
    } catch {
      setSavedTriage({})
      setDraftTriage({})
    }
  }, [])

  useEffect(() => {
    return () => {
      Object.values(saveTimeoutsRef.current).forEach((timeoutId) => clearTimeout(timeoutId))
      Object.values(saveResetTimeoutsRef.current).forEach((timeoutId) => clearTimeout(timeoutId))
    }
  }, [])

  if (!hydrated) {
    return (
      <AlertsTableShell
        selectedIds={selectedIds}
        alerts={[]}
        selectAll={selectAll}
        clearSelection={clearSelection}
      >
        <AlertsTableSkeletonRows />
      </AlertsTableShell>
    )
  }

  function getRowBorderClass(alert: Alert): string {
    if (alert.confidence_level === 'HIGH') return 'border-l-[3px] border-l-red-500'
    if (alert.confidence_level === 'MEDIUM') return 'border-l-[3px] border-l-orange-400'
    return 'border-l-[3px] border-l-gray-300'
  }

  function getTriageEntry(source: Record<string, TriageEntry>, alertId: string): TriageEntry {
    return source[alertId] ?? defaultTriageEntry()
  }

  function updateDraft(alertId: string, nextEntry: TriageEntry) {
    setDraftTriage((current) => ({
      ...current,
      [alertId]: nextEntry,
    }))

    if (saveTimeoutsRef.current[alertId]) {
      clearTimeout(saveTimeoutsRef.current[alertId])
      delete saveTimeoutsRef.current[alertId]
    }

    if (saveResetTimeoutsRef.current[alertId]) {
      clearTimeout(saveResetTimeoutsRef.current[alertId])
      delete saveResetTimeoutsRef.current[alertId]
    }

    if (nextEntry.status === 'Closed' && !nextEntry.disposition) {
      setSaveStates((current) => ({
        ...current,
        [alertId]: 'idle',
      }))
      return
    }

    setSaveStates((current) => ({
      ...current,
      [alertId]: 'saving',
    }))

    saveTimeoutsRef.current[alertId] = setTimeout(() => {
      persistTriage(alertId, nextEntry)
      delete saveTimeoutsRef.current[alertId]
    }, AUTO_SAVE_DELAY_MS)
  }

  function persistTriage(alertId: string, nextEntry = getTriageEntry(draftTriage, alertId)) {
    if (nextEntry.status === 'Closed' && !nextEntry.disposition) {
      return
    }

    const nextSaved = {
      ...savedTriage,
      [alertId]: nextEntry,
    }
    setSavedTriage(nextSaved)

    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(TRIAGE_STORAGE_KEY, JSON.stringify(nextSaved))
      } catch {
        // Keep local triage usable even if browser storage is unavailable.
      }
    }

    setSaveStates((current) => ({
      ...current,
      [alertId]: 'saved',
    }))

    saveResetTimeoutsRef.current[alertId] = setTimeout(() => {
      setSaveStates((current) => ({
        ...current,
        [alertId]: 'idle',
      }))
      delete saveResetTimeoutsRef.current[alertId]
    }, SAVE_CONFIRMED_DURATION_MS)
  }

  return (
    <AlertsTableShell
      selectedIds={selectedIds}
      alerts={alerts}
      selectAll={selectAll}
      clearSelection={clearSelection}
    >
      {isPending ? <AlertsTableSkeletonRows /> : null}

      {isError ? (
        <AlertsTableStateRow
          title="Unable to load alerts."
          detail={error instanceof Error ? error.message : 'Unexpected error while loading alerts.'}
          action={
            <button
              type="button"
              onClick={retryAlerts}
              className={cn(
                'rounded-sm border border-border-light px-3 py-1.5 text-xs font-medium text-text-main transition-colors hover:bg-sidebar-active',
                FOCUS_RING_CLASS
              )}
            >
              Retry
            </button>
          }
        />
      ) : null}

      {!isPending && !isError && !data ? (
        <AlertsTableStateRow
          title="Unable to load alerts."
          detail="The alerts response did not include a table payload."
          action={
            <button
              type="button"
              onClick={retryAlerts}
              className={cn(
                'rounded-sm border border-border-light px-3 py-1.5 text-xs font-medium text-text-main transition-colors hover:bg-sidebar-active',
                FOCUS_RING_CLASS
              )}
            >
              Retry
            </button>
          }
        />
      ) : null}

      {!isPending && !isError && data && alerts.length === 0 ? (
        <AlertsTableStateRow
          title={
            hasFilter ? 'No alerts match the current filters.' : 'No alerts in the selected range.'
          }
          meta={lastLoadedAt ? `Last loaded ${lastLoadedAt}` : null}
          action={
            hasFilter && pathname ? (
              <button
                type="button"
                onClick={() => void router.replace(pathname)}
                className={cn(
                  'rounded-sm border border-border-light px-3 py-1.5 text-xs font-medium text-text-main transition-colors hover:bg-sidebar-active',
                  FOCUS_RING_CLASS
                )}
              >
                Clear filters
              </button>
            ) : undefined
          }
        />
      ) : null}

      {!isPending && !isError && data
        ? alerts.map((alert) => (
              (() => {
                const draftEntry = getTriageEntry(draftTriage, alert.alert_id)
                const savedEntry = getTriageEntry(savedTriage, alert.alert_id)
                const requiresDisposition =
                  draftEntry.status === 'Closed' && !draftEntry.disposition
                const isDirty =
                  draftEntry.status !== savedEntry.status ||
                  draftEntry.disposition !== savedEntry.disposition
                const saveState = saveStates[alert.alert_id] ?? 'idle'

                return (
                  <tr
                    key={alert.alert_id}
                    className={cn(
                      'cursor-pointer transition-colors duration-150 ease-out hover:bg-sidebar-active focus-within:bg-sidebar-active focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-[-2px]',
                      getRowBorderClass(alert)
                    )}
                    onClick={(event) => {
                      event.currentTarget.focus()
                      setActiveIncident(alert.alert_id)
                    }}
                    onKeyDown={(e) => {
                      if (
                        e.target instanceof HTMLInputElement ||
                        e.target instanceof HTMLSelectElement ||
                        e.target instanceof HTMLButtonElement
                      ) {
                        return
                      }

                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        setActiveIncident(alert.alert_id)
                      }
                    }}
                    tabIndex={0}
                    aria-selected={selectedIds.includes(alert.alert_id)}
                  >
                    <td className="p-3" onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.includes(alert.alert_id)}
                        onChange={() => toggleAlertSelection(alert.alert_id)}
                        className={CHECKBOX_CLASS}
                        aria-label={`Select alert ${alert.alert_id}`}
                      />
                    </td>
                    <td className="p-3 align-top" onClick={(e) => e.stopPropagation()}>
                      <div className="flex min-w-[180px] flex-col gap-2">
                        <select
                          value={draftEntry.status}
                          onChange={(event) =>
                            updateDraft(alert.alert_id, {
                              status: event.target.value as TriageStatus,
                              disposition:
                                event.target.value === 'Closed' ? draftEntry.disposition : null,
                            })
                          }
                          className={cn(
                            'min-h-9 rounded-sm border border-border-light bg-surface-light px-2 py-1 text-xs text-text-main',
                            FOCUS_RING_CLASS
                          )}
                          aria-label={`Triage status for alert ${alert.alert_id}`}
                        >
                          {TRIAGE_STATUS_OPTIONS.map((status) => (
                            <option key={status} value={status}>
                              {status}
                            </option>
                          ))}
                        </select>

                        {draftEntry.status === 'Closed' && (
                          <select
                            value={draftEntry.disposition ?? ''}
                            onChange={(event) =>
                              updateDraft(alert.alert_id, {
                                ...draftEntry,
                                disposition: event.target.value
                                  ? (event.target.value as TriageDisposition)
                                  : null,
                              })
                            }
                            className={cn(
                              'min-h-9 rounded-sm border border-border-light bg-surface-light px-2 py-1 text-xs text-text-main',
                              FOCUS_RING_CLASS
                            )}
                            aria-label={`Disposition for alert ${alert.alert_id}`}
                          >
                            <option value="">Select disposition</option>
                            {TRIAGE_DISPOSITION_OPTIONS.map((disposition) => (
                              <option key={disposition} value={disposition}>
                                {disposition}
                              </option>
                            ))}
                          </select>
                        )}

                        <div className="flex min-h-6 items-center gap-2">
                          <span
                            className={cn(
                              'text-[11px] transition-all duration-200',
                              saveState === 'saving' && isDirty && 'text-text-muted',
                              saveState === 'saved' && !isDirty && 'text-status-blocked',
                              saveState === 'idle' &&
                                isDirty &&
                                !requiresDisposition &&
                                'text-text-muted/80'
                            )}
                            role="status"
                            aria-live="polite"
                          >
                            {requiresDisposition
                              ? null
                              : saveState === 'saving'
                                ? 'Saving...'
                                : saveState === 'saved' && !isDirty
                                  ? 'Saved'
                                  : isDirty
                                    ? 'Autosaving'
                                    : 'Saved locally'}
                          </span>
                          {requiresDisposition && (
                            <span className="text-[11px] text-status-medium">
                              Disposition required to close
                            </span>
                          )}
                        </div>
                      </div>
                    </td>
                    <td className="p-3">
                      <SeverityBadge
                        severity={alert.confidence_level}
                        prediction={alert.prediction}
                      />
                    </td>
                    <td className="p-3 text-xs text-text-muted whitespace-nowrap">
                      {new Date(alert.timestamp).toLocaleString()}
                    </td>
                    <td className="p-3 text-xs font-mono text-text-main whitespace-nowrap">
                      {alert.source_ip ?? '—'}
                    </td>
                    <td className="p-3 text-xs text-text-muted tabular-nums">
                      {formatCrsScore(alert.crs_score)}
                    </td>
                    <td className="p-3 text-xs font-mono text-text-main max-w-[200px] truncate">
                      {alert.request_path ?? '—'}
                    </td>
                    <td className="p-3 text-xs font-mono text-text-muted whitespace-nowrap">
                      {formatRuleIds(alert.crs_rule_ids)}
                    </td>
                    <td className="p-3 text-xs text-text-main">
                      {alert.prediction}
                    </td>
                    <td className="p-3">
                      <ConfidenceBar confidence={alert.confidence} />
                    </td>
                    <td className="p-3">
                      <ActionLabel action={alert.action_taken} />
                    </td>
                  </tr>
                )
              })()
            ))
        : null}
    </AlertsTableShell>
  )
}

export default function AlertsTable() {
  return (
    <Suspense
      fallback={
        <AlertsTableShell
          selectedIds={[]}
          alerts={[]}
          selectAll={() => undefined}
          clearSelection={() => undefined}
        >
          <AlertsTableSkeletonRows />
        </AlertsTableShell>
      }
    >
      <AlertsTableContent />
    </Suspense>
  )
}
