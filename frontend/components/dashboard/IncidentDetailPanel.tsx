'use client'

import { useEffect, useRef, useState } from 'react'
import { useDashboardStore } from 'store/dashboardStore'
import { useAlert } from 'features/alerts/queries'
import { ALERT_DISPLAY_ACTION_ALIASES } from 'features/alerts/contract'
import { ShapChart } from '@/components/ui/ShapChart'

const FOCUS_RING_CLASS =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-surface-light'

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

function formatConfidence(confidence: number): string {
  return `${Math.round(confidence * 100)}%`
}

function getFocusableElements(container: HTMLElement): HTMLElement[] {
  return [...container.querySelectorAll<HTMLElement>(
    'a[href], button:not([disabled]), textarea:not([disabled]), input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )].filter(
    (element) =>
      !element.hasAttribute('disabled') &&
      element.getAttribute('aria-hidden') !== 'true' &&
      !element.closest('[aria-hidden="true"]')
  )
}

function PanelSkeleton() {
  return (
    <div className="flex flex-col gap-4 p-4">
      <div className="h-6 w-48 animate-pulse rounded bg-border-light" />
      <div className="h-24 w-full animate-pulse rounded bg-border-light" />
      <div className="h-32 w-full animate-pulse rounded bg-border-light" />
      <div className="h-20 w-full animate-pulse rounded bg-border-light" />
    </div>
  )
}

export default function IncidentDetailPanel() {
  const activeIncidentId = useDashboardStore(s => s.activeIncidentId)
  const setActiveIncident = useDashboardStore(s => s.setActiveIncident)
  const { data: incident, isPending, isError, error } = useAlert(activeIncidentId)
  const closeButtonRef = useRef<HTMLButtonElement | null>(null)
  const panelRef = useRef<HTMLElement | null>(null)
  const restoreFocusRef = useRef<HTMLElement | null>(null)
  const panelOpen = activeIncidentId !== null
  const [isEntering, setIsEntering] = useState(false)

  useEffect(() => {
    if (!panelOpen) return

    setIsEntering(false)

    const activeElement = document.activeElement
    restoreFocusRef.current = activeElement instanceof HTMLElement ? activeElement : null

    requestAnimationFrame(() => {
      setIsEntering(true)
      closeButtonRef.current?.focus()
    })

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
        return
      }

      if (event.key !== 'Tab' || !panelRef.current) {
        return
      }

      const focusable = getFocusableElements(panelRef.current)
      if (focusable.length === 0) {
        event.preventDefault()
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const activeElement = document.activeElement

      if (event.shiftKey && activeElement === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [panelOpen, setActiveIncident])

  if (!panelOpen) return null

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity duration-200 ease-out ${
          isEntering ? 'opacity-100' : 'opacity-0'
        }`}
        onClick={() => setActiveIncident(null)}
        aria-hidden="true"
      />
      <aside
        ref={panelRef}
        className={`fixed right-0 top-0 z-50 flex h-full w-[480px] flex-col overflow-y-auto border-l border-border-light bg-surface-light shadow-lg transition-transform duration-250 ease-out will-change-transform ${
          isEntering ? 'translate-x-0' : 'translate-x-full'
        }`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="incident-panel-title"
      >
      {/* Header */}
      <div className="flex items-start justify-between p-4 border-b border-border-light sticky top-0 bg-surface-light z-10">
        <div className="flex flex-col gap-1 min-w-0">
          {isPending ? (
            <div className="animate-pulse rounded h-5 w-40 bg-border-light" />
          ) : incident ? (
            <>
              <div className="flex items-center gap-2 flex-wrap">
                <h2 id="incident-panel-title" className="text-sm font-bold text-text-main">
                  Incident #{incident.alert_id}
                </h2>
                <span
                  className={`inline-flex items-center rounded px-2 py-0.5 text-[10px] font-bold ${
                    incident.prediction === 'Normal'
                      ? 'bg-border-light text-text-muted'
                      : 'bg-status-high/15 text-status-high'
                  }`}
                >
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
          className={`ml-2 inline-flex min-h-6 min-w-6 shrink-0 items-center justify-center text-text-muted transition-colors hover:text-text-main ${FOCUS_RING_CLASS}`}
          aria-label="Close incident panel"
        >
          <span className="material-symbols-outlined text-[20px]">close</span>
        </button>
      </div>

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
              Detection Timeline
            </h3>
            <ol className="space-y-4 border-l border-border-light pl-4">
              <li className="relative">
                <span className="absolute -left-[21px] top-1 h-3 w-3 rounded-full border-2 border-primary bg-surface-light" />
                <p className="text-sm font-medium text-text-main">Request Received</p>
                <p className="text-xs text-text-muted">
                  {formatUtcTimestamp(incident.timestamp)}
                  {incident.request_method || incident.request_path
                    ? ` · ${(incident.request_method ?? 'Request')} ${incident.request_path ?? ''}`.trim()
                    : ''}
                </p>
              </li>
              <li className="relative">
                <span className="absolute -left-[21px] top-1 h-3 w-3 rounded-full border-2 border-orange-400 bg-surface-light" />
                <p className="text-sm font-medium text-text-main">CRS Flagged</p>
                <p className="text-xs text-text-muted">
                  CRS score {incident.crs_score === undefined ? 'unavailable with current response' : Number(incident.crs_score).toFixed(2)}
                </p>
                <p className="text-xs font-mono text-text-muted">
                  {formatRuleIds(incident.crs_rule_ids)}
                </p>
              </li>
              <li className="relative">
                <span className="absolute -left-[21px] top-1 h-3 w-3 rounded-full border-2 border-status-medium bg-surface-light" />
                <p className="text-sm font-medium text-text-main">ML Inference</p>
                <p className="text-xs text-text-muted">
                  {incident.prediction} at {formatConfidence(incident.confidence)} confidence ({incident.confidence_level})
                </p>
              </li>
              <li className="relative">
                <span className="absolute -left-[21px] top-1 h-3 w-3 rounded-full border-2 border-status-high bg-surface-light" />
                <p className="text-sm font-medium text-text-main">Action Taken</p>
                <p className="text-xs text-text-muted">
                  {incident.action_taken
                    ? ALERT_DISPLAY_ACTION_ALIASES[incident.action_taken]
                    : 'Unavailable with current response'}
                </p>
              </li>
            </ol>
          </section>

          <section>
            <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-2">
              Explainability
            </h3>
            {incident.shap_values && incident.shap_values.length > 0 ? (
              <div className="rounded-sm border border-border-light bg-sidebar-active p-3">
                <p className="mb-3 text-xs text-text-muted">
                  Token contribution is shown only because this alert includes real `shap_values` data.
                </p>
                <ShapChart features={incident.shap_values} />
              </div>
            ) : (
              <div className="rounded-sm border border-dashed border-border-light p-3 text-sm text-text-muted">
                Token contribution is unavailable with the current incident response.
              </div>
            )}
          </section>

          <section>
            <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-2">
              Captured Payload
            </h3>
            <div className="overflow-x-auto rounded-sm border border-border-light bg-sidebar-active p-3">
              <pre className="m-0">
                <code className="break-all font-mono text-xs text-status-high">
                  {incident.payload_snippet || 'No data available'}
                </code>
              </pre>
            </div>
          </section>

          <section>
            <h3 className="text-[13px] font-semibold text-text-muted uppercase tracking-wider mb-2">
              Source
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
              {incident.user_agent !== undefined && (
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
                    User Agent
                  </span>
                  <span className="text-sm font-medium text-text-main break-all">
                    {incident.user_agent || 'Unavailable with current response'}
                  </span>
                </div>
              )}
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
