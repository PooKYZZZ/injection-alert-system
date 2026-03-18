'use client'

import { useEffect, useRef, useState } from 'react'
import { useDashboardStore } from 'store/dashboardStore'
import { useAlert } from 'features/alerts/queries'
import { ALERT_DISPLAY_ACTION_ALIASES } from 'features/alerts/contract'
import { cn } from '@/lib/utils'
import { SeverityBadge } from '@/components/ui/SeverityBadge'

const FOCUS_RING_CLASS =
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/85 focus-visible:ring-offset-2 focus-visible:ring-offset-bg-panel'

function formatUtcTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) return '—'
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return timestamp
  return parsed.toLocaleString('en-US', {
    timeZone: 'UTC',
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
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
      <div className="h-6 w-48 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
      <div className="h-24 w-full rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
      <div className="h-32 w-full rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
      <div className="h-20 w-full rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
    </div>
  )
}

function ActionBadge({ action }: { action: 'BLOCKED' | 'ALLOWED' | 'THROTTLED' | null }) {
  if (!action) {
    return <span className="text-[10px] text-text-muted">Not included in current response.</span>
  }

  const className =
    action === 'BLOCKED'
      ? 'border-severity-blocked-border bg-severity-blocked-bg text-severity-blocked-text'
      : action === 'ALLOWED'
        ? 'border-severity-safe-border bg-severity-safe-bg text-severity-safe-text'
        : 'border-severity-blocked-border bg-severity-blocked-bg text-severity-blocked-text'

  return (
    <span className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${className}`}>
      {ALERT_DISPLAY_ACTION_ALIASES[action]}
    </span>
  )
}

function TimelineStep({
  title,
  detail,
  dotClassName,
  labelClassName,
  badge,
  emphasize = false,
  showLine = true,
}: {
  title: string
  detail: string
  dotClassName: string
  labelClassName: string
  badge?: React.ReactNode
  emphasize?: boolean
  showLine?: boolean
}) {
  const dotSize = emphasize ? '22px' : '18px'
  const lineLeft = emphasize ? '11px' : '9px'
  return (
    <li className="relative mb-3 pl-10 last:mb-0">
      {showLine ? (
        <div
          className="absolute top-[22px] w-px bg-border-light"
          style={{ left: lineLeft, height: 'calc(100% + 18px)' }}
          aria-hidden="true"
        />
      ) : null}
      <span
        className={`absolute left-0 top-0 rounded-full ${dotClassName}`}
        style={{ width: dotSize, height: dotSize }}
      />
      <p className={`text-sm font-medium ${labelClassName}`}>{title}</p>
      {badge ? <div className="mt-1">{badge}</div> : null}
      <p className="mt-1 text-xs text-text-secondary">{detail}</p>
    </li>
  )
}

export default function IncidentDetailPanel() {
  const activeIncidentId = useDashboardStore((state) => state.activeIncidentId)
  const setActiveIncident = useDashboardStore((state) => state.setActiveIncident)
  const { data: incident, isPending, isError, error } = useAlert(activeIncidentId)
  const closeButtonRef = useRef<HTMLButtonElement | null>(null)
  const panelRef = useRef<HTMLElement | null>(null)
  const restoreFocusRef = useRef<HTMLElement | null>(null)
  const panelOpen = activeIncidentId !== null
  const [isEntering, setIsEntering] = useState(false)
  const onClose = () => setActiveIncident(null)

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

      if (event.key !== 'Tab' || !panelRef.current) return

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

  const topShapValues =
    incident?.shap_values && incident.shap_values.length > 0
      ? [...incident.shap_values]
          .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
          .slice(0, 3)
      : []
  const maxContribution = Math.max(...topShapValues.map((item) => Math.abs(item.contribution)), 1)

  return (
    <>
      <div
        className={`fixed inset-0 z-40 bg-black/50 transition-opacity duration-200 ease-out ${
          isEntering ? 'opacity-100' : 'opacity-0'
        }`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        ref={panelRef}
        className={`fixed right-0 top-0 z-50 flex h-full w-[520px] flex-col overflow-y-auto border-l border-border-light bg-bg-panel shadow-lg transition-transform duration-[250ms] ease-out ${
          isEntering ? 'translate-x-0' : 'translate-x-full'
        }`}
        role="dialog"
        aria-modal="true"
        aria-label={incident ? `Alert detail: ${incident.prediction}` : 'Alert detail'}
      >
        <div className="sticky top-0 z-10 flex items-start justify-between border-b border-border-light bg-bg-panel p-4">
          <div className="min-w-0">
            {isPending || !incident ? (
              <div className="h-5 w-40 rounded bg-bg-elevated [animation:skeleton-pulse_1.5s_ease-in-out_infinite]" />
            ) : (
              <>
                <h2 className="text-[14px] font-medium text-text-primary">
                  Alert — {incident.prediction}
                </h2>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <span className="text-[10px] text-text-muted">{formatUtcTimestamp(incident.timestamp)}</span>
                  <SeverityBadge severity={incident.confidence_level} prediction={incident.prediction} />
                  <ActionBadge action={incident.action_taken} />
                </div>
              </>
            )}
          </div>
          <button
            ref={closeButtonRef}
            onClick={onClose}
            aria-label="Close alert detail"
            style={{
              minWidth: '28px',
              minHeight: '28px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: '6px',
              border: '1px solid transparent',
              background: 'transparent',
              color: 'var(--color-text-muted)',
              cursor: 'pointer',
              transition: 'background 0.1s ease, color 0.1s ease',
            }}
            onMouseEnter={(event) => {
              event.currentTarget.style.background = 'var(--color-bg-elevated)'
              event.currentTarget.style.color = 'var(--color-text-primary)'
            }}
            onMouseLeave={(event) => {
              event.currentTarget.style.background = 'transparent'
              event.currentTarget.style.color = 'var(--color-text-muted)'
            }}
            className={cn('ml-2', FOCUS_RING_CLASS)}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        {isError ? (
          <div className="flex flex-col gap-2 p-4" role="alert">
            <p className="text-sm font-medium text-severity-high-text">Unable to load alert detail.</p>
            <p className="text-xs text-text-secondary">
              {error instanceof Error ? error.message : 'Unexpected error while loading alert details.'}
            </p>
          </div>
        ) : isPending || !incident ? (
          <PanelSkeleton />
        ) : (
          <div className="flex flex-col gap-6 p-4">
            <section>
              <h3 className="mb-[10px] text-[9px] font-semibold uppercase tracking-[0.09em] text-text-muted">
                Detection Timeline
              </h3>
              <ol className="space-y-[12px]">
                <TimelineStep
                  title="Request Received"
                  detail={`${formatUtcTimestamp(incident.timestamp)} · ${incident.request_method ?? '—'} ${incident.request_path ?? '—'}`}
                  dotClassName="border-2 border-accent-blue bg-accent-blue-bg"
                  labelClassName="text-accent-blue"
                />
                <TimelineStep
                  title="CRS Flagged"
                  detail={`CRS score: ${incident.crs_score !== null && incident.crs_score !== undefined ? incident.crs_score.toFixed(2) : '—'}`}
                  dotClassName="border-2 border-accent-amber bg-accent-amber-bg"
                  labelClassName="text-accent-amber"
                />
                <TimelineStep
                  title="ML Inference"
                  detail={`${incident.prediction} · ${(incident.confidence * 100).toFixed(0)}% confidence · ${incident.confidence_level}`}
                  dotClassName="border-2 border-accent-purple bg-accent-purple-bg"
                  labelClassName="text-accent-purple"
                />
                <TimelineStep
                  title="Action Taken"
                  detail={
                    incident.action_taken
                      ? ALERT_DISPLAY_ACTION_ALIASES[incident.action_taken]
                      : 'Not included in current response.'
                  }
                  dotClassName={
                    incident.action_taken === 'BLOCKED'
                      ? 'border-2 border-severity-high-accent bg-severity-high-bg'
                      : 'border-2 border-severity-safe-accent bg-severity-safe-bg'
                  }
                  labelClassName={
                    incident.action_taken === 'BLOCKED'
                      ? 'text-severity-high-text'
                      : 'text-severity-safe-text'
                  }
                  badge={
                    <span
                      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-[10px] font-semibold ${
                        incident.action_taken === 'BLOCKED'
                          ? 'border-severity-blocked-border bg-severity-blocked-bg text-severity-blocked-text'
                          : 'border-severity-safe-border bg-severity-safe-bg text-severity-safe-text'
                      }`}
                    >
                      {incident.action_taken === 'BLOCKED'
                        ? 'REQUEST BLOCKED'
                        : incident.action_taken === 'ALLOWED'
                          ? 'REQUEST ALLOWED'
                          : 'REQUEST THROTTLED'}
                    </span>
                  }
                  emphasize
                  showLine={false}
                />
              </ol>
            </section>

            <section>
              <h3 className="mb-[10px] text-[9px] font-semibold uppercase tracking-[0.09em] text-text-muted">
                Explainability
              </h3>
              {topShapValues.length > 0 ? (
                <div className="space-y-3">
                  {topShapValues.map((item) => (
                    <div key={item.feature_name} className="grid grid-cols-[110px_1fr_auto] items-center gap-3">
                      <span className="truncate font-mono text-[10px] text-text-secondary">
                        {item.feature_name}
                      </span>
                      <div className="h-2 overflow-hidden rounded-full bg-bg-elevated">
                        <div
                          className="h-full rounded-full bg-accent-purple"
                          style={{ width: `${(Math.abs(item.contribution) / maxContribution) * 100}%` }}
                        />
                      </div>
                      <span className="text-[10px] tabular-nums text-text-secondary">
                        {item.contribution.toFixed(3)}
                      </span>
                    </div>
                  ))}
                </div>
              ) : incident.prediction === 'Normal' ? (
                <p className="text-[10px] text-text-muted">
                  Model classified this request as normal traffic with {(incident.confidence * 100).toFixed(0)}% confidence. No threat explanation generated.
                </p>
              ) : (
                <div className="rounded border border-border-light bg-bg-inset px-3 py-2 text-[10px] text-text-muted">
                  Token contribution not included in current response.
                </div>
              )}
            </section>

            <section>
              <h3 className="mb-[10px] text-[9px] font-semibold uppercase tracking-[0.09em] text-text-muted">
                Captured Payload
              </h3>
              <div className="rounded-md border border-border-light bg-bg-inset px-3 py-2">
                <pre className="m-0 whitespace-pre-wrap break-all font-mono text-[10px] leading-[1.8] text-text-secondary">
                  <span className="text-accent-amber">{incident.request_method ?? '—'}</span>{' '}
                  <span className="text-severity-high-text">{incident.request_path ?? '—'}</span>{' '}
                  <span className="text-text-muted">HTTP/1.1</span>
                  {'\n'}
                  <span className="text-accent-blue">Host</span>: <span className="text-text-secondary">dashboard.local</span>
                  {'\n'}
                  <span className="text-accent-blue">Source-IP</span>: <span className="text-text-secondary">{incident.source_ip ?? '—'}</span>
                  {'\n'}
                  {'\n'}
                  <span className="text-text-primary">{incident.payload_snippet?.trim() || 'Not included in current response.'}</span>
                </pre>
              </div>
            </section>

            <section>
              <h3 className="mb-[10px] text-[9px] font-semibold uppercase tracking-[0.09em] text-text-muted">
                Source
              </h3>
              <div className="grid grid-cols-2 gap-x-6 gap-y-3">
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-text-muted">Source IP</p>
                  <p className="font-mono text-sm text-text-secondary">{incident.source_ip ?? '—'}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-text-muted">Request Method</p>
                  <p className="text-sm text-text-primary">{incident.request_method ?? '—'}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-text-muted">Request Path</p>
                  <p className="break-all text-sm text-text-primary">{incident.request_path ?? '—'}</p>
                </div>
                <div>
                  <p className="text-[10px] uppercase tracking-wider text-text-muted">CRS Score</p>
                  <p className="text-sm text-accent-amber">
                    {incident.crs_score !== null && incident.crs_score !== undefined
                      ? incident.crs_score.toFixed(2)
                      : '—'}
                  </p>
                </div>
              </div>
            </section>
          </div>
        )}
      </aside>
    </>
  )
}
