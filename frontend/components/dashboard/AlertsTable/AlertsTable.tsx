'use client'

import { useState, useEffect, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useShallow } from 'zustand/react/shallow'
import { useAlerts } from 'features/alerts/queries'
import type { Alert } from 'features/alerts/types'
import { useDashboardStore } from 'store/dashboardStore'
import type { DashboardFilters, SeverityFilter, TimeRange } from 'lib/searchParams'
import { cn } from 'lib/utils'
import { SeverityBadge } from 'components/ui/SeverityBadge'
import { ConfidenceBar } from 'components/ui/ConfidenceBar'
import { ActionLabel } from 'components/ui/ActionLabel'
import BulkActionBar from 'components/dashboard/AlertsTable/BulkActionBar'

interface DashboardStoreState {
  selectedAlertIds: Set<string>
  toggleAlertSelection: (id: string) => void
  selectAll: (ids: string[]) => void
  clearSelection: () => void
  setActiveIncident: (id: string | null) => void
}

function formatRuleIds(ruleIds: string[] | null | undefined): string {
  if (!ruleIds || ruleIds.length === 0) return '—'
  if (ruleIds.length === 1) return ruleIds[0]
  return `${ruleIds[0]} +${ruleIds.length - 1}`
}

function AlertsTableSkeleton() {
  return (
    <div className="bg-surface-light border border-border-light rounded-sm shadow-subtle overflow-hidden">
      <div className="p-4 border-b border-border-light">
        <div className="animate-pulse bg-gray-200 rounded h-4 w-32" />
      </div>
      <div className="divide-y divide-border-light">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="flex items-center gap-4 p-4">
            <div className="animate-pulse bg-gray-200 rounded h-4 w-4" />
            <div className="animate-pulse bg-gray-200 rounded h-4 w-16" />
            <div className="animate-pulse bg-gray-200 rounded h-4 w-32" />
            <div className="animate-pulse bg-gray-200 rounded h-4 w-24" />
            <div className="animate-pulse bg-gray-200 rounded h-4 w-12" />
            <div className="animate-pulse bg-gray-200 rounded h-4 flex-1" />
            <div className="animate-pulse bg-gray-200 rounded h-4 w-20" />
            <div className="animate-pulse bg-gray-200 rounded h-4 w-24" />
            <div className="animate-pulse bg-gray-200 rounded h-4 w-16" />
          </div>
        ))}
      </div>
    </div>
  )
}

function AlertsTableError({ message }: { message: string }) {
  return (
    <div className="bg-surface-light border border-status-high/50 rounded-sm shadow-subtle p-4">
      <p className="text-sm font-medium text-status-high">Failed to load alerts</p>
      <p className="mt-1 text-xs text-text-muted">{message}</p>
    </div>
  )
}

function AlertsTableContent() {
  const searchParams = useSearchParams()

  const filters: DashboardFilters = {
    severity: (searchParams.get('severity') ?? 'ALL') as SeverityFilter,
    timeRange: (searchParams.get('timeRange') ?? '24h') as TimeRange,
    search: searchParams.get('search') ?? '',
  }

  const { toggleAlertSelection, selectAll, clearSelection, setActiveIncident } = useDashboardStore()
  const selectedIds = useDashboardStore(useShallow((s: DashboardStoreState) => [...s.selectedAlertIds]))

  useEffect(() => {
    if (selectedIds.length > 0) clearSelection()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.severity, filters.timeRange, filters.search])

  const { data, isPending, isError, error } = useAlerts(filters)

  const alerts = data?.items ?? []
  const hasFilter =
    filters.search.trim().length > 0 || filters.severity !== 'ALL' || filters.timeRange !== '24h'

  function getRowBorderClass(alert: Alert): string {
    if (alert.confidence_level === 'HIGH') return 'border-l-[3px] border-l-red-500'
    if (alert.confidence_level === 'MEDIUM') return 'border-l-[3px] border-l-orange-400'
    return 'border-l-[3px] border-l-gray-300'
  }

  if (isPending) {
    return <AlertsTableSkeleton />
  }

  if (isError) {
    return (
      <AlertsTableError
        message={error instanceof Error ? error.message : 'Unexpected error while loading alerts'}
      />
    )
  }

  if (!data) {
    return <AlertsTableError message="Unavailable with current response" />
  }

  return (
    <div className="bg-surface-light border border-border-light rounded-sm shadow-subtle overflow-hidden">
      <div className="p-4 border-b border-border-light flex items-center justify-between">
        <h2 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider">
          Alerts
        </h2>
        {selectedIds.length > 0 && <BulkActionBar />}
      </div>
      <div className="overflow-x-auto max-h-[420px] overflow-y-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border-light bg-[#16233A]">
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
                  className="rounded border-gray-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface-light"
                  aria-label="Select all alerts"
                />
              </th>
              <th className="p-3 text-left text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Confidence Level
              </th>
              <th className="p-3 text-left text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Timestamp
              </th>
              <th className="p-3 text-left text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                CRS Score
              </th>
              <th className="p-3 text-left text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Rule IDs
              </th>
              <th className="p-3 text-left text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Target Path
              </th>
              <th className="p-3 text-left text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Attack Type
              </th>
              <th className="p-3 text-left text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                ML Confidence
              </th>
              <th className="p-3 text-left text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                Action
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border-light">
            {alerts.map((alert) => (
              <tr
                key={alert.alert_id}
                className={cn(
                  'cursor-pointer hover:bg-[#16233A] transition-colors focus-within:bg-[#16233A] focus-visible:outline focus-visible:outline-2 focus-visible:outline-primary focus-visible:outline-offset-[-2px]',
                  getRowBorderClass(alert)
                )}
                onClick={() => setActiveIncident(alert.alert_id)}
                onKeyDown={(e) => {
                  if (e.target instanceof HTMLInputElement) return
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
                    className="rounded border-gray-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface-light"
                    aria-label={`Select alert ${alert.alert_id}`}
                  />
                </td>
                <td className="p-3">
                  <SeverityBadge severity={alert.confidence_level} />
                </td>
                <td className="p-3 text-xs text-text-muted whitespace-nowrap">
                  {new Date(alert.timestamp).toLocaleString()}
                </td>
                <td className="p-3 text-xs text-text-muted tabular-nums">
                  {alert.crs_score ?? '—'}
                </td>
                <td className="p-3 text-xs font-mono text-text-muted whitespace-nowrap">
                  {formatRuleIds(alert.crs_rule_ids)}
                </td>
                <td className="p-3 text-xs font-mono text-text-main max-w-[200px] truncate">
                  {alert.request_path ?? '—'}
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
            ))}
            {alerts.length === 0 && (
              <tr>
                <td colSpan={9} className="p-8 text-center text-sm text-text-muted">
                  {hasFilter ? 'No matching alerts' : 'No alerts found'}
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

export default function AlertsTable() {
  return (
    <Suspense fallback={<AlertsTableSkeleton />}>
      <AlertsTableContent />
    </Suspense>
  )
}
