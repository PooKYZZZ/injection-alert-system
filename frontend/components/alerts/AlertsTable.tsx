'use client'

import { useMemo, Suspense } from 'react'
import { usePathname, useRouter, useSearchParams, type ReadonlyURLSearchParams } from 'next/navigation'
import { useAlertsFromFilters } from '@/features/alerts/queries'
import type { Alert } from '@/features/alerts/types'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { ConfidenceBar } from '@/components/ui/ConfidenceBar'
import { ActionLabel } from '@/components/ui/ActionLabel'
import { TriageBadge } from '@/components/ui/TriageBadge'
import { normalizeAlertSearchParams } from '@/lib/searchParams'

interface AlertsTableProps {
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
  onAlertClick: (alert: Alert) => void
}

type SortColumn = 'timestamp' | 'confidence' | 'severity' | 'action'

function searchParamsToRecord(
  searchParams: ReadonlyURLSearchParams
): Record<string, string | string[]> {
  const normalized: Record<string, string | string[]> = {}

  for (const key of new Set(Array.from(searchParams.keys()))) {
    const values = searchParams.getAll(key)
    if (values.length === 0) continue
    normalized[key] = values.length === 1 ? values[0] : values
  }

  return normalized
}

const ALERT_TABLE_COLUMNS = [
  { key: 'triage', label: 'Triage', sortable: true },
  { key: 'severity', label: 'Severity', sortable: true },
  { key: 'timestamp', label: 'Timestamp', sortable: true },
  { key: 'source_ip', label: 'Source IP', sortable: false },
  { key: 'target_path', label: 'Target path', sortable: false },
  { key: 'crs_score', label: 'CRS score', sortable: true },
  { key: 'attack_type', label: 'Attack type', sortable: false },
  { key: 'confidence', label: 'Confidence', sortable: true },
  { key: 'action', label: 'Action', sortable: true },
] as const

function formatTimeOnly(timestamp: string): string {
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function AlertsTableSkeletonRows({ rowCount = 5 }: { rowCount?: number }) {
  return (
    <>
      {Array.from({ length: rowCount }).map((_, index) => (
        <tr key={index} aria-hidden="true" className="border-b border-[var(--color-text-ghost)]">
          <td className="p-3">
            <div className="h-4 w-4 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-5 w-16 rounded-full bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-5 w-12 rounded-full bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-16 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-24 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-20 truncate rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-14 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-20 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-20 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-5 w-14 rounded-full bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
        </tr>
      ))}
    </>
  )
}

function EmptyState({
  hasFilters,
  onClearFilters,
}: {
  hasFilters: boolean
  onClearFilters?: () => void
}) {
  return (
    <tr>
      <td colSpan={10} className="p-8 text-center">
        <p className="text-sm text-[var(--color-text-secondary)]">
          {hasFilters ? 'No alerts match the current filters.' : 'No alerts in the current window.'}
        </p>
        {hasFilters && onClearFilters && (
          <button
            type="button"
            onClick={onClearFilters}
            className="mt-3 rounded-md border border-[var(--color-text-ghost)] bg-[var(--color-text-ghost)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-text-ghost)]"
          >
            Clear filters
          </button>
        )}
      </td>
    </tr>
  )
}

function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <tr>
      <td colSpan={10} className="p-8 text-center">
        <p className="text-sm font-medium text-red-400">Unable to load alerts.</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-[var(--color-text-ghost)] bg-[var(--color-text-ghost)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-text-ghost)]"
        >
          Retry
        </button>
      </td>
    </tr>
  )
}

function SortHeader({
  column,
  currentSort,
  sortDir,
  onSort,
}: {
  column: (typeof ALERT_TABLE_COLUMNS)[number]
  currentSort: SortColumn | null
  sortDir: 'asc' | 'desc'
  onSort: (column: SortColumn) => void
}) {
  if (!column.sortable) {
    return (
      <th className="p-3 text-left text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
        {column.label}
      </th>
    )
  }

  const isActive = currentSort === column.key
  const isAsc = isActive && sortDir === 'asc'

  return (
    <th className="p-3 text-left">
      <button
        type="button"
        onClick={() => onSort(column.key as SortColumn)}
        className="flex items-center gap-1 text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)]"
      >
        {column.label}
        {isActive ? (
          <span className="text-blue-400">{isAsc ? '↑' : '↓'}</span>
        ) : (
          <span className="text-[var(--color-text-muted)]">↕</span>
        )}
      </button>
    </th>
  )
}

function AlertsTableContent({
  selectedIds,
  onSelectionChange,
  onAlertClick,
}: AlertsTableProps) {
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()

  const params = useMemo(
    () => normalizeAlertSearchParams(searchParamsToRecord(searchParams)),
    [searchParams]
  )

  // Use full AlertFilters for the alerts page (not down-converted to DashboardFilters)
  const { data, isPending, isError, refetch } = useAlertsFromFilters(params)
  const alerts = data?.items ?? []

  const currentSort = (params.sort_by as SortColumn | undefined) ?? null
  const currentDir = params.sort_dir ?? 'desc'

  const handleSort = (column: SortColumn) => {
    const newDir = currentSort === column && currentDir === 'desc' ? 'asc' : 'desc'

    const newParams = new URLSearchParams(searchParams.toString())
    newParams.set('sort_by', column)
    newParams.set('sort_dir', newDir)
    newParams.set('page', '1')

    router.replace(`${pathname}?${newParams.toString()}`, { scroll: false })
  }

  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      onSelectionChange(alerts.map((a) => a.alert_id))
    } else {
      onSelectionChange([])
    }
  }

  const handleSelectOne = (alertId: string) => {
    if (selectedIds.includes(alertId)) {
      onSelectionChange(selectedIds.filter((id) => id !== alertId))
    } else {
      onSelectionChange([...selectedIds, alertId])
    }
  }

  const handleClearFilters = () => {
    const paramsToKeep = ['page']
    const newParams = new URLSearchParams()
    for (const key of paramsToKeep) {
      const value = searchParams.get(key)
      if (value) newParams.set(key, value)
    }
    newParams.set('page', '1')
    router.replace(`${pathname}?${newParams.toString()}`, { scroll: false })
  }

  const hasFilters = Boolean(
    params.severity !== 'ALL' ||
    params.action !== undefined ||
    params.triage_status !== undefined ||
    params.window !== undefined ||
    (params.confidence_level && params.confidence_level.length > 0) ||
    (params.search && params.search.length > 0)
  )

  const selectedIdsSet = useMemo(() => new Set(selectedIds), [selectedIds])

  return (
    <div className="overflow-hidden rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-base)]">
      <div className="max-h-[500px] overflow-x-auto overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-[var(--color-bg-panel)]">
            <tr className="border-b border-[var(--color-text-ghost)]">
              <th className="w-10 p-3">
                <input
                  type="checkbox"
                  checked={alerts.length > 0 && selectedIds.length === alerts.length}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="h-4 w-4 cursor-pointer rounded border-[var(--color-text-ghost)] bg-[var(--color-bg-base)] text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                  aria-label="Select all alerts"
                />
              </th>
              {ALERT_TABLE_COLUMNS.map((column) => (
                <SortHeader
                  key={column.key}
                  column={column}
                  currentSort={currentSort}
                  sortDir={currentDir}
                  onSort={handleSort}
                />
              ))}
              <th className="w-12 p-3" />
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--color-text-ghost)]">
            {isPending ? (
              <AlertsTableSkeletonRows />
            ) : isError ? (
              <ErrorState onRetry={() => void refetch()} />
            ) : alerts.length === 0 ? (
              <EmptyState hasFilters={hasFilters} onClearFilters={handleClearFilters} />
            ) : (
              alerts.map((alert) => (
                <tr
                  key={alert.alert_id}
                  className="group cursor-pointer transition-colors duration-100 hover:bg-[var(--color-bg-panel)]"
                  onClick={() => onAlertClick(alert)}
                >
                  <td className="p-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIdsSet.has(alert.alert_id)}
                      onChange={() => handleSelectOne(alert.alert_id)}
                      className="h-4 w-4 cursor-pointer rounded border-[var(--color-text-ghost)] bg-[var(--color-bg-base)] text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
                      aria-label={`Select alert ${alert.alert_id}`}
                    />
                  </td>
                  <td className="p-3">
                    <TriageBadge triage_status={alert.triage_status ?? null} />
                  </td>
                  <td className="p-3">
                    <SeverityBadge
                      severity={alert.confidence_level}
                      prediction={alert.prediction}
                    />
                  </td>
                  <td className="whitespace-nowrap p-3 font-mono text-[10px] text-[var(--color-text-secondary)]">
                    {formatTimeOnly(alert.timestamp)}
                  </td>
                  <td className="whitespace-nowrap p-3 font-mono text-xs text-blue-400">
                    {alert.source_ip ?? '—'}
                  </td>
                  <td
                    className="w-[200px] max-w-[200px] overflow-hidden truncate whitespace-nowrap p-3 font-mono text-xs text-[var(--color-text-primary)]"
                    title={alert.request_path ?? '—'}
                  >
                    {alert.request_path ?? '—'}
                  </td>
                  <td className="whitespace-nowrap p-3 font-mono text-xs tabular-nums text-[var(--color-text-secondary)]">
                    {alert.crs_score !== null && alert.crs_score !== undefined
                      ? alert.crs_score.toFixed(2)
                      : '—'}
                  </td>
                  <td className="p-3 text-xs text-[var(--color-text-primary)]">{alert.prediction}</td>
                  <td className="p-3">
                    <ConfidenceBar
                      confidence={alert.confidence}
                      prediction={alert.prediction}
                    />
                  </td>
                  <td className="p-3">
                    <ActionLabel action={alert.action_taken} />
                  </td>
                  <td className="p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      type="button"
                      className="flex h-6 w-6 items-center justify-center rounded text-[var(--color-text-secondary)] hover:bg-[var(--color-text-ghost)] hover:text-[var(--color-text-primary)]"
                      aria-label={`View details for alert ${alert.alert_id}`}
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                      >
                        <polyline points="9 18 15 12 9 6" />
                      </svg>
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination footer */}
      <div className="flex items-center justify-between border-t border-[var(--color-text-ghost)] px-4 py-3">
        <p className="text-xs text-[var(--color-text-secondary)]">
          {data ? (
            <>
              Showing {(params.page - 1) * params.pageSize + 1}–
              {Math.min(params.page * params.pageSize, data.total)} of {data.total} alerts
            </>
          ) : (
            'Loading...'
          )}
        </p>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={() => {
              const newPage = Math.max(1, (params.page ?? 1) - 1)
              const newParams = new URLSearchParams(searchParams.toString())
              newParams.set('page', String(newPage))
              router.replace(`${pathname}?${newParams.toString()}`, { scroll: false })
            }}
            disabled={params.page <= 1}
            className="rounded border border-[var(--color-text-ghost)] bg-[var(--color-text-ghost)] px-3 py-1 text-xs font-medium text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-text-ghost)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            ← Prev
          </button>
          <span className="text-xs text-[var(--color-text-secondary)]">
            Page {params.page}
            {data ? ` of ${Math.ceil(data.total / params.pageSize)}` : ''}
          </span>
          <button
            type="button"
            onClick={() => {
              const newPage = (params.page ?? 1) + 1
              const newParams = new URLSearchParams(searchParams.toString())
              newParams.set('page', String(newPage))
              router.replace(`${pathname}?${newParams.toString()}`, { scroll: false })
            }}
            disabled={data ? params.page * params.pageSize >= data.total : true}
            className="rounded border border-[var(--color-text-ghost)] bg-[var(--color-text-ghost)] px-3 py-1 text-xs font-medium text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-text-ghost)] disabled:cursor-not-allowed disabled:opacity-50"
          >
            Next →
          </button>
        </div>
      </div>
    </div>
  )
}

export function AlertsTable({ selectedIds, onSelectionChange, onAlertClick }: AlertsTableProps) {
  return (
    <Suspense
      fallback={
        <div className="overflow-hidden rounded-lg border border-[var(--color-text-ghost)] bg-[var(--color-bg-base)]">
          <div className="max-h-[500px] overflow-x-auto overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10 bg-[var(--color-bg-panel)]">
                <tr className="border-b border-[var(--color-text-ghost)]">
                  <th className="w-10 p-3">
                    <div className="h-4 w-4 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
                  </th>
                  {ALERT_TABLE_COLUMNS.map((column) => (
                    <th
                      key={column.key}
                      className="p-3 text-left text-[11px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]"
                    >
                      {column.label}
                    </th>
                  ))}
                  <th className="w-12 p-3" />
                </tr>
              </thead>
              <tbody>
                <AlertsTableSkeletonRows />
              </tbody>
            </table>
          </div>
        </div>
      }
    >
      <AlertsTableContent
        selectedIds={selectedIds}
        onSelectionChange={onSelectionChange}
        onAlertClick={onAlertClick}
      />
    </Suspense>
  )
}
