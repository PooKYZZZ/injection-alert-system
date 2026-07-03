'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { motion, AnimatePresence } from 'motion/react'
import type { Alert, TriageStatus } from '@/features/alerts/types'
import { ALERT_DISPLAY_ACTION_ALIASES } from '@/features/alerts/contract'
import type { AlertAction } from '@/features/alerts/contract'
import { useTriageMutation, useActionMutation } from '@/features/alerts/queries'
import { cn } from '@/lib/utils'
import { PERMISSIONS, roleHasPermission } from '@/lib/auth/roles'

interface AlertDrawerProps {
  role?: unknown
  alert: Alert | null
  onClose: () => void
}

function formatAlertTimestamp(timestamp: string | null | undefined): string {
  if (!timestamp) return '—'
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return timestamp
  return parsed.toLocaleString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
  })
}

function formatTriageLabel(status: TriageStatus | null | undefined): string {
  switch (status) {
    case 'in_review':
      return 'In Review'
    case 'escalated':
      return 'Escalated'
    case 'resolved':
      return 'Resolved'
    case 'false_positive':
      return 'False Positive'
    case 'new':
    case null:
    case undefined:
      return 'New'
    default:
      return status
  }
}

function formatCrsScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  return score.toFixed(2)
}

export function AlertDrawer({ role, alert, onClose }: AlertDrawerProps) {
  const canTriage = roleHasPermission(role, PERMISSIONS.ALERTS_TRIAGE)
  const canUpdateAction = roleHasPermission(
    role,
    PERMISSIONS.ALERTS_ACTION_UPDATE
  )
  const {
    mutate,
    isPending,
    isError,
  } = useTriageMutation()

  const handleVerdictClick = (status: TriageStatus) => {
    if (alert && !isPending) {
      mutate({ id: alert.alert_id, status })
    }
  }

  const {
    mutate: mutateAction,
    isPending: isActionPending,
    isError: isActionError,
  } = useActionMutation()

  const handleActionClick = (action: AlertAction) => {
    if (alert && !isActionPending) {
      mutateAction({ id: alert.alert_id, action })
    }
  }

  const displayStatus = alert?.triage_status ?? null
  const displayAction = alert?.action_taken ?? null

  const triageLabel = formatTriageLabel(displayStatus)
  const requestLine = [alert?.request_method ?? '—', alert?.request_path ?? '—'].join(' ')
  const confidenceLabel = alert ? `${Math.round(alert.confidence * 100)}% (${alert.confidence_level})` : '—'
  const crsRuleIds = alert?.crs_rule_ids?.length ? alert.crs_rule_ids.join(', ') : '—'

  return (
    <Dialog.Root open={!!alert} onOpenChange={(open) => !open && onClose()}>
      <AnimatePresence>
        {alert && (
          <Dialog.Portal forceMount>
            {/* Backdrop (low-opacity so page remains visible) */}
            <Dialog.Overlay asChild>
              <motion.div
                className="fixed inset-0 z-20 bg-black/10"
                initial={{ opacity: 0 }}
                animate={{ opacity: 0.1 }}
                exit={{ opacity: 0 }}
              />
            </Dialog.Overlay>

            {/* Drawer panel */}
            <Dialog.Content asChild>
              <motion.div
                className="fixed top-0 right-0 z-30 flex h-full w-[420px] flex-col border-l border-surface-border bg-surface-card shadow-2xl"
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
              >
                {/* Visually hidden title for screen readers */}
                <Dialog.Title className="sr-only">
                  Alert detail for {alert.prediction}
                </Dialog.Title>
                {/* Hidden description to satisfy Radix accessibility warnings */}
                <Dialog.Description className="sr-only">
                  Details for {alert.prediction} — {formatAlertTimestamp(alert.timestamp)}. Contains summary details, WAF evidence, captured request data, and role-appropriate review controls.
                </Dialog.Description>

                {/* Header */}
                <div className="sticky top-0 z-10 flex items-start justify-between border-b border-surface-border bg-surface-card p-4">
                  <div className="min-w-0 space-y-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--color-text-secondary)]">
                      Alert summary
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-[16px] font-semibold text-[var(--color-text-primary)]">
                        {alert.prediction}
                      </span>
                      <span className="rounded-full border border-action-border bg-action-bg px-2 py-1 text-[10px] font-medium uppercase tracking-[0.08em] text-action-accent">
                        {triageLabel}
                      </span>
                      <span
                        className={cn(
                          'rounded-full border px-2 py-1 text-[10px] font-medium uppercase tracking-[0.08em]',
                          displayAction === 'BLOCKED'
                            ? 'border-severity-high-border text-severity-high-text'
                            : displayAction === 'THROTTLED'
                              ? 'border-severity-blocked-border text-severity-blocked-text'
                              : displayAction === 'ALLOWED'
                                ? 'border-severity-safe-border text-severity-safe-text'
                                : 'border-surface-border text-[var(--color-text-secondary)]'
                        )}
                      >
                        {displayAction ? ALERT_DISPLAY_ACTION_ALIASES[displayAction] : 'No Action'}
                      </span>
                    </div>
                    {isError && (
                      <span className="block text-[11px] text-severity-high-text">
                        Triage update failed. Please retry.
                      </span>
                    )}
                    {isActionError && (
                      <span className="block text-[11px] text-severity-high-text">
                        Intervention update failed. Please retry.
                      </span>
                    )}
                  </div>
                  <Dialog.Close asChild>
                    <button
                      type="button"
                      aria-label="Close alert detail"
                      className="ml-2 flex h-7 w-7 items-center justify-center rounded-md border border-transparent text-[var(--color-text-secondary)] transition-colors hover:bg-surface-inset hover:text-[var(--color-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-border"
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
                <div className="flex-1 overflow-hidden p-3">
                  <div className="grid content-start gap-3">
                  <section className="rounded-lg border border-surface-border bg-surface-panel p-3">
                    <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                      Core Details
                    </h3>
                    <dl className="grid grid-cols-[82px_1fr] gap-x-2 gap-y-2 text-[12px] leading-4">
                      <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        Time
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {formatAlertTimestamp(alert.timestamp)}
                      </dd>
                      <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        Source IP
                      </dt>
                      <dd className="font-mono text-[11px] text-[var(--color-accent-analytic)]">
                        {alert.source_ip ?? '—'}
                      </dd>
                      <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        Request
                      </dt>
                      <dd className="font-mono text-[11px] text-[var(--color-accent-analytic)] break-all">
                        {requestLine}
                      </dd>
                      <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        Confidence
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {confidenceLabel}
                      </dd>
                    </dl>
                  </section>

                  <section className="rounded-lg border border-surface-border bg-surface-panel p-3">
                    <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                      WAF Evidence
                    </h3>
                    <dl className="grid grid-cols-[82px_1fr] gap-x-2 gap-y-2 text-[12px] leading-4">
                      <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        CRS Score
                      </dt>
                      <dd className="text-severity-blocked-text">{formatCrsScore(alert.crs_score)}</dd>
                      <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        Rule IDs
                      </dt>
                      <dd className="font-mono text-[11px] text-[var(--color-text-primary)] break-all">{crsRuleIds}</dd>
                    </dl>
                  </section>

                  <section>
                    <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                      Captured Request
                    </h3>
                    <div className="max-h-44 overflow-auto rounded-lg border border-surface-border bg-surface-inset">
                      <div className="grid grid-cols-2 gap-2 border-b border-surface-border px-3 py-2 text-[10px]">
                        <div>
                          <p className="uppercase tracking-[0.08em] text-[var(--color-text-soft)]">Host</p>
                          <p className="font-mono text-[var(--color-text-primary)]">dashboard.local</p>
                        </div>
                        <div>
                          <p className="uppercase tracking-[0.08em] text-[var(--color-text-soft)]">Source-IP</p>
                          <p className="font-mono text-[var(--color-accent-analytic)]">{alert.source_ip ?? '—'}</p>
                        </div>
                      </div>
                      <pre className="whitespace-pre-wrap break-all p-3 font-mono text-[10px] leading-[1.6] text-[var(--color-text-secondary)]">
                        <span className="text-severity-blocked-text">{alert.request_method ?? '—'}</span>{' '}
                        <span className="text-severity-high-text">{alert.request_path ?? '—'}</span>{' '}
                        <span className="text-[var(--color-text-secondary)]">HTTP/1.1</span>
                        {'\n'}
                        {'\n'}
                        <span className="text-[var(--color-text-primary)]">
                          {alert.payload_snippet?.trim() || 'No payload captured.'}
                        </span>
                      </pre>
                    </div>
                  </section>

                  <section>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-lg border border-surface-border bg-surface-panel p-3">
                        <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                          Analyst Actions
                        </h3>
                        {canTriage ? (
                        <div className="flex flex-col gap-1.5">
                          <button
                            type="button"
                            disabled={isPending}
                            onClick={() => handleVerdictClick('resolved')}
                            className={cn(
                              'flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                              displayStatus === 'resolved'
                                ? 'border-severity-safe-border bg-severity-safe-bg text-severity-safe-text'
                                : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                              isPending && 'cursor-not-allowed opacity-50'
                            )}
                          >
                            <span>Resolve</span>
                            {isPending && displayStatus === 'resolved' ? <span>Updating...</span> : <span>→</span>}
                          </button>
                          <button
                            type="button"
                            disabled={isPending}
                            onClick={() => handleVerdictClick('false_positive')}
                            className={cn(
                              'flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                              displayStatus === 'false_positive'
                                ? 'border-action-border bg-action-bg text-action-accent'
                                : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                              isPending && 'cursor-not-allowed opacity-50'
                            )}
                          >
                            <span>False Positive</span>
                            {isPending && displayStatus === 'false_positive' ? <span>Updating...</span> : <span>→</span>}
                          </button>
                          <button
                            type="button"
                            disabled={isPending}
                            onClick={() => handleVerdictClick('escalated')}
                            className={cn(
                              'flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                              displayStatus === 'escalated'
                                ? 'border-severity-high-border bg-severity-high-bg text-severity-high-text'
                                : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                              isPending && 'cursor-not-allowed opacity-50'
                            )}
                          >
                            <span>Escalate</span>
                            {isPending && displayStatus === 'escalated' ? <span>Updating...</span> : <span>→</span>}
                          </button>
                        </div>
                        ) : (
                          <div className="space-y-1 text-[11px] text-[var(--color-text-secondary)]">
                            <p>Viewer mode: read-only.</p>
                            <p>Triage updates require Analyst or Admin.</p>
                          </div>
                        )}
                      </div>

                      <div className="rounded-lg border border-surface-border bg-surface-panel p-3">
                        <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                          Intervene
                        </h3>
                        {canUpdateAction ? (
                        <div className="flex flex-col gap-1.5">
                      <button
                        type="button"
                        disabled={isActionPending}
                        onClick={() => handleActionClick('BLOCKED')}
                        className={cn(
                          'flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                          displayAction === 'BLOCKED'
                            ? 'border-severity-high-border bg-severity-high-bg text-severity-high-text'
                            : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                          isActionPending && 'cursor-not-allowed opacity-50'
                        )}
                      >
                        {isActionPending && displayAction === 'BLOCKED' ? (
                          <>
                            <span>{ALERT_DISPLAY_ACTION_ALIASES.BLOCKED}</span>
                            <span>Applying...</span>
                          </>
                        ) : (
                          <>
                            <span>{ALERT_DISPLAY_ACTION_ALIASES.BLOCKED}</span>
                            <span>→</span>
                          </>
                        )}
                      </button>

                      <button
                        type="button"
                        disabled={isActionPending}
                        onClick={() => handleActionClick('THROTTLED')}
                        className={cn(
                          'flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                          displayAction === 'THROTTLED'
                            ? 'border-severity-blocked-border bg-severity-blocked-bg text-severity-blocked-text'
                            : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                          isActionPending && 'cursor-not-allowed opacity-50'
                        )}
                      >
                        {isActionPending && displayAction === 'THROTTLED' ? (
                          <>
                            <span>{ALERT_DISPLAY_ACTION_ALIASES.THROTTLED}</span>
                            <span>Applying...</span>
                          </>
                        ) : (
                          <>
                            <span>{ALERT_DISPLAY_ACTION_ALIASES.THROTTLED}</span>
                            <span>→</span>
                          </>
                        )}
                      </button>

                      <button
                        type="button"
                        disabled={isActionPending}
                        onClick={() => handleActionClick('ALLOWED')}
                        className={cn(
                          'flex w-full items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                          displayAction === 'ALLOWED'
                            ? 'border-severity-safe-border bg-severity-safe-bg text-severity-safe-text'
                            : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                          isActionPending && 'cursor-not-allowed opacity-50'
                        )}
                      >
                        {isActionPending && displayAction === 'ALLOWED' ? (
                          <>
                            <span>{ALERT_DISPLAY_ACTION_ALIASES.ALLOWED}</span>
                            <span>Applying...</span>
                          </>
                        ) : (
                          <>
                            <span>{ALERT_DISPLAY_ACTION_ALIASES.ALLOWED}</span>
                            <span>→</span>
                          </>
                        )}
                      </button>
                        </div>
                        ) : (
                          <p className="text-[11px] text-[var(--color-text-secondary)]">
                            Action updates require Admin.
                          </p>
                        )}
                      </div>
                    </div>
                  </section>
                  </div>
                </div>
              </motion.div>
            </Dialog.Content>
          </Dialog.Portal>
        )}
      </AnimatePresence>
    </Dialog.Root>
  )
}


