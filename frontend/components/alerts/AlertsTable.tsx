'use client'

import { useMemo, useSyncExternalStore, Suspense } from 'react'
import { usePathname, useRouter, useSearchParams, type ReadonlyURLSearchParams } from 'next/navigation'
import { useAlertsFromFilters } from '@/features/alerts/queries'
import type { Alert } from '@/features/alerts/types'
import { ActionLabel } from '@/components/ui/ActionLabel'
import { TriageBadge } from '@/components/ui/TriageBadge'
import { getCurrentSearchParams, normalizeAlertSearchParams } from '@/lib/searchParams'
import { formatAlertDateTime, formatCompactConfidencePercent, formatConfidenceTierLabel, formatRelativeTime } from '@/lib/date-time'
import { getConfidenceColors } from '@/components/ui/ConfidenceBar'
import { PERMISSIONS, roleHasPermission } from '@/lib/auth/roles'

interface AlertsTableProps {
  role?: unknown
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
  onAlertClick: (alert: Alert) => void
  activeAlertId?: string
}

type SortColumn = 'timestamp' | 'confidence' | 'severity' | 'confidence_tier' | 'action'

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
  { key: 'triage', label: 'Triage', sortable: false },
  { key: 'timestamp', label: 'Timestamp', sortable: true },
  { key: 'source_ip', label: 'Source IP', sortable: false },
  { key: 'target_path', label: 'Request', sortable: false },
  { key: 'attack_type', label: 'Prediction', sortable: false },
  { key: 'confidence', label: 'Confidence', sortable: true },
  { key: 'action', label: 'Action Taken', sortable: true },
  { key: 'crs_score', label: 'CRS Score', sortable: false },
] as const

function formatCrsScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  return Number(score.toFixed(1)).toString()
}

function formatRequestHeadline(alert: Alert): string {
  const path = alert.request_path?.trim()
  if (!path) return '—'
  const method = alert.request_method?.trim()
  return method ? `${method.toUpperCase()} ${path}` : path
}

function formatPayloadEvidence(snippet: string | null | undefined): string {
  const normalized = snippet?.trim()
  return normalized && normalized.length > 0 ? normalized : 'No payload snippet'
}

function AlertsTableSkeletonRows({ rowCount = 5 }: { rowCount?: number }) {
  return (
    <>
      {Array.from({ length: rowCount }).map((_, index) => (
        <tr key={index} aria-hidden="true" className="border-b border-surface-border">
          <td className="p-3">
            <div className="h-4 w-4 rounded bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-5 w-16 rounded-full bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-5 w-12 rounded-full bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-16 rounded bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-24 rounded bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-20 truncate rounded bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-14 rounded bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-20 rounded bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-4 w-20 rounded bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
          </td>
          <td className="p-3">
            <div className="h-5 w-14 rounded-full bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
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
            className="mt-3 rounded-md border border-surface-border bg-surface-inset px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)] transition-colors hover:bg-surface-inset"
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
          className="mt-3 rounded-md border border-surface-border bg-surface-inset px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)] transition-colors hover:bg-surface-inset"
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
      <th scope="col" className="p-3 text-left text-xs font-semibold text-[var(--color-text-secondary)]">
        {column.label}
      </th>
    )
  }

  const isActive = currentSort === column.key
  const isAsc = isActive && sortDir === 'asc'

  return (
    <th scope="col" className="p-3 text-left">
      <button
        type="button"
        onClick={() => onSort(column.key as SortColumn)}
        aria-label={`${column.label}, ${isActive ? (isAsc ? 'ascending' : 'descending') : 'not sorted'}`}
        className="flex items-center gap-1 text-xs font-semibold text-[var(--color-text-secondary)] transition-colors hover:text-[var(--color-text-primary)]"
      >
        {column.label}
        {isActive ? (
          <span className="text-action-accent">{isAsc ? '↑' : '↓'}</span>
        ) : (
          <span className="text-[var(--color-text-muted)]">↕</span>
        )}
      </button>
    </th>
  )
}

function AlertsTableContent({
  role,
  selectedIds,
  onSelectionChange,
  onAlertClick,
  activeAlertId,
}: AlertsTableProps) {
  const canTriage = roleHasPermission(role, PERMISSIONS.ALERTS_TRIAGE)
  const isHydrated = useSyncExternalStore(
    () => () => {},
    () => true,
    () => false
  )
  const pathname = usePathname()
  const router = useRouter()
  const searchParams = useSearchParams()

  const params = useMemo(
    () => normalizeAlertSearchParams(searchParamsToRecord(searchParams)),
    [searchParams]
  )

  // Use full AlertFilters for the alerts page (not down-converted to DashboardFilters)
  const { data, isPending, isFetching, isError, refetch } = useAlertsFromFilters(params)
  const alerts = data?.items ?? []

  const currentSort = (params.sort_by as SortColumn | undefined) ?? null
  const currentDir = params.sort_dir ?? 'desc'
  const currentConfidenceTierFilter = params.confidence_tier ?? params.severity ?? 'ALL'

  const handleSort = (column: SortColumn) => {
    const newDir = currentSort === column && currentDir === 'desc' ? 'asc' : 'desc'

    const newParams = getCurrentSearchParams(searchParams)
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

  const handleRowClick = (alert: Alert) => {
    onAlertClick(alert)
  }

  const handleClearFilters = () => {
    const paramsToKeep = ['page']
    const currentParams = getCurrentSearchParams(searchParams)
    const newParams = new URLSearchParams()
    for (const key of paramsToKeep) {
      const value = currentParams.get(key)
      if (value) newParams.set(key, value)
    }
    newParams.set('page', '1')
    router.replace(`${pathname}?${newParams.toString()}`, { scroll: false })
  }

  const hasFilters = Boolean(
    currentConfidenceTierFilter !== 'ALL' ||
    params.action !== undefined ||
    params.triage_status !== undefined ||
    params.prediction !== undefined ||
    params.window !== undefined ||
    (params.confidence_level && params.confidence_level.length > 0) ||
    (params.search && params.search.length > 0)
  )

  const selectedIdsSet = useMemo(() => new Set(selectedIds), [selectedIds])
  const canGoPrev = params.page > 1
  const canGoNext = !!data && params.page * params.pageSize < data.total

  return (
    <div className="overflow-hidden rounded-lg border border-surface-border bg-surface-card">
      <div
        role="region"
        aria-label="Scrollable security alerts table"
        className="max-h-[500px] overflow-x-auto overflow-y-auto"
      >
        <table className="w-full text-sm">
          <caption className="sr-only">Security alerts matching the current filters</caption>
          <thead className="sticky top-0 z-10 bg-surface-panel">
            <tr className="border-b border-surface-border">
              <th scope="col" className="w-10 p-3">
                {canTriage && (
                  <input
                    type="checkbox"
                    checked={alerts.length > 0 && selectedIds.length === alerts.length}
                    onChange={(e) => handleSelectAll(e.target.checked)}
                    className="h-4 w-4 cursor-pointer rounded border-surface-border bg-surface-card text-action-accent focus:ring-2 focus:ring-action-border focus:ring-offset-0"
                    style={{ accentColor: 'var(--color-action-accent)' }}
                    aria-label="Select all alerts"
                  />
                )}
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
              <th scope="col" className="w-12 p-3" />
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
                  className={
                    `group cursor-pointer transition-colors duration-100 hover:bg-surface-inset` +
                    (alert.alert_id === (typeof activeAlertId !== 'undefined' ? activeAlertId : undefined)
                      ? ' bg-surface-inset ring-1 ring-action-border'
                      : '')
                  }
                  onClick={() => handleRowClick(alert)}
                >
                  <td className="p-3" onClick={(e) => e.stopPropagation()}>
                    {canTriage && (
                      <input
                        type="checkbox"
                        checked={selectedIdsSet.has(alert.alert_id)}
                        onChange={() => handleSelectOne(alert.alert_id)}
                        className="h-4 w-4 cursor-pointer rounded border-surface-border bg-surface-card text-action-accent focus:ring-2 focus:ring-action-border focus:ring-offset-0"
                        style={{ accentColor: 'var(--color-action-accent)' }}
                        aria-label={`Select alert ${alert.alert_id}`}
                      />
                    )}
                  </td>
                  <td className="p-3">
                    <TriageBadge triage_status={alert.triage_status ?? null} />
                  </td>
                  <td className="whitespace-nowrap p-3 font-mono text-[10px] text-[var(--color-text-primary)]">
                    <time dateTime={alert.timestamp}>{formatAlertDateTime(alert.timestamp)}</time>
                    <div className="text-xs text-[var(--color-text-muted)]">
                      {formatRelativeTime(alert.timestamp)}
                    </div>
                  </td>
                  <td className="whitespace-nowrap p-3 font-mono text-xs text-[var(--color-accent-analytic)]">
                    {alert.source_ip ?? '—'}
                  </td>
                  <td className="w-[260px] max-w-[260px] p-3 align-top">
                    <div className="flex max-w-[260px] flex-col gap-0.5">
                      <span
                        className="truncate font-mono text-[11px] text-[var(--color-accent-analytic)]"
                        title={formatRequestHeadline(alert)}
                      >
                        {formatRequestHeadline(alert)}
                      </span>
                      <span
                        className="truncate text-[10px] text-[var(--color-text-soft)]"
                        title={formatPayloadEvidence(alert.payload_snippet)}
                      >
                        {formatPayloadEvidence(alert.payload_snippet)}
                      </span>
                    </div>
                  </td>
                  <td className="p-3 text-xs text-[var(--color-text-primary)]">{alert.prediction}</td>
                  <td className="p-3">
                    <div className="flex flex-col gap-0.5">
                      <span className="font-mono text-xs text-text-primary">
                        {formatCompactConfidencePercent(alert.confidence)}
                      </span>
                      <span className={`text-xs ${getConfidenceColors(alert.confidence, alert.confidence_level).text}`}>
                        {formatConfidenceTierLabel(alert.confidence_level)}
                      </span>
                    </div>
                  </td>
                  <td className="p-3">
                    <ActionLabel action={alert.action_taken} bordered={false} />
                  </td>
                  <td className="p-3 font-mono text-xs text-[var(--color-text-secondary)]">
                    {formatCrsScore(alert.crs_score)}
                  </td>
                  <td className="p-3">
                    <button
                      type="button"
                      className="flex h-6 w-6 items-center justify-center rounded text-[var(--color-text-secondary)] opacity-0 transition-opacity group-hover:opacity-100 focus-visible:opacity-100 hover:bg-surface-border hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-border"
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
      {!isHydrated ? (
        <div className="flex items-center justify-between border-t border-surface-border px-4 py-3">
          <p className="text-xs text-[var(--color-text-secondary)]">Loading...</p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled
              className="rounded border border-surface-border bg-surface-inset px-3 py-1 text-xs font-medium text-[var(--color-text-primary)] transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              ← Prev
            </button>
            <span className="text-xs text-[var(--color-text-secondary)]">Page 1</span>
            <button
              type="button"
              disabled
              className="rounded border border-surface-border bg-surface-inset px-3 py-1 text-xs font-medium text-[var(--color-text-primary)] transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next →
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between border-t border-surface-border px-4 py-3">
          <p className="text-xs text-[var(--color-text-secondary)]">
            {data?.total === 0 ? (
              'Showing 0 alerts'
            ) : data ? (
              <>
                Showing {(params.page - 1) * params.pageSize + 1}–
                {Math.min(params.page * params.pageSize, data.total)} of {data.total} alerts
              </>
            ) : (
              'Loading...'
            )}
          </p>
          <div className="flex items-center gap-2">
            {isFetching && !isPending ? (
              <span role="status" aria-live="polite" className="text-[10px] text-[var(--color-text-muted)]">
                Updating…
              </span>
            ) : null}
            <button
              type="button"
              onClick={() => {
                const newPage = Math.max(1, (params.page ?? 1) - 1)
                const newParams = getCurrentSearchParams(searchParams)
                newParams.set('page', String(newPage))
                router.replace(`${pathname}?${newParams.toString()}`, { scroll: false })
              }}
              disabled={!canGoPrev}
              className="rounded border border-surface-border bg-surface-inset px-3 py-1 text-xs font-medium text-[var(--color-text-primary)] transition-colors hover:bg-surface-inset disabled:cursor-not-allowed disabled:opacity-50"
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
                const newParams = getCurrentSearchParams(searchParams)
                newParams.set('page', String(newPage))
                router.replace(`${pathname}?${newParams.toString()}`, { scroll: false })
              }}
              disabled={!canGoNext}
              className="rounded border border-surface-border bg-surface-inset px-3 py-1 text-xs font-medium text-[var(--color-text-primary)] transition-colors hover:bg-surface-inset disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export function AlertsTable({ role, selectedIds, onSelectionChange, onAlertClick, activeAlertId }: AlertsTableProps) {
  return (
    <Suspense
      fallback={
        <div className="overflow-hidden rounded-lg border border-surface-border bg-surface-card">
          <div className="max-h-[500px] overflow-x-auto overflow-y-auto">
            <table className="w-full text-sm">
              <caption className="sr-only">Security alerts matching the current filters</caption>
              <thead className="sticky top-0 z-10 bg-surface-panel">
                <tr className="border-b border-surface-border">
                  <th scope="col" className="w-10 p-3">
                    <div className="h-4 w-4 rounded bg-surface-inset [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
                  </th>
                  {ALERT_TABLE_COLUMNS.map((column) => (
                    <th
                      key={column.key}
                      scope="col"
                      className="p-3 text-left text-xs font-semibold text-[var(--color-text-secondary)]"
                    >
                      {column.label}
                    </th>
                  ))}
                  <th scope="col" className="w-12 p-3" />
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
        role={role}
        selectedIds={selectedIds}
        onSelectionChange={onSelectionChange}
        onAlertClick={onAlertClick}
        activeAlertId={activeAlertId}
      />
    </Suspense>
  )
}
