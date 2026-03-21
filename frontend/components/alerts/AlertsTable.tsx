'use client'

import { useMemo, useState, Suspense } from 'react'
import { usePathname, useRouter, useSearchParams } from 'next/navigation'
import { useAlerts } from '@/features/alerts/queries'
import type { Alert, PaginatedAlerts, TriageStatus } from '@/features/alerts/types'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { ConfidenceBar } from '@/components/ui/ConfidenceBar'
import { ActionLabel } from '@/components/ui/ActionLabel'
import { TriageBadge } from '@/components/ui/TriageBadge'
import { cn } from '@/lib/utils'
import { DEFAULT_ALERT_FILTERS, normalizeAlertSearchParams } from '@/lib/searchParams'

interface AlertsTableProps {
  selectedIds: string[]
  onSelectionChange: (ids: string[]) => void
  onAlertClick: (alert: Alert) => void
}

type SortColumn = 'timestamp' | 'confidence' | 'severity' | 'action'

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
        <tr key={index} aria-hidden="true" className="border-b border-[#21262d]">
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
        <p className="text-sm text-[#7d8590]">
          {hasFilters ? 'No alerts match the current filters.' : 'No alerts in the current window.'}
        </p>
        {hasFilters && onClearFilters && (
          <button
            type="button"
            onClick={onClearFilters}
            className="mt-3 rounded-md border border-[#30363d] bg-[#21262d] px-3 py-1.5 text-xs font-medium text-[#e6edf3] transition-colors hover:bg-[#30363d]"
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
          className="mt-3 rounded-md border border-[#30363d] bg-[#21262d] px-3 py-1.5 text-xs font-medium text-[#e6edf3] transition-colors hover:bg-[#30363d]"
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
      <th className="p-3 text-left text-[9px] font-semibold uppercase tracking-[0.08em] text-[#7d8590]">
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
        className="flex items-center gap-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-[#7d8590] transition-colors hover:text-[#e6edf3]"
      >
        {column.label}
        {isActive ? (
          <span className="text-blue-400">{isAsc ? '↑' : '↓'}</span>
        ) : (
          <span className="text-[#484f58]">↕</span>
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
    () => normalizeAlertSearchParams(searchParams as unknown as Record<string, string | string[] | undefined>),
    [searchParams]
  )

  // Convert AlertFilters to DashboardFilters for useAlerts
  const dashboardFilters = useMemo(() => ({
    severity: params.severity ?? 'ALL',
    timeRange: (params.window as '1h' | '6h' | '24h' | '7d') ?? '24h',
    search: params.search ?? '',
  }), [params])

  const { data, isPending, isError, refetch } = useAlerts(dashboardFilters)
  const alerts = data?.items ?? []

  const [localSortBy, setLocalSortBy] = useState<SortColumn | null>(null)
  const [localSortDir, setLocalSortDir] = useState<'asc' | 'desc'>('desc')

  const currentSort = (params.sort_by as SortColumn) ?? localSortBy
  const currentDir = params.sort_dir ?? localSortDir

  const handleSort = (column: SortColumn) => {
    const newDir = currentSort === column && currentDir === 'desc' ? 'asc' : 'desc'

    const paramsObj = Object.fromEntries(searchParams.entries())
    const newParams = new URLSearchParams({
      ...paramsObj,
      sort_by: column,
      sort_dir: newDir,
      page: '1',
    })

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
    <div className="overflow-hidden rounded-lg border border-[#30363d] bg-[#0d1117]">
      <div className="max-h-[500px] overflow-x-auto overflow-y-auto">
        <table className="w-full text-sm">
          <thead className="sticky top-0 z-10 bg-[#161b22]">
            <tr className="border-b border-[#30363d]">
              <th className="w-10 p-3">
                <input
                  type="checkbox"
                  checked={alerts.length > 0 && selectedIds.length === alerts.length}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                  className="h-4 w-4 cursor-pointer rounded border-[#30363d] bg-[#0d1117] text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
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
          <tbody className="divide-y divide-[#21262d]">
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
                  className="group cursor-pointer transition-colors duration-100 hover:bg-[#161b22]"
                  onClick={() => onAlertClick(alert)}
                >
                  <td className="p-3" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIdsSet.has(alert.alert_id)}
                      onChange={() => handleSelectOne(alert.alert_id)}
                      className="h-4 w-4 cursor-pointer rounded border-[#30363d] bg-[#0d1117] text-blue-500 focus:ring-2 focus:ring-blue-500 focus:ring-offset-0"
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
                  <td className="whitespace-nowrap p-3 font-mono text-[10px] text-[#7d8590]">
                    {formatTimeOnly(alert.timestamp)}
                  </td>
                  <td className="whitespace-nowrap p-3 font-mono text-xs text-blue-400">
                    {alert.source_ip ?? '—'}
                  </td>
                  <td
                    className="w-[200px] max-w-[200px] overflow-hidden truncate whitespace-nowrap p-3 font-mono text-xs text-[#e6edf3]"
                    title={alert.request_path ?? '—'}
                  >
                    {alert.request_path ?? '—'}
                  </td>
                  <td className="whitespace-nowrap p-3 font-mono text-xs tabular-nums text-[#7d8590]">
                    {alert.crs_score !== null && alert.crs_score !== undefined
                      ? alert.crs_score.toFixed(2)
                      : '—'}
                  </td>
                  <td className="p-3 text-xs text-[#e6edf3]">{alert.prediction}</td>
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
                      className="flex h-6 w-6 items-center justify-center rounded text-[#7d8590] hover:bg-[#21262d] hover:text-[#e6edf3]"
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
      <div className="flex items-center justify-between border-t border-[#30363d] px-4 py-3">
        <p className="text-xs text-[#7d8590]">
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
              const paramsObj = Object.fromEntries(searchParams.entries())
              const newParams = new URLSearchParams({ ...paramsObj, page: String(newPage) })
              router.replace(`${pathname}?${newParams.toString()}`, { scroll: false })
            }}
            disabled={params.page <= 1}
            className="rounded border border-[#30363d] bg-[#21262d] px-3 py-1 text-xs font-medium text-[#e6edf3] transition-colors hover:bg-[#30363d] disabled:cursor-not-allowed disabled:opacity-50"
          >
            ← Prev
          </button>
          <span className="text-xs text-[#7d8590]">
            Page {params.page}
            {data ? ` of ${Math.ceil(data.total / params.pageSize)}` : ''}
          </span>
          <button
            type="button"
            onClick={() => {
              const newPage = (params.page ?? 1) + 1
              const paramsObj = Object.fromEntries(searchParams.entries())
              const newParams = new URLSearchParams({ ...paramsObj, page: String(newPage) })
              router.replace(`${pathname}?${newParams.toString()}`, { scroll: false })
            }}
            disabled={data ? params.page * params.pageSize >= data.total : true}
            className="rounded border border-[#30363d] bg-[#21262d] px-3 py-1 text-xs font-medium text-[#e6edf3] transition-colors hover:bg-[#30363d] disabled:cursor-not-allowed disabled:opacity-50"
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
        <div className="overflow-hidden rounded-lg border border-[#30363d] bg-[#0d1117]">
          <div className="max-h-[500px] overflow-x-auto overflow-y-auto">
            <table className="w-full text-sm">
              <thead className="sticky top-0 z-10 bg-[#161b22]">
                <tr className="border-b border-[#30363d]">
                  <th className="w-10 p-3">
                    <div className="h-4 w-4 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
                  </th>
                  {ALERT_TABLE_COLUMNS.map((column) => (
                    <th
                      key={column.key}
                      className="p-3 text-left text-[9px] font-semibold uppercase tracking-[0.08em] text-[#7d8590]"
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
