'use client'

import type { UseQueryResult } from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState, Suspense } from 'react'
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

interface TriageEntry {
  status: TriageStatus
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

type AlertColumnKey =
  | 'triageStatus'
  | 'confidenceLevel'
  | 'timestamp'
  | 'sourceIp'
  | 'crsScore'
  | 'targetPath'
  | 'ruleIds'
  | 'attackType'
  | 'mlConfidence'
  | 'action'

interface AlertTableColumn {
  key: AlertColumnKey
  header: string
}

const ALERT_TABLE_COLUMNS: readonly AlertTableColumn[] = [
  { key: 'triageStatus', header: 'Triage Status' },
  { key: 'confidenceLevel', header: 'Threat Severity' },
  { key: 'timestamp', header: 'Timestamp ▼' },
  { key: 'sourceIp', header: 'Source IP' },
  { key: 'crsScore', header: 'CRS Score' },
  { key: 'targetPath', header: 'Target Path' },
  { key: 'ruleIds', header: 'Rule IDs' },
  { key: 'attackType', header: 'Attack Type' },
  { key: 'mlConfidence', header: 'ML Confidence' },
  { key: 'action', header: 'Action' },
] as const

const FOCUS_RING_CLASS =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-panel'
const CHECKBOX_CLASS = cn(
  'h-4 w-4 cursor-pointer rounded border-border-light bg-bg-panel text-primary',
  FOCUS_RING_CLASS
)

function formatRuleIds(ruleIds: string[] | null | undefined): string {
  if (!ruleIds || ruleIds.length === 0) return '—'
  if (ruleIds.length === 1) return ruleIds[0]
  return `${ruleIds[0]} +${ruleIds.length - 1}`
}

function formatTimeOnly(timestamp: string): string {
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function sanitizeTriageRecord(value: unknown): Record<string, TriageEntry> {
  if (!value || typeof value !== 'object') return {}

  const sanitized: Record<string, TriageEntry> = {}
  for (const [alertId, entry] of Object.entries(value as Record<string, unknown>)) {
    const status = (entry as { status?: unknown })?.status
    if (status === 'New' || status === 'In Progress' || status === 'Closed') {
      sanitized[alertId] = { status }
    }
  }
  return sanitized
}

function getTriageClasses(status: TriageStatus, isSaving: boolean): string {
  const base =
    'inline-flex min-h-6 min-w-12 items-center justify-center rounded-full border px-2 py-[2px] text-[10px] font-medium transition-colors'

  if (isSaving) {
    return `${base} border-accent-blue bg-accent-blue-bg text-accent-blue`
  }

  switch (status) {
    case 'In Progress':
      return `${base} border-accent-blue bg-accent-blue-bg text-accent-blue`
    case 'Closed':
      return `${base} border-severity-safe-border bg-severity-safe-bg text-severity-safe-text`
    default:
      return `${base} border-severity-benign-border bg-bg-elevated text-text-muted`
  }
}

function nextTriageStatus(current: TriageStatus): TriageStatus {
  const currentIndex = TRIAGE_STATUS_OPTIONS.indexOf(current)
  return TRIAGE_STATUS_OPTIONS[(currentIndex + 1) % TRIAGE_STATUS_OPTIONS.length]
}

function AlertsTableSkeletonRows({
  rowCount = 3,
  columnCount,
}: {
  rowCount?: number
  columnCount: number
}) {
  return (
    <>
      {Array.from({ length: rowCount }).map((_, index) => (
        <tr key={index} aria-hidden="true" className="border-b border-border-light">
          <td className="p-3">
            <div className="h-[10px] w-[10px] rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          {Array.from({ length: columnCount - 1 }).map((__, cellIndex) => (
            <td key={cellIndex} className="p-3">
              <div className="h-[10px] rounded-sm bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
            </td>
          ))}
        </tr>
      ))}
    </>
  )
}

function AlertsTableStateRow({
  title,
  action,
  columnCount,
}: {
  title: string
  action?: React.ReactNode
  columnCount: number
}) {
  return (
    <tr>
      <td colSpan={columnCount} className="p-8">
        <div className="flex flex-col items-center justify-center gap-3 text-center">
          <p className="text-sm font-medium text-text-primary">{title}</p>
          {action ? <div>{action}</div> : null}
        </div>
      </td>
    </tr>
  )
}

function AlertsTableShell({
  selectedIds,
  alerts,
  selectAll,
  clearSelection,
  children,
  columns,
}: {
  selectedIds: string[]
  alerts: Alert[]
  selectAll: (ids: string[]) => void
  clearSelection: () => void
  children: React.ReactNode
  columns: AlertTableColumn[]
}) {
  return (
    <div className="overflow-hidden rounded-lg border border-border-light bg-bg-panel shadow-subtle">
      <div className="flex items-start justify-between gap-4 border-b border-border-light p-4">
        <h2 className="text-[9px] font-semibold uppercase tracking-[0.09em] text-text-muted">
          Alerts
        </h2>
        {selectedIds.length > 0 ? <BulkActionBar /> : null}
      </div>

      <div className="max-h-[420px] overflow-x-auto overflow-y-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-bg-inset">
              <th className="w-10 p-3">
                <input
                  type="checkbox"
                  checked={alerts.length > 0 && selectedIds.length === alerts.length}
                  onChange={(event) => {
                    if (event.target.checked) {
                      selectAll(alerts.map((alert) => alert.alert_id))
                    } else {
                      clearSelection()
                    }
                  }}
                  className={CHECKBOX_CLASS}
                  aria-label="Select all alerts"
                />
              </th>
              {columns.map((column) => (
                <th
                  key={column.key}
                  className={cn(
                    'p-3 text-left text-label font-semibold uppercase tracking-[0.08em] text-text-muted',
                    column.key === 'crsScore' && 'w-[70px]',
                    column.key === 'targetPath' && 'w-[200px]'
                  )}
                >
                  {column.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-border-light">{children}</tbody>
          <tfoot>
            <tr>
              <td
                colSpan={columns.length + 1}
                className="border-t border-border-light px-3 py-2 text-[10px] italic text-text-muted"
              >
                Showing {alerts.length} loaded records · Triage status stored locally in this browser.
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  )
}

function AlertsTableContent() {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()
  const [hydrated, setHydrated] = useState(false)
  const [triageEntries, setTriageEntries] = useState<Record<string, TriageEntry>>({})
  const [savingIds, setSavingIds] = useState<Record<string, boolean>>({})
  const savingTimeoutsRef = useRef<Record<string, ReturnType<typeof setTimeout>>>({})

  const filters: DashboardFilters = {
    severity: (searchParams?.get('severity') ?? 'ALL') as SeverityFilter,
    timeRange: (searchParams?.get('timeRange') ?? '24h') as TimeRange,
    search: searchParams?.get('search') ?? '',
  }

  const { toggleAlertSelection, selectAll, clearSelection, setActiveIncident } = useDashboardStore()
  const selectedIds = useDashboardStore(
    useShallow((state: DashboardStoreState) => [...state.selectedAlertIds])
  )

  useEffect(() => {
    if (selectedIds.length > 0) clearSelection()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.severity, filters.timeRange, filters.search])

  const alertsQuery: UseQueryResult<PaginatedAlerts, Error> = useAlerts(filters)
  const { data, isPending, isError } = alertsQuery
  const alerts = useMemo(
    () =>
      [...(data?.items ?? [])].sort(
        (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
      ),
    [data?.items]
  )
  const retryAlerts = () => {
    void alertsQuery.refetch()
  }
  const hasFilter =
    filters.search.trim().length > 0 ||
    filters.severity !== DEFAULT_FILTERS.severity ||
    filters.timeRange !== DEFAULT_FILTERS.timeRange

  useEffect(() => {
    setHydrated(true)
  }, [])

  useEffect(() => {
    if (typeof window === 'undefined') return

    try {
      const storedValue = window.localStorage.getItem(TRIAGE_STORAGE_KEY)
      setTriageEntries(sanitizeTriageRecord(storedValue ? JSON.parse(storedValue) : {}))
    } catch {
      setTriageEntries({})
    }
  }, [])

  useEffect(() => {
    const timeouts = savingTimeoutsRef.current
    return () => {
      Object.values(timeouts).forEach((timeoutId) => clearTimeout(timeoutId))
    }
  }, [])

  const hasRuleIdsColumn = alerts.some((alert) => (alert.crs_rule_ids?.length ?? 0) > 0)
  const visibleColumns = ALERT_TABLE_COLUMNS.filter(
    (column) => column.key !== 'ruleIds' || hasRuleIdsColumn
  )
  const columnCount = visibleColumns.length + 1

  const updateTriage = (alertId: string) => {
    const currentStatus = triageEntries[alertId]?.status ?? 'New'
    const nextEntries = {
      ...triageEntries,
      [alertId]: { status: nextTriageStatus(currentStatus) },
    }
    setTriageEntries(nextEntries)

    if (typeof window !== 'undefined') {
      try {
        window.localStorage.setItem(TRIAGE_STORAGE_KEY, JSON.stringify(nextEntries))
      } catch {
        // Keep the local interaction usable if storage is unavailable.
      }
    }

    if (savingTimeoutsRef.current[alertId]) {
      clearTimeout(savingTimeoutsRef.current[alertId])
    }

    setSavingIds((current) => ({ ...current, [alertId]: true }))
    savingTimeoutsRef.current[alertId] = setTimeout(() => {
      setSavingIds((current) => ({ ...current, [alertId]: false }))
      delete savingTimeoutsRef.current[alertId]
    }, 200)
  }

  if (!hydrated) {
    return (
      <AlertsTableShell
        selectedIds={selectedIds}
        alerts={[]}
        selectAll={selectAll}
        clearSelection={clearSelection}
        columns={ALERT_TABLE_COLUMNS.filter((column) => column.key !== 'ruleIds')}
      >
        <AlertsTableSkeletonRows
          columnCount={ALERT_TABLE_COLUMNS.filter((column) => column.key !== 'ruleIds').length + 1}
        />
      </AlertsTableShell>
    )
  }

  return (
    <AlertsTableShell
      selectedIds={selectedIds}
      alerts={alerts}
      selectAll={selectAll}
      clearSelection={clearSelection}
      columns={visibleColumns}
    >
      {isPending ? <AlertsTableSkeletonRows columnCount={columnCount} /> : null}

      {!isPending && isError ? (
        <AlertsTableStateRow
          title="Unable to load alerts."
          columnCount={columnCount}
          action={
            <button
              type="button"
              onClick={retryAlerts}
              className={cn(
                'rounded-md border border-border-light px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:bg-bg-elevated',
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
          columnCount={columnCount}
          action={
            <button
              type="button"
              onClick={retryAlerts}
              className={cn(
                'rounded-md border border-border-light px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:bg-bg-elevated',
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
          title={hasFilter ? 'No alerts match the current filters.' : 'No alerts in the current window.'}
          columnCount={columnCount}
          action={
            hasFilter && pathname ? (
              <button
                type="button"
                onClick={() => void router.replace(pathname)}
                className={cn(
                  'rounded-md border border-border-light px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:bg-bg-elevated',
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
        ? alerts.map((alert) => {
            const triageStatus = triageEntries[alert.alert_id]?.status ?? 'New'
            const isSaving = savingIds[alert.alert_id] ?? false

            return (
              <tr
                key={alert.alert_id}
                className="cursor-pointer transition-[background-color] duration-100 ease-in hover:bg-bg-elevated focus-within:bg-bg-elevated focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-[-2px]"
                onClick={(event) => {
                  event.currentTarget.focus()
                  setActiveIncident(alert.alert_id)
                }}
                onKeyDown={(event) => {
                  if (
                    event.target instanceof HTMLInputElement ||
                    event.target instanceof HTMLSelectElement ||
                    event.target instanceof HTMLButtonElement
                  ) {
                    return
                  }

                  if (event.key === 'Enter' || event.key === ' ') {
                    event.preventDefault()
                    setActiveIncident(alert.alert_id)
                  }
                }}
                tabIndex={0}
                aria-selected={selectedIds.includes(alert.alert_id)}
              >
                <td className="p-3" onClick={(event) => event.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={selectedIds.includes(alert.alert_id)}
                    onChange={() => toggleAlertSelection(alert.alert_id)}
                    className={CHECKBOX_CLASS}
                    aria-label={`Select alert ${alert.alert_id}`}
                  />
                </td>

                {visibleColumns.map((column) => {
                  switch (column.key) {
                    case 'triageStatus':
                      return (
                        <td key={column.key} className="p-3" onClick={(event) => event.stopPropagation()}>
                          <button
                            type="button"
                            onClick={() => updateTriage(alert.alert_id)}
                            className={cn(getTriageClasses(triageStatus, isSaving), FOCUS_RING_CLASS)}
                            aria-label={`Triage status for alert ${alert.alert_id}: ${triageStatus}`}
                          >
                            {triageStatus}
                          </button>
                        </td>
                      )
                    case 'confidenceLevel':
                      return (
                        <td key={column.key} className="p-3">
                          <SeverityBadge
                            severity={alert.confidence_level}
                            prediction={alert.prediction}
                          />
                        </td>
                      )
                    case 'timestamp':
                      return (
                        <td
                          key={column.key}
                          className="whitespace-nowrap p-3 text-[10px] text-text-muted"
                          title={alert.timestamp}
                        >
                          {formatTimeOnly(alert.timestamp)}
                        </td>
                      )
                    case 'sourceIp':
                      return (
                        <td
                          key={column.key}
                          className="whitespace-nowrap p-3 font-mono text-xs text-text-secondary"
                        >
                          {alert.source_ip ?? '—'}
                        </td>
                      )
                    case 'crsScore':
                      return (
                        <td key={column.key} className="w-[70px] p-3 text-xs tabular-nums text-text-secondary">
                          {alert.crs_score === null || alert.crs_score === undefined
                            ? '—'
                            : Number(alert.crs_score ?? 0).toFixed(2)}
                        </td>
                      )
                    case 'targetPath':
                      return (
                        <td
                          key={column.key}
                          title={alert.request_path ?? ''}
                          className="w-[200px] max-w-[200px] overflow-hidden truncate whitespace-nowrap p-3 font-mono text-xs text-text-primary"
                        >
                          {alert.request_path ?? '—'}
                        </td>
                      )
                    case 'ruleIds':
                      return (
                        <td
                          key={column.key}
                          className="whitespace-nowrap p-3 font-mono text-xs text-text-secondary"
                        >
                          {formatRuleIds(alert.crs_rule_ids)}
                        </td>
                      )
                    case 'attackType':
                      return (
                        <td key={column.key} className="p-3 text-xs text-text-primary">
                          {alert.prediction}
                        </td>
                      )
                    case 'mlConfidence':
                      return (
                        <td key={column.key} className="p-3">
                          <ConfidenceBar
                            confidence={alert.confidence}
                            prediction={alert.prediction}
                          />
                        </td>
                      )
                    case 'action':
                      return (
                        <td key={column.key} className="p-3">
                          <ActionLabel action={alert.action_taken} />
                        </td>
                      )
                  }
                })}
              </tr>
            )
          })
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
          columns={ALERT_TABLE_COLUMNS.filter((column) => column.key !== 'ruleIds')}
        >
          <AlertsTableSkeletonRows
            columnCount={ALERT_TABLE_COLUMNS.filter((column) => column.key !== 'ruleIds').length + 1}
          />
        </AlertsTableShell>
      }
    >
      <AlertsTableContent />
    </Suspense>
  )
}
