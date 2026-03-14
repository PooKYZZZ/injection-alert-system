'use client'

import { useDashboardStore } from 'store/dashboardStore'
import { useAlert } from 'features/alerts/queries'
import type { Alert } from 'features/alerts/types'
import { ALERT_DISPLAY_ACTION_ALIASES } from 'features/alerts/contract'
import { ShapChart } from 'components/ui/ShapChart'
import { cn } from 'lib/utils'

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

          {/* ML Feature Contribution (SHAP) */}
          <section>
            <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-1">
              ML Feature Contribution (SHAP)
            </h3>
            <p className="text-xs text-text-muted mb-3">
              Feature importance scores explaining the ML model decision.
            </p>
            <ShapChart features={incident.shap_values ?? []} />
          </section>

          {/* Source Intelligence */}
          <section>
            <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-2">
              Source Intelligence
            </h3>
            <div className="grid grid-cols-2 gap-4">
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  IP Reputation
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.source_intel?.ip ?? incident.source_ip}
                </span>
                {incident.source_intel?.reputation_score !== undefined && (
                  <span
                    className={cn(
                      'text-xs font-medium',
                      incident.source_intel.reputation_score > 70
                        ? 'text-red-600'
                        : incident.source_intel.reputation_score > 40
                        ? 'text-orange-500'
                        : 'text-green-600'
                    )}
                  >
                    Score: {incident.source_intel.reputation_score}
                  </span>
                )}
                {incident.source_intel?.asn && (
                  <span className="text-xs text-text-muted">
                    ASN: {incident.source_intel.asn}
                  </span>
                )}
              </div>
              <div className="flex flex-col gap-1">
                <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                  Geolocation
                </span>
                <span className="text-sm font-medium text-text-main">
                  {incident.source_intel?.country ?? 'Unknown'}
                </span>
                <span className="text-xs text-text-muted">
                  Method: {incident.request_method}
                </span>
                {incident.user_agent && (
                  <span className="text-xs text-text-muted truncate" title={incident.user_agent}>
                    UA: {incident.user_agent}
                  </span>
                )}
              </div>
            </div>
          </section>

          {/* ML Analysis & Action Timeline */}
          <section>
            <h3 className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-3">
              ML Analysis &amp; Action Timeline
            </h3>
            <ol className="flex flex-col gap-3">
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-blue-500 shrink-0" />
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs font-medium text-text-main">Request Received</span>
                  <span className="text-[10px] text-text-muted">
                    {new Date(incident.timestamp).toLocaleString()}
                  </span>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-orange-400 shrink-0" />
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs font-medium text-text-main">CRS Flagged</span>
                  <span className="text-[10px] text-text-muted">
                    Score: {incident.crs_score ?? 'N/A'}
                  </span>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <span className="mt-1 h-2 w-2 rounded-full bg-purple-500 shrink-0" />
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs font-medium text-text-main">ML Inference</span>
                  <span className="text-[10px] text-text-muted">
                    {incident.prediction} — Confidence: {Math.round(incident.confidence * 100)}%
                  </span>
                </div>
              </li>
              <li className="flex items-start gap-3">
                <span
                  className={cn(
                    'mt-1 h-2 w-2 rounded-full shrink-0',
                    incident.action_taken === 'BLOCKED'
                      ? 'bg-red-600'
                      : incident.action_taken === 'THROTTLED'
                      ? 'bg-orange-500'
                      : 'bg-gray-400'
                  )}
                />
                <div className="flex flex-col gap-0.5">
                  <span className="text-xs font-medium text-text-main">
                    Action: {ALERT_DISPLAY_ACTION_ALIASES[incident.action_taken]}
                  </span>
                  <span className="text-[10px] text-text-muted">
                    Enforcement applied
                  </span>
                </div>
              </li>
            </ol>
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
