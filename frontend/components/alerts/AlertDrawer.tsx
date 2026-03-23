'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { motion, AnimatePresence } from 'motion/react'
import type { Alert, TriageStatus } from '@/features/alerts/types'
import { SeverityBadge } from '@/components/ui/SeverityBadge'
import { ActionLabel } from '@/components/ui/ActionLabel'
import { TriageBadge } from '@/components/ui/TriageBadge'
import { ALERT_DISPLAY_ACTION_ALIASES } from '@/features/alerts/contract'
import { useTriageMutation } from '@/features/alerts/queries'
import { cn } from '@/lib/utils'

interface AlertDrawerProps {
  alert: Alert | null
  onClose: () => void
}

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

export function AlertDrawer({ alert, onClose }: AlertDrawerProps) {
  const {
    mutate,
    isPending,
    variables,
    isError,
  } = useTriageMutation()

  // Display optimistic status while mutation is pending
  const displayStatus = isPending && variables?.id === alert?.alert_id
    ? variables.status
    : (alert?.triage_status ?? null)

  const handleVerdictClick = (status: TriageStatus) => {
    if (alert && !isPending) {
      mutate({ id: alert.alert_id, status })
    }
  }

  const topShapValues =
    alert?.shap_values && alert.shap_values.length > 0
      ? [...alert.shap_values]
          .sort((a, b) => Math.abs(b.contribution) - Math.abs(a.contribution))
          .slice(0, 5)
      : []
  const maxContribution = Math.max(...topShapValues.map((item) => Math.abs(item.contribution)), 1)

  return (
    <Dialog.Root open={!!alert} onOpenChange={(open) => !open && onClose()}>
      <AnimatePresence>
        {alert && (
          <Dialog.Portal forceMount>
            {/* Backdrop */}
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-20 bg-black/40 backdrop-blur-[1px]"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>

            {/* Drawer panel */}
            <Dialog.Content asChild>
              <motion.div
                className="fixed top-0 right-0 z-30 flex h-full w-[420px] flex-col border-l border-[var(--color-text-ghost)] bg-[var(--color-bg-base)] shadow-2xl"
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
              >
                {/* Visually hidden title for screen readers */}
                <Dialog.Title className="sr-only">
                  Alert detail for {alert.prediction}
                </Dialog.Title>

                {/* Header */}
                <div className="sticky top-0 z-10 flex items-start justify-between border-b border-[var(--color-text-ghost)] bg-[var(--color-bg-base)] p-4">
                  <div className="min-w-0">
                    <h2 className="text-[14px] font-medium text-[var(--color-text-primary)]">
                      {alert.prediction}
                    </h2>
                    <div className="mt-2 flex flex-wrap items-center gap-2">
                      <span className="text-[10px] text-[var(--color-text-secondary)]">
                        {formatUtcTimestamp(alert.timestamp)}
                      </span>
                      <SeverityBadge
                        severity={alert.confidence_level}
                        prediction={alert.prediction}
                      />
                      <ActionLabel action={alert.action_taken} />
                      {displayStatus && <TriageBadge triage_status={displayStatus} />}
                      {isError && (
                        <span className="text-[11px] text-red-400">
                          Update failed — please retry
                        </span>
                      )}
                    </div>
                  </div>
                  <Dialog.Close asChild>
                    <button
                      type="button"
                      aria-label="Close alert detail"
                      className="ml-2 flex h-7 w-7 items-center justify-center rounded-md border border-transparent text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-text-ghost)] hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        aria-hidden="true"
                      >
                        <line x1="18" y1="6" x2="6" y2="18" />
                        <line x1="6" y1="6" x2="18" y2="18" />
                      </svg>
                    </button>
                  </Dialog.Close>
                </div>

                {/* Content */}
                <div className="flex-1 overflow-y-auto p-4">
                  {/* Verdict buttons */}
                  <section className="mb-6">
                    <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.09em] text-[var(--color-text-secondary)]">
                      Triage Verdict
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      <button
                        type="button"
                        disabled={isPending}
                        onClick={() => handleVerdictClick('false_positive')}
                        className={cn(
                          'rounded border px-3 py-1.5 text-xs font-medium transition-colors',
                          displayStatus === 'false_positive'
                            ? 'border-[var(--color-text-ghost)] bg-[var(--color-text-ghost)] text-[var(--color-text-primary)]'
                            : 'border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-ghost)] hover:bg-[var(--color-text-ghost)]',
                          isPending && 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        {isPending && variables?.status === 'false_positive' ? (
                          <span className="inline-flex items-center gap-1">
                            <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24">
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                                fill="none"
                              />
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              />
                            </svg>
                            Updating...
                          </span>
                        ) : (
                          'False Positive'
                        )}
                      </button>
                      <button
                        type="button"
                        disabled={isPending}
                        onClick={() => handleVerdictClick('escalated')}
                        className={cn(
                          'rounded border px-3 py-1.5 text-xs font-medium transition-colors',
                          displayStatus === 'escalated'
                            ? 'border-red-800 bg-red-950/50 text-red-400'
                            : 'border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-ghost)] hover:bg-[var(--color-text-ghost)]',
                          isPending && 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        {isPending && variables?.status === 'escalated' ? (
                          <span className="inline-flex items-center gap-1">
                            <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24">
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                                fill="none"
                              />
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              />
                            </svg>
                            Updating...
                          </span>
                        ) : (
                          'Escalate'
                        )}
                      </button>
                      <button
                        type="button"
                        disabled={isPending}
                        onClick={() => handleVerdictClick('resolved')}
                        className={cn(
                          'rounded border px-3 py-1.5 text-xs font-medium transition-colors',
                          displayStatus === 'resolved'
                            ? 'border-emerald-800 bg-emerald-950/50 text-emerald-400'
                            : 'border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] text-[var(--color-text-secondary)] hover:border-[var(--color-text-ghost)] hover:bg-[var(--color-text-ghost)]',
                          isPending && 'opacity-50 cursor-not-allowed'
                        )}
                      >
                        {isPending && variables?.status === 'resolved' ? (
                          <span className="inline-flex items-center gap-1">
                            <svg className="h-3 w-3 animate-spin" viewBox="0 0 24 24">
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                                fill="none"
                              />
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              />
                            </svg>
                            Updating...
                          </span>
                        ) : (
                          'Resolve'
                        )}
                      </button>
                    </div>
                  </section>

                  {/* Detection Timeline */}
                  <section className="mb-6">
                    <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.09em] text-[var(--color-text-secondary)]">
                      Detection Timeline
                    </h3>
                    <div className="relative space-y-4 before:absolute before:inset-0 before:ml-[3px] before:h-full before:w-[1px] before:-translate-x-px before:bg-[var(--color-text-ghost)]">
                      <div className="relative flex items-start gap-3">
                        <div className="relative z-10 mt-0.5 h-2 w-2 rounded-full bg-blue-400 ring-4 ring-[var(--color-bg-base)]" />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-blue-400">Request Received</p>
                          <p className="mt-0.5 text-[10px] text-[var(--color-text-secondary)]">
                            {alert.request_method} {alert.request_path}
                          </p>
                        </div>
                      </div>
                      <div className="relative flex items-start gap-3">
                        <div className="relative z-10 mt-0.5 h-2 w-2 rounded-full bg-amber-500 ring-4 ring-[var(--color-bg-base)]" />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-amber-500">CRS Flagged</p>
                          <p className="mt-0.5 text-[10px] text-[var(--color-text-secondary)]">
                            Score:{' '}
                            {alert.crs_score !== null && alert.crs_score !== undefined
                              ? alert.crs_score.toFixed(2)
                              : '—'}
                          </p>
                        </div>
                      </div>
                      <div className="relative flex items-start gap-3">
                        <div className="relative z-10 mt-0.5 h-2 w-2 rounded-full bg-violet-400 ring-4 ring-[var(--color-bg-base)]" />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs font-medium text-violet-400">ML Inference</p>
                          <p className="mt-0.5 text-[10px] text-[var(--color-text-secondary)]">
                            {alert.prediction} · {Math.round(alert.confidence * 100)}% confidence
                          </p>
                        </div>
                      </div>
                      <div className="relative flex items-start gap-3">
                        <div
                          className={cn(
                            'relative z-10 mt-0.5 h-2 w-2 rounded-full ring-4 ring-[var(--color-bg-base)]',
                            alert.action_taken === 'BLOCKED' ? 'bg-red-500' : 'bg-emerald-500'
                          )}
                        />
                        <div className="min-w-0 flex-1">
                          <p
                            className={cn(
                              'text-xs font-medium',
                              alert.action_taken === 'BLOCKED' ? 'text-red-400' : 'text-emerald-400'
                            )}
                          >
                            Action Taken
                          </p>
                          <p className="mt-0.5 text-[10px] text-[var(--color-text-secondary)]">
                            {alert.action_taken
                              ? ALERT_DISPLAY_ACTION_ALIASES[alert.action_taken]
                              : '—'}
                          </p>
                        </div>
                      </div>
                    </div>
                  </section>

                  {/* Explainability (SHAP) */}
                  <section className="mb-6">
                    <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.09em] text-[var(--color-text-secondary)]">
                      Explainability
                    </h3>
                    {topShapValues.length > 0 ? (
                      <div className="space-y-2">
                        {topShapValues.map((item) => (
                          <div
                            key={item.feature_name}
                            className="grid grid-cols-[100px_1fr_48px] items-center gap-2"
                          >
                            <span className="truncate font-mono text-[10px] text-[var(--color-text-secondary)]">
                              {item.feature_name}
                            </span>
                            <div className="h-1.5 overflow-hidden rounded-full bg-[var(--color-bg-panel)]">
                              <div
                                className="h-full rounded-full bg-violet-500"
                                style={{
                                  width: `${(Math.abs(item.contribution) / maxContribution) * 100}%`,
                                }}
                              />
                            </div>
                            <span className="text-right font-mono text-[10px] tabular-nums text-[var(--color-text-secondary)]">
                              {item.contribution.toFixed(3)}
                            </span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="rounded border border-[var(--color-text-ghost)] bg-[var(--color-bg-panel)] px-3 py-2 text-[10px] text-[var(--color-text-secondary)]">
                        No explainability data available.
                      </p>
                    )}
                  </section>

                  {/* Captured Payload */}
                  <section className="mb-6">
                    <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.09em] text-[var(--color-text-secondary)]">
                      Captured Payload
                    </h3>
                    <div className="overflow-hidden rounded-md border border-[var(--color-text-ghost)] bg-[var(--color-bg-base)]">
                      <pre className="whitespace-pre-wrap break-all p-3 font-mono text-[10px] leading-[1.8] text-[var(--color-text-secondary)]">
                        <span className="text-amber-400">{alert.request_method ?? '—'}</span>{' '}
                        <span className="text-red-400">{alert.request_path ?? '—'}</span>{' '}
                        <span className="text-[var(--color-text-secondary)]">HTTP/1.1</span>
                        {'\n'}
                        <span className="text-blue-400">Host</span>:{' '}
                        <span className="text-[var(--color-text-secondary)]">dashboard.local</span>
                        {'\n'}
                        <span className="text-blue-400">Source-IP</span>:{' '}
                        <span className="text-[var(--color-text-secondary)]">{alert.source_ip ?? '—'}</span>
                        {'\n'}
                        {'\n'}
                        <span className="text-[var(--color-text-primary)]">
                          {alert.payload_snippet?.trim() || 'No payload captured.'}
                        </span>
                      </pre>
                    </div>
                  </section>

                  {/* Source */}
                  <section>
                    <h3 className="mb-3 text-[11px] font-semibold uppercase tracking-[0.09em] text-[var(--color-text-secondary)]">
                      Source
                    </h3>
                    <div className="grid grid-cols-2 gap-x-4 gap-y-3">
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
                          Source IP
                        </p>
                        <p className="font-mono text-sm text-[var(--color-text-secondary)]">
                          {alert.source_ip ?? '—'}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
                          Request Method
                        </p>
                        <p className="text-sm text-[var(--color-text-primary)]">{alert.request_method ?? '—'}</p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
                          Request Path
                        </p>
                        <p className="break-all text-sm text-[var(--color-text-primary)]">
                          {alert.request_path ?? '—'}
                        </p>
                      </div>
                      <div>
                        <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
                          CRS Score
                        </p>
                        <p className="text-sm text-amber-400">
                          {alert.crs_score !== null && alert.crs_score !== undefined
                            ? alert.crs_score.toFixed(2)
                            : '—'}
                        </p>
                      </div>
                      {alert.source_intel && (
                        <>
                          {alert.source_intel.asn && (
                            <div>
                              <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
                                ASN
                              </p>
                              <p className="text-sm text-[var(--color-text-secondary)]">{alert.source_intel.asn}</p>
                            </div>
                          )}
                          {alert.source_intel.country && (
                            <div>
                              <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
                                Country
                              </p>
                              <p className="text-sm text-[var(--color-text-secondary)]">
                                {alert.source_intel.country}
                              </p>
                            </div>
                          )}
                          {alert.source_intel.reputation_score !== undefined && (
                            <div>
                              <p className="text-[10px] uppercase tracking-wider text-[var(--color-text-secondary)]">
                                Reputation
                              </p>
                              <p className="text-sm text-[var(--color-text-secondary)]">
                                {alert.source_intel.reputation_score.toFixed(1)}
                              </p>
                            </div>
                          )}
                        </>
                      )}
                    </div>
                  </section>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  )
}



