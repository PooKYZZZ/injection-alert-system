'use client'

import { useMemo, useSyncExternalStore, Suspense } from 'react'
import { usePathname, useRouter, useSearchParams, type ReadonlyURLSearchParams } from 'next/navigation'
import { useAlertsFromFilters, useTriageMutation } from '@/features/alerts/queries'
import type { Alert } from '@/features/alerts/types'
import { ActionLabel } from '@/components/ui/ActionLabel'
import { TriageBadge } from '@/components/ui/TriageBadge'
import { normalizeAlertSearchParams } from '@/lib/searchParams'

interface AlertsTableProps {
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
  onAlertClick: (alert: Alert) => void
  activeAlertId?: string
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
  { key: 'timestamp', label: 'Timestamp', sortable: true },
  { key: 'source_ip', label: 'Source IP', sortable: false },
  { key: 'target_path', label: 'Request', sortable: false },
  { key: 'attack_type', label: 'Prediction', sortable: false },
  { key: 'confidence', label: 'Confidence', sortable: true },
  { key: 'action', label: 'Action Taken', sortable: true },
  { key: 'crs_score', label: 'CRS Score', sortable: false },
] as const

function formatTimeOnly(timestamp: string): string {
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return '—'
  return parsed.toLocaleTimeString([], {
    hour: 'numeric',
    minute: '2-digit',
  })
}

function formatRelativeTime(timestamp: string): string {
  const now = Date.now()
  const then = new Date(timestamp).getTime()
  if (Number.isNaN(then)) return '—'
  const diff = Math.max(0, Math.floor((now - then) / 1000)) // seconds

  const minutes = Math.floor(diff / 60)
  if (minutes < 1) return `${Math.max(0, diff)}s ago`
  if (minutes < 60) return `${minutes}min${minutes === 1 ? '' : 's'} ago`

  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}hr${hours === 1 ? '' : 's'} ago`

  const days = Math.floor(hours / 24)
  if (days < 30) return `${days}day${days === 1 ? '' : 's'} ago`

  const months = Math.floor(days / 30)
  if (months < 12) return `${months}month${months === 1 ? '' : 's'} ago`

  const years = Math.floor(days / 365)
  return `${years}year${years === 1 ? '' : 's'} ago`
}

function formatCrsScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  return score.toFixed(2)
}

function getConfidenceTextColor(confidence: number): string {
  const value = Math.round(confidence * 100)
  if (value >= 80) return 'text-severity-high-text'
  if (value >= 50) return 'text-severity-blocked-text'
  return 'text-severity-safe-text'
}

function formatConfidence(confidence: number, level: string): string {
  return `${Math.round(confidence * 100)}% (${level})`
}

function isNewTriageStatus(status: Alert['triage_status']): boolean {
  return status === 'new' || status == null
}

function AlertsTableSkeletonRows({ rowCount = 5 }: { rowCount?: number }) {
  return (
    <>
      {Array.from({ length: rowCount }).map((_, index) => (
        <tr key={index} aria-hidden="true" className="border-b border-border-light">
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
            className="mt-3 rounded-md border border-border-light bg-bg-inset px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:border-primary hover:text-accent-purple"
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
        <p className="text-sm font-medium text-severity-high-text">Unable to load alerts.</p>
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md border border-border-light bg-bg-inset px-3 py-1.5 text-xs font-medium text-text-primary transition-colors hover:border-severity-high-border hover:text-severity-high-text"
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
          <span className="text-accent-purple">{isAsc ? '↑' : '↓'}</span>
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
  activeAlertId,
}: AlertsTableProps) {
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
  const { data, isPending, isError, refetch } = useAlertsFromFilters(params)
  const { mutate: updateTriage } = useTriageMutation()
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

  const handleRowClick = (alert: Alert) => {
    if (isNewTriageStatus(alert.triage_status)) {
      updateTriage({ id: alert.alert_id, status: 'in_review' })
      onAlertClick({ ...alert, triage_status: 'in_review' })
      return
    }

    onAlertClick(alert)
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
    params.prediction !== undefined ||
    params.window !== undefined ||
    (params.confidence_level && params.confidence_level.length > 0) ||
    (params.search && params.search.length > 0)
  )

  const selectedIdsSet = useMemo(() => new Set(selectedIds), [selectedIds])
  const canGoPrev = params.page > 1
  const canGoNext = !!data && params.page * params.pageSize < data.total

  return (
    <div className="overflow-hidden rounded-lg border border-border-light bg-bg-card">
      <div className="max-h-[500px] overflow-x-auto overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-bg-card">
            <tr className="border-b border-border-light">
              <th className="w-10 p-3">
                <input
                  type="checkbox"
                  checked={alerts.length > 0 && selectedIds.length === alerts.length}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="h-4 w-4 cursor-pointer rounded border-border-light bg-bg-card text-accent-purple accent-[var(--color-primary)] focus:ring-2 focus:ring-accent-purple focus:ring-offset-0"
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
          <tbody className="divide-y divide-border-light">
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
                    `group cursor-pointer transition-colors duration-100 hover:bg-bg-inset` +
                    (alert.alert_id === (typeof activeAlertId !== 'undefined' ? activeAlertId : undefined)
                      ? ' bg-bg-inset ring-1 ring-primary/30'
                      : '')
                  }
                  onClick={() => handleRowClick(alert)}
                >
                  <td className="p-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIdsSet.has(alert.alert_id)}
                      onChange={() => handleSelectOne(alert.alert_id)}
                      className="h-4 w-4 cursor-pointer rounded border-border-light bg-bg-card text-accent-purple accent-[var(--color-primary)] focus:ring-2 focus:ring-accent-purple focus:ring-offset-0"
                      aria-label={`Select alert ${alert.alert_id}`}
                    />
                  </td>
                  <td className="p-3">
                    <TriageBadge triage_status={alert.triage_status ?? null} />
                  </td>
                  <td className="whitespace-nowrap p-3 font-mono text-[10px] text-[var(--color-text-primary)]">
                    <div>{formatTimeOnly(alert.timestamp)}</div>
                    <div className="text-xs text-[var(--color-text-muted)]">
                      {formatRelativeTime(alert.timestamp)}
                    </div>
                  </td>
                  <td className="whitespace-nowrap p-3 font-mono text-xs text-[var(--color-text-secondary)]">
                    {alert.source_ip ?? '—'}
                  </td>
                  <td
                    className={
                      `w-[200px] max-w-[200px] overflow-hidden truncate whitespace-nowrap p-3 text-xs ` +
                      (alert.request_path?.trim().startsWith('•')
                        ? 'font-normal text-[var(--color-text-secondary)]'
                        : 'font-mono text-xs text-[var(--color-accent-analytic)]')
                    }
                    title={alert.request_path ?? '—'}
                  >
                    {alert.request_path ?? '—'}
                  </td>
                  <td className="p-3 text-xs text-[var(--color-text-primary)]">{alert.prediction}</td>
                  <td className="p-3">
                    <span className={`font-mono text-xs ${getConfidenceTextColor(alert.confidence)}`}>
                      {formatConfidence(alert.confidence, alert.confidence_level)}
                    </span>
                  </td>
                  <td className="p-3">
                    <ActionLabel action={alert.action_taken} bordered={false} />
                  </td>
                  <td className="p-3 font-mono text-xs text-[var(--color-text-secondary)]">
                    {formatCrsScore(alert.crs_score)}
                  </td>
                  <td className="p-3 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      type="button"
                      className="flex h-6 w-6 items-center justify-center rounded text-[var(--color-text-secondary)] hover:bg-bg-inset hover:text-[var(--color-text-primary)]"
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
        <div className="flex items-center justify-between border-t border-border-light px-4 py-3">
          <p className="text-xs text-[var(--color-text-secondary)]">Loading...</p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled
              className="rounded border border-border-light bg-bg-inset px-3 py-1 text-xs font-medium text-text-primary transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              ← Prev
            </button>
            <span className="text-xs text-[var(--color-text-secondary)]">Page 1</span>
            <button
              type="button"
              disabled
              className="rounded border border-border-light bg-bg-inset px-3 py-1 text-xs font-medium text-text-primary transition-colors disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next →
            </button>
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-between border-t border-border-light px-4 py-3">
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
              disabled={!canGoPrev}
              className="rounded border border-border-light bg-bg-inset px-3 py-1 text-xs font-medium text-text-primary transition-colors hover:border-primary hover:text-accent-purple disabled:cursor-not-allowed disabled:opacity-50"
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
              disabled={!canGoNext}
              className="rounded border border-border-light bg-bg-inset px-3 py-1 text-xs font-medium text-text-primary transition-colors hover:border-primary hover:text-accent-purple disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next →
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

export function AlertsTable({ selectedIds, onSelectionChange, onAlertClick, activeAlertId }: AlertsTableProps) {
  return (
    <Suspense
      fallback={
        <div className="overflow-hidden rounded-lg border border-border-light bg-bg-card">
          <div className="max-h-[500px] overflow-x-auto overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10 bg-bg-card">
                <tr className="border-b border-border-light">
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
        activeAlertId={activeAlertId}
      />
    </Suspense>
  )
}
