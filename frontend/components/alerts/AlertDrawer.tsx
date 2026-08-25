'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { motion, AnimatePresence } from 'motion/react'
import { useState } from 'react'
import type { Alert, LabelReview, TriageStatus } from '@/features/alerts/types'
import { ALERT_DISPLAY_ACTION_ALIASES, VERIFIED_LABEL_VALUES } from '@/features/alerts/contract'
import type { AlertAction, VerifiedLabel } from '@/features/alerts/contract'
import { useTriageMutation, useActionMutation, useLabelReviewMutation } from '@/features/alerts/queries'
import { cn } from '@/lib/utils'
import { formatAlertDateTime, formatConfidenceLabel } from '@/lib/date-time'
import { PERMISSIONS, roleHasPermission } from '@/lib/auth/roles'
import { describeEvidenceRelationship } from '@/features/alerts/evidence'
import { StatusBadge } from '@/components/ui/StatusBadge'

interface AlertDrawerProps {
  role?: unknown
  alert: Alert | null
  onClose: () => void
  onTriageUpdated?: (alert: Alert) => void
  onActionUpdated?: (alert: Alert) => void
  onReviewUpdated?: (alertId: string, review: LabelReview) => void
}

function formatTriageLabel(status: TriageStatus | null | undefined): string {
  switch (status) {
    case 'in_review':
      return 'In review'
    case 'escalated':
      return 'Escalated'
    case 'resolved':
      return 'Resolved'
    case 'false_positive':
      return 'False positive'
    case 'new':
    case null:
    case undefined:
      return 'New'
    default:
      return status
  }
}

function isNewTriageStatus(status: TriageStatus | null | undefined): boolean {
  return status === 'new' || status == null
}

function formatCrsScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  return score.toFixed(2)
}

function AlertDrawerContent({ role, alert, onClose, onTriageUpdated, onActionUpdated, onReviewUpdated }: AlertDrawerProps) {
  const canTriage = roleHasPermission(role, PERMISSIONS.ALERTS_TRIAGE)
  const canUpdateAction = roleHasPermission(
    role,
    PERMISSIONS.ALERTS_ACTION_UPDATE
  )
  const [verifiedLabel, setVerifiedLabel] = useState<VerifiedLabel | ''>(
    alert?.label_review?.verified_label ?? ''
  )
  const [reviewNote, setReviewNote] = useState('')
  const {
    mutate,
    isPending,
    isError,
  } = useTriageMutation()

  const handleVerdictClick = (status: TriageStatus) => {
    if (alert && !isPending) {
      mutate(
        { id: alert.alert_id, status },
        { onSuccess: (updatedAlert) => onTriageUpdated?.(updatedAlert) }
      )
    }
  }

  const handleStartReview = () => {
    if (alert && !isPending && isNewTriageStatus(displayStatus)) {
      mutate(
        { id: alert.alert_id, status: 'in_review' },
        { onSuccess: (updatedAlert) => onTriageUpdated?.(updatedAlert) }
      )
    }
  }

  const {
    mutate: mutateAction,
    isPending: isActionPending,
    isError: isActionError,
  } = useActionMutation()

  const handleActionClick = (action: AlertAction) => {
    if (alert && !isActionPending) {
      mutateAction(
        { id: alert.alert_id, action },
        { onSuccess: (updatedAlert) => onActionUpdated?.(updatedAlert) }
      )
    }
  }

  const {
    mutate: mutateLabelReview,
    isPending: isLabelReviewPending,
    isError: isLabelReviewError,
  } = useLabelReviewMutation()

  const handleLabelReview = (
    approvalState: 'approved_for_training' | 'excluded_from_training'
  ) => {
    if (alert && verifiedLabel && !isLabelReviewPending) {
      mutateLabelReview({
        id: alert.alert_id,
        verifiedLabel,
        approvalState,
        reviewNote: reviewNote || undefined,
      }, {
        onSuccess: (review) => onReviewUpdated?.(alert.alert_id, review),
      })
    }
  }

  const displayStatus = alert?.triage_status ?? null
  const displayAction = alert?.action_taken ?? null

  const triageLabel = formatTriageLabel(displayStatus)
  const confidenceLabel = alert
    ? formatConfidenceLabel(alert.confidence, alert.confidence_level)
    : '—'
  const crsRuleIds = alert?.crs_rule_ids?.length ? alert.crs_rule_ids.join(', ') : '—'
  const evidenceRelationship = alert
    ? describeEvidenceRelationship(alert)
    : null
  const hasCorrelatedCrsEvidence = Boolean(
    evidenceRelationship && evidenceRelationship.kind !== 'ml_only'
  )

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
                className="fixed right-0 top-0 z-30 flex h-full w-full max-w-[520px] flex-col border-l border-surface-border bg-surface-card shadow-2xl"
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
              >
                {/* Hidden description to satisfy Radix accessibility warnings */}
                <Dialog.Description className="sr-only">
                  Details for {alert.prediction} — {formatAlertDateTime(alert.timestamp)}. Contains summary details, WAF evidence, captured request data, and role-appropriate review controls.
                </Dialog.Description>

                {/* Header */}
                <div className="sticky top-0 z-10 flex items-start justify-between border-b border-surface-border bg-surface-card p-5">
                  <div className="min-w-0 space-y-2">
                    <Dialog.Title className="text-base font-semibold text-text-primary">
                      Alert details
                    </Dialog.Title>
                    <p className="text-sm text-text-secondary">{alert.prediction}</p>
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge label={triageLabel} tone={displayStatus === 'escalated' ? 'danger' : displayStatus === 'resolved' ? 'success' : displayStatus === 'in_review' ? 'warning' : 'info'} domain="workflow" />
                      <StatusBadge
                        label={displayAction ? ALERT_DISPLAY_ACTION_ALIASES[displayAction] : 'No recorded outcome'}
                        tone={displayAction === 'BLOCKED' ? 'danger' : displayAction === 'THROTTLED' ? 'warning' : displayAction === 'ALLOWED' ? 'success' : 'neutral'}
                        domain="enforcement"
                      />
                    </div>
                    {isError && (
                      <span className="block text-[11px] text-severity-high-text">
                        Triage update failed. Please retry.
                      </span>
                    )}
                    {isActionError && (
                      <span className="block text-[11px] text-severity-high-text">
                        Recorded outcome update failed. Please retry.
                      </span>
                    )}
                    {isLabelReviewError && (
                      <span className="block text-[11px] text-severity-high-text">
                        Verified-label review failed. Please retry.
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
                <div
                  data-testid="alert-drawer-scroll-region"
                  className="min-h-0 flex-1 overflow-y-auto p-5"
                >
                  <div className="grid content-start gap-5">
                  <section className="border-t-0 pt-0">
                    <h3 className="mb-3 text-sm font-semibold text-text-primary">
                      Detection details
                    </h3>
                    <dl className="grid grid-cols-[minmax(92px,auto)_1fr] gap-x-3 gap-y-2 text-sm leading-5">
                      <dt className="text-xs font-medium text-text-secondary">
                        Alert ID
                      </dt>
                      <dd className="font-mono text-[var(--color-text-primary)]">
                        {alert.alert_id}
                      </dd>
                      <dt className="text-xs font-medium text-text-secondary">
                        Time
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {formatAlertDateTime(alert.timestamp)}
                      </dd>
                      <dt className="text-xs font-medium text-text-secondary">
                        Source IP
                      </dt>
                      <dd className="font-mono text-[11px] text-[var(--color-accent-analytic)]">
                        {alert.source_ip ?? '—'}
                      </dd>
                      <dt className="text-xs font-medium text-text-secondary">
                        Model confidence
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {confidenceLabel}
                        <span className="mt-0.5 block text-[10px] text-[var(--color-text-secondary)]">
                          Model certainty, not attack severity.
                        </span>
                      </dd>
                    </dl>
                  </section>

                  <section className="border-t border-surface-border pt-4">
                    <h3 className="mb-3 text-sm font-semibold text-text-primary">
                      WAF evidence
                    </h3>
                    {evidenceRelationship ? (
                      <div className="mb-3 rounded-md border border-surface-border bg-surface-inset p-2">
                        <p className="text-[11px] font-medium text-[var(--color-text-primary)]">
                          {evidenceRelationship.label}
                        </p>
                        <p className="mt-1 text-[10px] leading-4 text-[var(--color-text-secondary)]">
                          {evidenceRelationship.description}
                        </p>
                      </div>
                    ) : null}
                    {!hasCorrelatedCrsEvidence ? (
                      <p className="text-[11px] text-[var(--color-text-secondary)]">
                        No correlated CRS evidence available
                      </p>
                    ) : (
                      <>
                        <dl className="grid grid-cols-[minmax(112px,auto)_1fr] gap-x-3 gap-y-2 text-sm leading-5">
                          <dt className="text-xs font-medium text-text-secondary">
                            Transaction ID
                          </dt>
                          <dd className="font-mono text-[11px] text-[var(--color-text-primary)] break-all">
                            {alert.transaction_id ?? '—'}
                          </dd>
                          <dt className="text-xs font-medium text-text-secondary">
                            Ingest source
                          </dt>
                          <dd className="text-[var(--color-text-primary)]">{alert.ingest_source ?? '—'}</dd>
                          <dt className="text-xs font-medium text-text-secondary">
                            Provenance
                          </dt>
                          <dd className="text-[var(--color-text-primary)]">{alert.source_provenance ?? '—'}</dd>
                          <dt className="text-xs font-medium text-text-secondary">
                            Verification
                          </dt>
                          <dd className="text-[var(--color-text-primary)]">{alert.source_verification_status ?? '—'}</dd>
                          <dt className="text-xs font-medium text-text-secondary">
                            CRS anomaly score
                          </dt>
                          <dd className="text-severity-blocked-text">{formatCrsScore(alert.crs_score)}</dd>
                          <dt className="text-xs font-medium text-text-secondary">
                            Rule IDs
                          </dt>
                          <dd className="font-mono text-[11px] text-[var(--color-text-primary)] break-all">{crsRuleIds}</dd>
                        </dl>
                        {alert.matched_rule_messages?.length ? (
                          <div className="mt-3 border-t border-surface-border pt-2">
                            <p className="text-xs font-semibold text-text-secondary">
                              Rule messages
                            </p>
                            <ul className="mt-1 list-disc space-y-1 pl-4 text-[10px] leading-4 text-[var(--color-text-primary)]">
                              {alert.matched_rule_messages.map((message, index) => (
                                <li key={`${message}-${index}`}>{message}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {alert.matched_rule_tags?.length ? (
                          <div className="mt-3 border-t border-surface-border pt-2">
                            <p className="text-xs font-semibold text-text-secondary">
                              Rule tags
                            </p>
                            <p className="mt-1 break-words font-mono text-[10px] leading-4 text-[var(--color-text-primary)]">
                              {alert.matched_rule_tags.join(', ')}
                            </p>
                          </div>
                        ) : null}
                      </>
                    )}
                  </section>

                  <section>
                    <h3 className="mb-2 text-sm font-semibold text-text-primary">
                      Captured request
                    </h3>
                    <div className="max-h-44 overflow-auto rounded-lg border border-surface-border bg-surface-inset">
                      <div className="grid grid-cols-2 gap-2 border-b border-surface-border px-3 py-2 text-xs">
                        <div>
                          <p className="text-text-secondary">Host</p>
                          <p className="font-mono text-[var(--color-text-primary)]">—</p>
                        </div>
                        <div>
                          <p className="text-text-secondary">Source IP</p>
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

                  <details className="border-t border-surface-border pt-4">
                    <summary className="cursor-pointer list-none text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-border focus-visible:ring-offset-2 focus-visible:ring-offset-surface-card">
                      Training feedback
                    </summary>
                    <div className="mt-3">
                    <p className="mb-3 text-sm leading-5 text-text-secondary">
                      Record a verified label for the training review process. This does not change the current model automatically.
                    </p>
                    {canTriage ? (
                      <div className="space-y-2">
                        <label htmlFor="verified-label" className="sr-only">
                          Verified classification
                        </label>
                        <select
                          id="verified-label"
                          aria-label="Verified classification"
                          value={verifiedLabel}
                          onChange={(event) => setVerifiedLabel(event.target.value as VerifiedLabel | '')}
                          disabled={isLabelReviewPending}
                          className="w-full rounded-md border border-surface-border bg-surface-card px-2.5 py-1.5 text-[11px] text-[var(--color-text-primary)]"
                        >
                          <option value="">Select a canonical class</option>
                          {VERIFIED_LABEL_VALUES.map((label) => (
                            <option key={label} value={label}>{label}</option>
                          ))}
                        </select>
                        <label htmlFor="review-note" className="sr-only">Review note (optional)</label>
                        <textarea
                          id="review-note"
                          aria-label="Review note (optional)"
                          value={reviewNote}
                          onChange={(event) => setReviewNote(event.target.value)}
                          maxLength={1000}
                          disabled={isLabelReviewPending}
                          placeholder="Optional review note"
                          className="min-h-14 w-full rounded-md border border-surface-border bg-surface-card px-2.5 py-1.5 text-[11px] text-[var(--color-text-primary)]"
                        />
                        <div className="flex gap-1.5">
                          <button
                            type="button"
                            disabled={!verifiedLabel || isLabelReviewPending}
                            onClick={() => handleLabelReview('approved_for_training')}
                            className="flex-1 rounded-md border border-severity-safe-border px-2.5 py-1.5 text-[11px] font-medium text-severity-safe-text disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            {isLabelReviewPending ? 'Saving...' : 'Approve for training'}
                          </button>
                          <button
                            type="button"
                            disabled={!verifiedLabel || isLabelReviewPending}
                            onClick={() => handleLabelReview('excluded_from_training')}
                            className="flex-1 rounded-md border border-action-border px-2.5 py-1.5 text-[11px] font-medium text-action-accent disabled:cursor-not-allowed disabled:opacity-50"
                          >
                            Exclude from training
                          </button>
                        </div>
                      </div>
                    ) : (
                      <p className="text-[11px] text-[var(--color-text-secondary)]">Viewer mode: training feedback is read-only.</p>
                    )}
                    {alert.label_review && (
                      <p className="mt-3 text-xs text-text-secondary">
                        Latest: {alert.label_review.verified_label} ({alert.label_review.approval_state.replaceAll('_', ' ')}) by {alert.label_review.reviewer_id} at {formatAlertDateTime(alert.label_review.reviewed_at)}
                      </p>
                    )}
                    </div>
                  </details>

                  <section className="border-t border-surface-border pt-4">
                    <div className="grid gap-5 md:grid-cols-2">
                      <div>
                        <h3 className="mb-2 text-sm font-semibold text-text-primary">
                          Analyst disposition
                        </h3>
                        <p className="mb-3 text-sm leading-5 text-text-secondary">
                          Your review decision is separate from the recorded enforcement outcome.
                        </p>
                        {canTriage ? (
                        <div className="flex flex-col gap-1.5">
                          {isNewTriageStatus(displayStatus) ? (
                            <>
                              <p className="mb-1 text-[11px] leading-4 text-[var(--color-text-secondary)]">
                                Opening this drawer is read-only. Start a review when you are ready to record analyst ownership.
                              </p>
                              <button
                                type="button"
                                aria-label="Start Review"
                                disabled={isPending}
                                onClick={handleStartReview}
                                className={cn(
                                  'flex w-full items-center justify-between rounded-md border border-action-border bg-action-bg px-2.5 py-1.5 text-left text-[11px] font-medium text-action-accent transition-colors hover:bg-action-bg/70',
                                  isPending && 'cursor-not-allowed opacity-50'
                                )}
                              >
                                <span>Start Review</span>
                                {isPending ? <span>Updating...</span> : <span>→</span>}
                              </button>
                            </>
                          ) : null}
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
                            <span>False positive</span>
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

                      <details>
                        <summary className="cursor-pointer list-none text-sm font-semibold text-text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-action-border focus-visible:ring-offset-2 focus-visible:ring-offset-surface-card">
                          Recorded system outcome
                        </summary>
                        <div className="mt-3">
                        <p className="mb-3 text-sm leading-5 text-text-secondary">
                          This is the action recorded when the request was processed. Updating it changes the stored alert record; it does not replay the request or apply a new network rule.
                        </p>
                        {canUpdateAction ? (
                        <div className="flex flex-col gap-1.5">
                      <p className="text-xs font-semibold text-text-secondary">
                        Update recorded outcome
                      </p>
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
                      </details>
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

export function AlertDrawer(props: AlertDrawerProps) {
  return <AlertDrawerContent key={props.alert?.alert_id ?? 'closed'} {...props} />
}
