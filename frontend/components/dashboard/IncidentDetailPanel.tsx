'use client'

import { useEffect, useRef } from 'react'
import { useDashboardStore } from 'store/dashboardStore'
import { useAlert } from 'features/alerts/queries'
import { ALERT_DISPLAY_ACTION_ALIASES } from 'features/alerts/contract'

function formatRuleIds(ruleIds: string[] | null | undefined): string {
  if (!ruleIds || ruleIds.length === 0) return 'No data available'
  return ruleIds.join(', ')
}

function formatUtcTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) return 'Not reviewed'
  if (!/(Z|[+-]\d{2}:\d{2})$/.test(timestamp)) return timestamp

  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return timestamp
  return parsed.toLocaleString()
}

function PanelSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="animate-pulse bg-gray-200 rounded h-6 w-48" />
      <div className="animate-pulse bg-gray-200 rounded h-24 w-full" />
      <div className="animate-pulse bg-gray-200 rounded h-32 w-full" />
      <div className="animate-pulse bg-gray-200 rounded h-20 w-full" />
    </div>
  )
}

export default function IncidentDetailPanel() {
  const activeIncidentId = useDashboardStore(s => s.activeIncidentId)
  const setActiveIncident = useDashboardStore(s => s.setActiveIncident)
  const { data: incident, isPending, isError, error } = useAlert(activeIncidentId)
  const closeButtonRef = useRef<HTMLButtonElement | null>(null)
  const restoreFocusRef = useRef<HTMLElement | null>(null)
  const panelOpen = activeIncidentId !== null

  useEffect(() => {
    if (!panelOpen) return

    const activeElement = document.activeElement
    restoreFocusRef.current = activeElement instanceof HTMLElement ? activeElement : null

    // Keep keyboard users in context when the panel opens.
    closeButtonRef.current?.focus()

    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    return () => {
      document.body.style.overflow = previousOverflow
      restoreFocusRef.current?.focus()
    }
  }, [panelOpen])

  useEffect(() => {
    if (!panelOpen) return

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        setActiveIncident(null)
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [panelOpen, setActiveIncident])

  if (!panelOpen) return null

  return (
    <>
      <div
        className="fixed inset-0 z-40 bg-black/50"
        onClick={() => setActiveIncident(null)}
        aria-hidden="true"
      />
      <aside
        className="fixed right-0 top-0 z-50 flex h-full w-[480px] flex-col overflow-y-auto border-l border-border-light bg-surface-light shadow-lg"
        role="dialog"
        aria-modal="true"
        aria-labelledby="incident-panel-title"
      >
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border-light sticky top-0 bg-surface-light z-10">
        <div className="flex flex-col gap-1 min-w-0">
          {isPending ? (
            <div className="animate-pulse bg-gray-200 rounded h-5 w-40" />
          ) : incident ? (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 id="incident-panel-title" className="text-sm font-bold text-text-main">
                  Incident #{incident.alert_id}
                </h2>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-red-600 text-white">
                  {incident.prediction}
                </span>
              </div>
              <span className="text-xs text-text-muted">
                {formatUtcTimestamp(incident.timestamp)}
              </span>
            </>
          ) : (
            <h2 id="incident-panel-title" className="text-sm font-bold text-text-main">
              Incident detail
            </h2>
          )}
        </div>
        <button
          ref={closeButtonRef}
          type="button"
          onClick={() => setActiveIncident(null)}
          className="ml-2 shrink-0 text-text-muted transition-colors hover:text-text-main focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 focus-visible:ring-offset-surface-light"
          aria-label="Close incident panel"
        >
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>
      </div>

      {/* Body */}
      {isPending ? (
        <PanelSkeleton />
      ) : isError ? (
        <div className="flex flex-col gap-2 p-4" role="alert">
          <p className="text-sm font-medium text-status-high">Failed to load incident details</p>
          <p className="text-xs text-text-muted">
            {error instanceof Error ? error.message : 'Unexpected error while loading incident details'}
          </p>
        </div>
      ) : incident ? (
        <div className="flex flex-col gap-6 p-4">
          <section>
            <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-2">
              Alert Details
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Source IP
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.source_ip ?? 'Unavailable with current response'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Request Method
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.request_method ?? 'Unavailable with current response'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Request Path
                </span>
                <span className="text-sm font-medium text-text-main break-all">
                  {incident.request_path ?? 'Unavailable with current response'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Prediction
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.prediction}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  ML Confidence
                </span>
                <span className="text-sm font-medium text-text-main">
                  {Math.round(incident.confidence * 100)}%
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Confidence Level
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.confidence_level}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Action Taken
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.action_taken
                    ? ALERT_DISPLAY_ACTION_ALIASES[incident.action_taken]
                    : 'Unavailable with current response'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  CRS Score
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.crs_score ?? 'Unavailable with current response'}
                </span>
              </div>
              <div className="flex flex-col gap-1 col-span-2">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  CRS Rule IDs
                </span>
                <span className="text-sm font-medium text-text-main font-mono break-all">
                  {formatRuleIds(incident.crs_rule_ids)}
                </span>
              </div>
            </div>
          </section>

          <section>
            <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-2">
              Analyst Review
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Analyst Label
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.analyst_label ?? 'Not reviewed'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Labeled By
                </span>
                <span className="text-sm font-medium text-text-main break-all">
                  {incident.labeled_by ?? 'Not reviewed'}
                </span>
              </div>
              <div className="flex flex-col gap-1 col-span-2">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Labeled At
                </span>
                <span className="text-sm font-medium text-text-main">
                  {formatUtcTimestamp(incident.labeled_at)}
                </span>
              </div>
            </div>
          </section>

          {/* Captured Payload */}
          <section>
            <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-2">
              Captured Payload
            </h3>
            <div className="bg-gray-50 border border-border-light rounded-sm p-3 overflow-x-auto">
              <pre className="m-0">
                <code className="font-mono text-xs text-red-700 break-all">
                  {incident.payload_snippet || 'No data available'}
                </code>
              </pre>
            </div>
          </section>
        </div>
      ) : (
        <div className="flex items-center justify-center flex-1 p-8">
          <p className="text-sm text-text-muted">No data available</p>
        </div>
      )}
      </aside>
    </>
  )
}
