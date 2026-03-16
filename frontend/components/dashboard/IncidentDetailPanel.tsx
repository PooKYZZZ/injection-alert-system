'use client'

import { useDashboardStore } from 'store/dashboardStore'
import { useAlert } from 'features/alerts/queries'
import { ALERT_DISPLAY_ACTION_ALIASES } from 'features/alerts/contract'

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
  const { data: incident, isPending } = useAlert(activeIncidentId)

  if (activeIncidentId === null) return null

  return (
    <aside className="fixed right-0 top-0 h-full w-[480px] bg-surface-light border-l border-border-light shadow-lg z-50 overflow-y-auto flex flex-col">
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border-light sticky top-0 bg-surface-light z-10">
        <div className="flex flex-col gap-1 min-w-0">
          {isPending ? (
            <div className="animate-pulse bg-gray-200 rounded h-5 w-40" />
          ) : incident ? (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 className="text-sm font-bold text-text-main">
                  Incident #{incident.alert_id}
                </h2>
                <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-bold bg-red-600 text-white">
                  {incident.prediction}
                </span>
              </div>
              <span className="text-xs text-text-muted">
                {new Date(incident.timestamp).toLocaleString()}
              </span>
            </>
          ) : null}
        </div>
        <button
          type="button"
          onClick={() => setActiveIncident(null)}
          className="shrink-0 ml-2 text-text-muted hover:text-text-main transition-colors"
          aria-label="Close incident panel"
        >
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>
      </div>

      {/* Body */}
      {isPending ? (
        <PanelSkeleton />
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
                  {incident.source_ip ?? 'Unknown'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Request Method
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.request_method ?? 'Unknown'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Request Path
                </span>
                <span className="text-sm font-medium text-text-main break-all">
                  {incident.request_path ?? 'Unavailable'}
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
                    : 'Unavailable'}
                </span>
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  CRS Score
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.crs_score ?? 'Unavailable'}
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
                  {incident.payload_snippet}
                </code>
              </pre>
            </div>
          </section>
        </div>
      ) : (
        <div className="flex items-center justify-center flex-1 p-8">
          <p className="text-sm text-text-muted">Incident not found.</p>
        </div>
      )}
    </aside>
  )
}
