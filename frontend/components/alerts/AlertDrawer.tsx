'use client'

import * as Dialog from '@radix-ui/react-dialog'
import { motion, AnimatePresence } from 'motion/react'
import { useState, type ReactNode } from 'react'
import type { Alert, CorrelatedEvidenceRecord, LabelReview, TriageStatus } from '@/features/alerts/types'
import {
  ALERT_DISPLAY_ACTION_ALIASES,
  getAlertActionLabel,
  isActionableAttackClass,
  VERIFIED_LABEL_VALUES,
} from '@/features/alerts/contract'
import type { AlertAction, VerifiedLabel } from '@/features/alerts/contract'
import { useAlert, useTriageMutation, useActionMutation, useLabelReviewMutation } from '@/features/alerts/queries'
import { cn } from '@/lib/utils'
import { formatAlertDateTime, formatConfidenceLabel } from '@/lib/date-time'
import { PERMISSIONS, roleHasPermission } from '@/lib/auth/roles'
import { describeEvidenceRelationship } from '@/features/alerts/evidence'
import { ALERT_CONFIDENCE_HELP_TEXT, ALERT_CRS_SCORE_HELP_TEXT } from '@/features/alerts/help-text'
import { InfoDisclosure } from '@/components/ui/InfoDisclosure'

const ALERT_DETAIL_HELP = {
  recordId: 'The identifier assigned to this alert or traffic record. It identifies a record, not necessarily a separate client request.',
  time: 'The event time saved with this record and formatted for display. Older or incomplete records may not include every timestamp detail.',
  sourceIp: 'The source address saved with this record when available. Its origin and verification are shown separately; the address alone does not identify a person or prove trusted provenance.',
  request: 'The request method and path saved with this record when available. A dash means that part was not available in the stored details.',
  modelVersion: 'The model version captured with this classification, when recorded. “Not recorded” means CyberTrace cannot identify the historical version from this record.',
  preprocessing: 'The preprocessing version captured for preparing model input, when recorded. “Not recorded” means that provenance is unavailable here.',
  decisionReason: 'The reason code saved with the policy recommendation, displayed with underscores replaced by spaces. A dash means no reason was recorded.',
  evidenceBasis: 'A short display summary derived from the saved policy evidence context. It may summarize only part of the available context; a dash means none was recorded.',
  policyVersion: 'The policy configuration version saved with the recommendation, when available. A dash means the version was not recorded.',
  correlationId: 'Used to associate records that share this identifier. It does not prove separate requests, duplicates, a compromised source, or that records came from the same processing layer.',
  observedHttpStatus: 'The HTTP response status recorded by the producer when available. A status such as 403 does not by itself identify which component produced or enforced the response.',
  enforcementSource: 'Names the enforcing component only when that source was recorded. “Not recorded” means it is unknown here; an HTTP status alone cannot identify the enforcement layer.',
  relatedRecords: 'Lists up to 20 records returned by the correlation-ID lookup. Related rows may describe the same request or separate observations; one row does not necessarily mean one distinct client request.',
  transactionId: 'The transaction identifier assigned by ModSecurity for its WAF event. It helps locate that WAF evidence but does not by itself prove a match to a portal record.',
  ruleIds: 'Identifiers of ModSecurity/OWASP CRS rules recorded as matched for this WAF event. Missing IDs mean they were not available in this record.',
  ruleTags: 'Categories or metadata attached to matched ModSecurity/OWASP CRS rules. Tags describe those same rules; they are not separate proof of an attack.',
  host: 'The Host value is not available in this request-detail view. The dash means CyberTrace cannot show a recorded host here.',
  requestSourceIp: 'The source address stored for this request. Origin and verification are reported separately; an IP address alone does not establish identity or trusted provenance.',
  requestLine: 'Shows the method and path available in the record. The displayed HTTP/1.1 text is fixed by this view, not a protocol value captured from the request; missing method or path values appear as dashes.',
  queryString: 'Shows query input retained with the record when available; sensitive values may be redacted. If none appears, the original query may be absent or simply not retained.',
  startReview: 'Assigns you to review this detection and updates analyst triage status. It does not change the recorded action or the HTTP response.',
  resolve: 'Marks the analyst triage workflow as resolved. It does not show whether the request was blocked, throttled, or allowed.',
  falsePositive: 'Records an analyst assessment that this detection is a false positive. It does not change the request outcome or the saved action label.',
  escalate: 'Marks the detection for further analyst attention. Escalation is a workflow status, not an enforcement action.',
  saveBlocked: 'Saves Blocked as the record’s action label. It does not issue a WAF command or prove that the HTTP request was blocked.',
  saveThrottled: 'Saves Throttled as the record’s action label. It does not apply throttling or prove that the HTTP request was slowed.',
  saveAllowed: 'Saves Allowed as the record’s action label. It does not change a past response or prove that the request was allowed at runtime.',
} as const

const ALERT_DETAIL_LIST_LAYOUT_CLASS =
  'grid grid-cols-[minmax(0,96px)_20px_minmax(0,1fr)] gap-x-2 gap-y-2 ' +
  '[&>dt]:col-span-2 [&>dt]:grid [&>dt]:min-w-0 [&>dt]:grid-cols-[minmax(0,1fr)_20px] ' +
  '[&>dt]:items-center [&>dt]:gap-x-1 [&>dt>span:first-child]:min-w-0 [&>dt>span:first-child]:break-words ' +
  '[&>dd]:col-start-3 [&>dd]:min-w-0'

const ALERT_DETAIL_LIST_CLASS = `${ALERT_DETAIL_LIST_LAYOUT_CLASS} text-[12px] leading-4`
const ALERT_DETAIL_COMPACT_LIST_CLASS = `${ALERT_DETAIL_LIST_LAYOUT_CLASS} text-[10px] leading-4`

const ALERT_DETAIL_LABEL_CLASS =
  'grid grid-cols-[minmax(0,1fr)_20px] items-center gap-x-1 uppercase tracking-[0.08em] text-[var(--color-text-soft)]'

interface AlertDrawerProps {
  role?: unknown
  alert: Alert | null
  onClose: () => void
  onTriageUpdated?: (alert: Alert) => void
  onActionUpdated?: (alert: Alert) => void
  onReviewUpdated?: (alertId: string, review: LabelReview) => void
}

interface AlertDrawerContentProps extends AlertDrawerProps {
  detailLoading?: boolean
  detailError?: boolean
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

function isNewTriageStatus(status: TriageStatus | null | undefined): boolean {
  return status === 'new' || status == null
}

function formatCrsScore(score: number | null | undefined): string {
  if (score === null || score === undefined) return '—'
  return score.toFixed(2)
}

function formatSourceOrigin(value: string | null | undefined): string {
  if (!value) return 'Not recorded'
  const labels: Record<string, string> = {
    CLOUDFLARE_CONNECTING_IP: 'Cloudflare connecting IP',
    DIRECT_REMOTE_ADDR: 'Direct remote address',
    LEGACY_UNKNOWN: 'Unknown (legacy)',
  }
  return labels[value] ?? value
}

function formatSourceVerification(value: string | null | undefined): string {
  if (!value) return 'Not recorded'
  const labels: Record<string, string> = {
    VERIFIED: 'Verified',
    UNVERIFIED: 'Unverified',
    INVALID: 'Invalid',
    LEGACY_UNKNOWN: 'Unknown (legacy)',
  }
  return labels[value] ?? value
}

function hasCrsEvidence(record: Pick<Alert, 'crs_score' | 'crs_rule_ids' | 'matched_rule_tags'> | CorrelatedEvidenceRecord): boolean {
  return Boolean(
    (typeof record.crs_score === 'number' && record.crs_score > 0) ||
      record.crs_rule_ids?.some((ruleId) => ruleId.trim() && !['no-crs-match', 'unknown-rule'].includes(ruleId.trim().toLowerCase())) ||
      record.matched_rule_tags?.some((tag) => tag.trim())
  )
}

function formatPolicyReason(reason: string | null | undefined): string {
  return reason ? reason.replaceAll('_', ' ') : '—'
}

function formatPolicyEvidence(context: Record<string, unknown> | null | undefined): string {
  if (!context) return '—'
  if (context.strong_waf_evidence === true) return 'Strong CRS evidence'
  if (context.source_verified === true) return 'Verified source context'
  return 'Recorded evidence context'
}

function renderNotificationStatus(
  status: Alert['notification_status'],
  confidenceTier: Alert['confidence_level']
): ReactNode {
  const entries = Object.entries(status ?? {})
  if (entries.length === 0) {
    return confidenceTier === 'INFORMATIONAL' || confidenceTier === 'LOW' || confidenceTier === 'MEDIUM'
      ? 'Not applicable'
      : 'No outbox record'
  }
  return (
    <ul aria-label="Notification channel statuses" className="grid min-w-0 gap-1">
      {entries.map(([channel, value]) => (
        <li
          key={channel}
          className="grid min-w-0 grid-cols-[minmax(0,1fr)_auto] items-center gap-2"
        >
          <span className="min-w-0 capitalize text-[var(--color-text-secondary)]">{channel}</span>
          <span className="justify-self-end rounded border border-surface-border bg-surface-inset px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text-primary)]">
            {value.replaceAll('_', ' ')}
          </span>
        </li>
      ))}
    </ul>
  )
}

function AlertDrawerContent({ role, alert, onClose, onTriageUpdated, onActionUpdated, onReviewUpdated, detailLoading, detailError }: AlertDrawerContentProps) {
  const isActionableAlert = alert !== null && isActionableAttackClass(alert.prediction)
  const capturedRequestLine = alert
    ? `${alert.request_method ?? '—'} ${alert.request_path ?? '—'} HTTP/1.1`
    : ''
  const queryString = alert?.query_string?.trim() ?? ''
  const payloadSnippet = alert?.payload_snippet?.trim() ?? ''
  const additionalPayload = payloadSnippet && payloadSnippet !== capturedRequestLine
    ? payloadSnippet
    : ''
  const missingRequestDetailsMessage =
    alert?.ingest_source === 'portal_route_bridge'
      ? 'This portal request was inspected, but its submitted input is intentionally not saved with this traffic record.'
      : alert?.ingest_source === 'nginx_access_bridge'
        ? 'Access-log events do not retain query strings, so the original input is unavailable here.'
        : payloadSnippet
          ? 'No additional request data captured.'
          : 'No payload captured.'
  const canTriage = roleHasPermission(role, PERMISSIONS.ALERTS_TRIAGE)
  const canUpdateAction = roleHasPermission(
    role,
    PERMISSIONS.ALERTS_ACTION_UPDATE
  )
  const canManageTrainingFeedback = roleHasPermission(
    role,
    PERMISSIONS.TRAINING_FEEDBACK_MANAGE
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
    if (alert && isActionableAlert && !isPending) {
      mutate(
        { id: alert.alert_id, status },
        { onSuccess: (updatedAlert) => onTriageUpdated?.(updatedAlert) }
      )
    }
  }

  const handleStartReview = () => {
    if (alert && isActionableAlert && !isPending && isNewTriageStatus(displayStatus)) {
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
    if (alert && isActionableAlert && !isActionPending) {
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
    if (
      canManageTrainingFeedback &&
      alert &&
      isActionableAlert &&
      verifiedLabel &&
      !isLabelReviewPending
    ) {
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

  const triageLabel = isActionableAlert ? formatTriageLabel(displayStatus) : 'Traffic'
  const requestLine = [alert?.request_method ?? '—', alert?.request_path ?? '—'].join(' ')
  const confidenceLabel = alert
    ? formatConfidenceLabel(alert.confidence, alert.confidence_level)
    : '—'
  const crsRuleIds = alert?.crs_rule_ids?.length ? alert.crs_rule_ids.join(', ') : '—'
  const evidenceRelationship = alert
    ? describeEvidenceRelationship(alert)
    : null
  const hasOwnCrsEvidence = alert?.ingest_source === 'modsec_audit_bridge' && hasCrsEvidence(alert)
  const relatedWafRecords = (alert?.correlated_records ?? []).filter(
    (record) => record.ingest_source === 'modsec_audit_bridge' && hasCrsEvidence(record)
  )
  const hasCorrelatedCrsEvidence = hasOwnCrsEvidence || relatedWafRecords.length > 0

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
            <Dialog.Content
              asChild
              onEscapeKeyDown={(event) => {
                if (event.target instanceof Element && event.target.closest('[data-info-disclosure-open="true"]')) {
                  event.preventDefault()
                }
              }}
            >
              <motion.div
                className="fixed top-0 right-0 z-30 flex h-full w-full max-w-[420px] flex-col border-l border-surface-border bg-surface-card shadow-2xl"
                initial={{ x: '100%' }}
                animate={{ x: 0 }}
                exit={{ x: '100%' }}
                transition={{ duration: 0.25, ease: 'easeOut' }}
              >
                {/* Visually hidden title for screen readers */}
                <Dialog.Title className="sr-only">
                  Traffic details for {alert.prediction}
                </Dialog.Title>
                {/* Hidden description to satisfy Radix accessibility warnings */}
                <Dialog.Description className="sr-only">
                  Details for {alert.prediction} — {formatAlertDateTime(alert.timestamp)}. {isActionableAlert
                    ? 'Contains request details, WAF evidence, model classification, and role-appropriate detection review controls.'
                    : 'Contains the stored request and classification. Normal traffic has no analyst triage status.'}
                </Dialog.Description>

                {/* Header */}
                <div className="sticky top-0 z-10 flex items-start justify-between border-b border-surface-border bg-surface-card p-4">
                  <div className="min-w-0 space-y-3">
                    <p className="text-[11px] font-semibold uppercase tracking-[0.12em] text-[var(--color-text-secondary)]">
                      Traffic Details
                    </p>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className={cn(
                        'rounded-full border px-2 py-1 text-[12px] font-semibold',
                        alert.prediction === 'Normal'
                          ? 'border-severity-safe-border bg-severity-safe-bg text-severity-safe-text'
                          : 'border-action-border bg-action-bg text-action-accent'
                      )}>
                        {alert.prediction}
                      </span>
                      {isActionableAlert && (
                        <span className="rounded-full border border-action-border bg-action-bg px-2 py-1 text-[10px] font-medium uppercase tracking-[0.08em] text-action-accent">
                          {triageLabel}
                        </span>
                      )}
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
                        {displayAction
                          ? `Recorded: ${getAlertActionLabel(displayAction, alert.confidence_level, alert.prediction)}`
                          : 'No recorded action'}
                      </span>
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
                      aria-label="Close Traffic Details"
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
                  className="min-h-0 flex-1 overflow-y-auto p-3"
                >
                  <div className="grid content-start gap-3">
                  {detailLoading ? (
                    <p role="status" className="rounded-md border border-surface-border bg-surface-inset p-2 text-[11px] text-[var(--color-text-secondary)]">
                      Loading additional traffic details…
                    </p>
                  ) : null}
                  {detailError ? (
                    <p role="status" className="rounded-md border border-severity-blocked-border bg-severity-blocked-bg p-2 text-[11px] text-severity-blocked-text">
                      Additional traffic details could not be loaded. The record remains available.
                    </p>
                  ) : null}
                  <section className="rounded-lg border border-surface-border bg-surface-panel p-3">
                    <h3 className="mb-3 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                      Core Details
                    </h3>
                    <dl className={ALERT_DETAIL_LIST_CLASS}>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>{isActionableAlert ? 'Alert ID' : 'Traffic record ID'}</span>
                        <InfoDisclosure label={isActionableAlert ? 'Alert ID' : 'Traffic record ID'}>
                          {ALERT_DETAIL_HELP.recordId}
                        </InfoDisclosure>
                      </dt>
                      <dd className="font-mono text-[var(--color-text-primary)]">
                        {alert.alert_id}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Time</span>
                        <InfoDisclosure label="Time">{ALERT_DETAIL_HELP.time}</InfoDisclosure>
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {formatAlertDateTime(alert.timestamp)}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Source IP</span>
                        <InfoDisclosure label="Source IP">{ALERT_DETAIL_HELP.sourceIp}</InfoDisclosure>
                      </dt>
                      <dd className="font-mono text-[11px] text-[var(--color-accent-analytic)]">
                        {alert.source_ip ?? '—'}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Source IP origin</span>
                        <InfoDisclosure label="Source IP origin">
                          This identifies the address source accepted by the backend, such as a verified Cloudflare connecting IP or the direct remote address. It does not identify a person behind the address.
                        </InfoDisclosure>
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">{formatSourceOrigin(alert.source_provenance)}</dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Source IP verification</span>
                        <InfoDisclosure label="Source IP verification">
                          Verified means the configured Cloudflare tunnel checks accepted the connecting-IP evidence. Unverified means those checks did not establish trusted Cloudflare provenance; invalid means no valid source IP was accepted. Older records may have unknown metadata.
                        </InfoDisclosure>
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">{formatSourceVerification(alert.source_verification_status)}</dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Request</span>
                        <InfoDisclosure label="Request">{ALERT_DETAIL_HELP.request}</InfoDisclosure>
                      </dt>
                      <dd className="font-mono text-[11px] text-[var(--color-accent-analytic)] break-all">
                        {requestLine}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Confidence</span>
                        <InfoDisclosure label="Confidence">
                          {ALERT_CONFIDENCE_HELP_TEXT}
                        </InfoDisclosure>
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {confidenceLabel}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Model version</span>
                        <InfoDisclosure label="Model version">{ALERT_DETAIL_HELP.modelVersion}</InfoDisclosure>
                      </dt>
                      <dd className="font-mono text-[11px] text-[var(--color-text-primary)]">
                        {alert.model_version ?? 'Not recorded'}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Preprocessing</span>
                        <InfoDisclosure label="Preprocessing">{ALERT_DETAIL_HELP.preprocessing}</InfoDisclosure>
                      </dt>
                      <dd className="font-mono text-[11px] text-[var(--color-text-primary)]">
                        {alert.preprocessing_version ?? 'Not recorded'}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Policy decision</span>
                        <InfoDisclosure label="Policy decision">
                          This is the policy recommendation recorded for the event. Compare it with the saved action and observed HTTP status to review the available evidence.
                        </InfoDisclosure>
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {alert.policy_decision ?? 'No recommendation'}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Decision reason</span>
                        <InfoDisclosure label="Decision reason">{ALERT_DETAIL_HELP.decisionReason}</InfoDisclosure>
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {formatPolicyReason(alert.policy_decision_reason)}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Evidence basis</span>
                        <InfoDisclosure label="Evidence basis">{ALERT_DETAIL_HELP.evidenceBasis}</InfoDisclosure>
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {formatPolicyEvidence(alert.policy_evidence_context)}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Policy version</span>
                        <InfoDisclosure label="Policy version">{ALERT_DETAIL_HELP.policyVersion}</InfoDisclosure>
                      </dt>
                      <dd className="font-mono text-[11px] text-[var(--color-text-primary)]">
                        {alert.policy_version ?? '—'}
                      </dd>
                      <dt className="flex min-w-0 items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Notifications</span>
                        <InfoDisclosure label="Notifications" className="shrink-0">
                          <div className="grid gap-2">
                            <p>Shows the delivery status saved for each notification channel.</p>
                            <ul className="grid list-disc gap-1 pl-4">
                              <li><span className="font-semibold text-[var(--color-text-primary)]">Not applicable:</span> no notification status applies to this record.</li>
                              <li><span className="font-semibold text-[var(--color-text-primary)]">No outbox record:</span> no saved delivery record is available.</li>
                            </ul>
                            <p>Notification status does not show whether the request was allowed, throttled, or blocked.</p>
                          </div>
                        </InfoDisclosure>
                      </dt>
                      <dd className="min-w-0 text-[var(--color-text-primary)]">
                        {renderNotificationStatus(alert.notification_status, alert.confidence_level)}
                      </dd>
                    </dl>
                  </section>

                  <section className="rounded-lg border border-surface-border bg-surface-panel p-3">
                    <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                      Request correlation and observed outcome
                    </h3>
                    <dl className={ALERT_DETAIL_LIST_CLASS}>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Correlation ID</span>
                        <InfoDisclosure label="Correlation ID">{ALERT_DETAIL_HELP.correlationId}</InfoDisclosure>
                      </dt>
                      <dd className="break-all font-mono text-[11px] text-[var(--color-text-primary)]">
                        {alert.request_correlation_id ?? 'Not recorded'}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Observed HTTP status</span>
                        <InfoDisclosure label="Observed HTTP status">{ALERT_DETAIL_HELP.observedHttpStatus}</InfoDisclosure>
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        {alert.observed_http_status ?? 'Not recorded'}
                      </dd>
                      <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        <span>Enforcement source</span>
                        <InfoDisclosure label="Enforcement source">{ALERT_DETAIL_HELP.enforcementSource}</InfoDisclosure>
                      </dt>
                      <dd className="text-[var(--color-text-primary)]">
                        Not recorded
                      </dd>
                    </dl>
                    <p className="mt-2 text-[10px] leading-4 text-[var(--color-text-secondary)]">
                      An observed HTTP status records the response seen by the producer; it does not by itself identify which layer enforced it.
                    </p>
                    {alert.request_correlation_id ? (
                      <div className="mt-3 border-t border-surface-border pt-2">
                        <p className="grid grid-cols-[minmax(0,1fr)_20px] items-center gap-x-1 text-[9px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                          <span>Other records with this request ID (up to 20 shown)</span>
                          <InfoDisclosure label="Related records" className="shrink-0">{ALERT_DETAIL_HELP.relatedRecords}</InfoDisclosure>
                        </p>
                        {alert.correlated_records?.length ? (
                          <ul className="mt-2 space-y-2">
                            {alert.correlated_records.map((record) => (
                              <li key={record.id} className="rounded-md border border-surface-border bg-surface-inset p-2 text-[10px] leading-4">
                                <p className="font-medium text-[var(--color-text-primary)]">
                                  Record #{record.id} · {record.ingest_source ?? 'Unknown source'}
                                </p>
                                <dl className={`mt-1 ${ALERT_DETAIL_COMPACT_LIST_CLASS}`}>
                                  <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                    <span>Transaction</span>
                                    <InfoDisclosure label="Transaction ID">{ALERT_DETAIL_HELP.transactionId}</InfoDisclosure>
                                  </dt>
                                  <dd className="break-all font-mono text-[var(--color-text-secondary)]">
                                    {record.transaction_id ?? 'Not recorded'}
                                  </dd>
                                  <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                    <span>Classification</span>
                                  </dt>
                                  <dd className="text-[var(--color-text-secondary)]">
                                    {record.prediction ?? 'Not recorded'}
                                  </dd>
                                  <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                    <span>HTTP status</span>
                                    <InfoDisclosure label="Observed HTTP status">{ALERT_DETAIL_HELP.observedHttpStatus}</InfoDisclosure>
                                  </dt>
                                  <dd className="text-[var(--color-text-secondary)]">
                                    {record.observed_http_status ?? 'Not recorded'}
                                  </dd>
                                  {record.crs_rule_ids?.length ? (
                                    <>
                                      <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                        <span>CRS rules</span>
                                        <InfoDisclosure label="Rule IDs">{ALERT_DETAIL_HELP.ruleIds}</InfoDisclosure>
                                      </dt>
                                      <dd className="break-all font-mono text-[var(--color-text-secondary)]">
                                        {record.crs_rule_ids.join(', ')}
                                      </dd>
                                    </>
                                  ) : null}
                                </dl>
                              </li>
                            ))}
                          </ul>
                        ) : (
                          <p className="mt-1 text-[10px] text-[var(--color-text-secondary)]">
                            No other matching records were returned.
                          </p>
                        )}
                      </div>
                    ) : (
                      <p className="mt-2 text-[10px] text-[var(--color-text-secondary)]">
                        No request correlation ID was recorded; no cross-record join is asserted.
                      </p>
                    )}
                  </section>

                  <section className="rounded-lg border border-surface-border bg-surface-panel p-3">
                    <div className="mb-3 grid grid-cols-[minmax(0,1fr)_20px] items-center gap-x-1">
                      <h3 className="text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        WAF Evidence
                      </h3>
                      <InfoDisclosure label="WAF evidence" className="shrink-0">
                        Correlated ModSecurity/CRS records may include a transaction ID, matched rule IDs and tags, a score, and a producer-recorded HTTP status. The score and its matched rules are related WAF evidence; a missing CRS match does not by itself invalidate model evidence.
                      </InfoDisclosure>
                    </div>
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
                        {hasOwnCrsEvidence ? (
                        <dl className={ALERT_DETAIL_LIST_CLASS}>
                          <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                            <span>Transaction ID</span>
                            <InfoDisclosure label="Transaction ID">{ALERT_DETAIL_HELP.transactionId}</InfoDisclosure>
                          </dt>
                          <dd className="font-mono text-[11px] text-[var(--color-text-primary)] break-all">
                            {alert.transaction_id ?? '—'}
                          </dd>
                          <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                            Ingest source
                          </dt>
                          <dd className="text-[var(--color-text-primary)]">{alert.ingest_source ?? '—'}</dd>
                          <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                            <span>CRS score</span>
                            <InfoDisclosure label="CRS score">
                              {ALERT_CRS_SCORE_HELP_TEXT}
                            </InfoDisclosure>
                          </dt>
                          <dd className="text-severity-blocked-text">{formatCrsScore(alert.crs_score)}</dd>
                          <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                            <span>Rule IDs</span>
                            <InfoDisclosure label="Rule IDs">{ALERT_DETAIL_HELP.ruleIds}</InfoDisclosure>
                          </dt>
                          <dd className="font-mono text-[11px] text-[var(--color-text-primary)] break-all">{crsRuleIds}</dd>
                          {alert.matched_rule_tags?.length ? (
                            <>
                              <dt className="flex items-center gap-1 text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                <span>Rule tags</span>
                                <InfoDisclosure label="Rule tags">{ALERT_DETAIL_HELP.ruleTags}</InfoDisclosure>
                              </dt>
                              <dd className="break-all font-mono text-[10px] leading-4 text-[var(--color-text-primary)]">
                                {alert.matched_rule_tags.join(', ')}
                              </dd>
                            </>
                          ) : null}
                        </dl>
                        ) : null}
                        {hasOwnCrsEvidence && alert.matched_rule_messages?.length ? (
                          <div className="mt-3 border-t border-surface-border pt-2">
                            <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                              Rule messages
                            </p>
                            <ul className="mt-1 list-disc space-y-1 pl-4 text-[10px] leading-4 text-[var(--color-text-primary)]">
                              {alert.matched_rule_messages.map((message, index) => (
                                <li key={`${message}-${index}`}>{message}</li>
                              ))}
                            </ul>
                          </div>
                        ) : null}
                        {relatedWafRecords.map((record) => (
                          <div key={record.id} className="mt-3 border-t border-surface-border pt-2 text-[10px] leading-4">
                            <p className="font-semibold text-[var(--color-text-primary)]">
                              Correlated ModSecurity record #{record.id}
                            </p>
                            <dl className={`mt-1 ${ALERT_DETAIL_COMPACT_LIST_CLASS}`}>
                              <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                <span>Transaction</span>
                                <InfoDisclosure label="Transaction ID">{ALERT_DETAIL_HELP.transactionId}</InfoDisclosure>
                              </dt>
                              <dd className="break-all font-mono text-[var(--color-text-secondary)]">
                                {record.transaction_id ?? 'Not recorded'}
                              </dd>
                              <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                <span>CRS score</span>
                                <InfoDisclosure label="CRS score">{ALERT_CRS_SCORE_HELP_TEXT}</InfoDisclosure>
                              </dt>
                              <dd className="text-[var(--color-text-secondary)]">
                                {formatCrsScore(record.crs_score)}
                              </dd>
                              <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                <span>HTTP status</span>
                                <InfoDisclosure label="Observed HTTP status">{ALERT_DETAIL_HELP.observedHttpStatus}</InfoDisclosure>
                              </dt>
                              <dd className="text-[var(--color-text-secondary)]">
                                {record.observed_http_status ?? 'Not recorded'}
                              </dd>
                              {record.crs_rule_ids?.length ? (
                                <>
                                  <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                    <span>Rule IDs</span>
                                    <InfoDisclosure label="Rule IDs">{ALERT_DETAIL_HELP.ruleIds}</InfoDisclosure>
                                  </dt>
                                  <dd className="break-all font-mono text-[var(--color-text-secondary)]">
                                    {record.crs_rule_ids.join(', ')}
                                  </dd>
                                </>
                              ) : null}
                              {record.matched_rule_tags?.length ? (
                                <>
                                  <dt className="text-[9px] uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                                    <span>Rule tags</span>
                                    <InfoDisclosure label="Rule tags">{ALERT_DETAIL_HELP.ruleTags}</InfoDisclosure>
                                  </dt>
                                  <dd className="break-all font-mono text-[var(--color-text-secondary)]">
                                    {record.matched_rule_tags.join(', ')}
                                  </dd>
                                </>
                              ) : null}
                            </dl>
                          </div>
                        ))}
                      </>
                    )}
                  </section>

                  <section>
                    <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                      Request details
                    </h3>
                    <div className="max-h-44 overflow-auto rounded-lg border border-surface-border bg-surface-inset">
                      <div className="grid grid-cols-2 gap-2 border-b border-surface-border px-3 py-2 text-[10px]">
                        <div className="min-w-0">
                          <p className={ALERT_DETAIL_LABEL_CLASS}>
                            <span>Host</span>
                            <InfoDisclosure label="Host" className="shrink-0">{ALERT_DETAIL_HELP.host}</InfoDisclosure>
                          </p>
                          <p className="font-mono text-[var(--color-text-primary)]">—</p>
                        </div>
                        <div className="min-w-0">
                          <p className={ALERT_DETAIL_LABEL_CLASS}>
                            <span>Source-IP</span>
                            <InfoDisclosure label="Source IP" className="shrink-0">{ALERT_DETAIL_HELP.requestSourceIp}</InfoDisclosure>
                          </p>
                          <p className="font-mono text-[var(--color-accent-analytic)]">{alert.source_ip ?? '—'}</p>
                        </div>
                      </div>
                      <div className="grid gap-3 p-3 text-[10px]">
                        <div>
                          <p className={ALERT_DETAIL_LABEL_CLASS}>
                            <span>Request method/path/protocol</span>
                            <InfoDisclosure label="Request method/path/protocol" className="shrink-0">
                              {ALERT_DETAIL_HELP.requestLine}
                            </InfoDisclosure>
                          </p>
                          <pre className="mt-1 whitespace-pre-wrap break-all font-mono leading-[1.6] text-[var(--color-text-secondary)]">
                            <span className="text-severity-blocked-text">{alert.request_method ?? '—'}</span>{' '}
                            <span className="text-severity-high-text">{alert.request_path ?? '—'}</span>{' '}
                            <span className="text-[var(--color-text-secondary)]">HTTP/1.1</span>
                          </pre>
                        </div>
                        {queryString ? (
                          <div>
                            <p className={ALERT_DETAIL_LABEL_CLASS}>
                              <span>Captured query string (sensitive values redacted):</span>
                              <InfoDisclosure label="Captured query string" className="shrink-0">
                                {ALERT_DETAIL_HELP.queryString}
                              </InfoDisclosure>
                            </p>
                            <pre className="mt-1 whitespace-pre-wrap break-all font-mono leading-[1.6] text-[var(--color-text-primary)]">
                              {queryString}
                            </pre>
                          </div>
                        ) : null}
                        {additionalPayload ? (
                          <pre className="whitespace-pre-wrap break-all font-mono leading-[1.6] text-[var(--color-text-primary)]">
                            {additionalPayload}
                          </pre>
                        ) : null}
                        {!queryString ? (
                          <div>
                            <p className={ALERT_DETAIL_LABEL_CLASS}>
                              <span>Request input</span>
                              <InfoDisclosure label="Captured query string" className="shrink-0">
                                {ALERT_DETAIL_HELP.queryString}
                              </InfoDisclosure>
                            </p>
                            {!additionalPayload ? (
                              <p className="mt-1 leading-[1.6] text-[var(--color-text-soft)]">
                                {missingRequestDetailsMessage}
                              </p>
                            ) : null}
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </section>

                  {isActionableAlert && canManageTrainingFeedback && (
                    <section className="rounded-lg border border-surface-border bg-surface-panel p-3">
                      <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                        Training feedback
                      </h3>
                      <p className="mb-2 text-[11px] leading-4 text-[var(--color-text-secondary)]">
                        Add a correct label for training review. The current model is not changed automatically.
                      </p>
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
                          <option value="">Select the correct class</option>
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
                      {alert.label_review && (
                        <p className="mt-2 text-[10px] text-[var(--color-text-secondary)]">
                          Latest: {alert.label_review.verified_label} ({alert.label_review.approval_state.replaceAll('_', ' ')}) by {alert.label_review.reviewer_id} at {formatAlertDateTime(alert.label_review.reviewed_at)}
                        </p>
                      )}
                    </section>
                  )}

                  <section>
                    <div className="grid gap-4 md:grid-cols-2">
                      <div className="rounded-lg border border-surface-border bg-surface-panel p-3">
                        <h3 className="mb-2 text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                          Review &amp; triage
                        </h3>
                        {!isActionableAlert ? (
                          <p className="text-[11px] leading-4 text-[var(--color-text-secondary)]">
                            Normal traffic has no analyst triage workflow.
                          </p>
                        ) : canTriage ? (
                        <div className="flex flex-col gap-1.5">
                          {isNewTriageStatus(displayStatus) ? (
                            <>
                              <p className="mb-1 text-[11px] leading-4 text-[var(--color-text-secondary)]">
                                Assign yourself to this alert before reviewing.
                              </p>
                              <div className="flex items-center gap-1.5">
                                <button
                                  type="button"
                                  aria-label="Start Review"
                                  disabled={isPending}
                                  onClick={handleStartReview}
                                  className={cn(
                                    'flex min-w-0 flex-1 items-center justify-between rounded-md border border-action-border bg-action-bg px-2.5 py-1.5 text-left text-[11px] font-medium text-action-accent transition-colors hover:bg-action-bg/70',
                                    isPending && 'cursor-not-allowed opacity-50'
                                  )}
                                >
                                  <span>Start Review</span>
                                  {isPending ? <span>Updating...</span> : <span>→</span>}
                                </button>
                                <InfoDisclosure label="Start Review" className="shrink-0">{ALERT_DETAIL_HELP.startReview}</InfoDisclosure>
                              </div>
                            </>
                          ) : null}
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              disabled={isPending}
                              onClick={() => handleVerdictClick('resolved')}
                              className={cn(
                                'flex min-w-0 flex-1 items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                                displayStatus === 'resolved'
                                  ? 'border-severity-safe-border bg-severity-safe-bg text-severity-safe-text'
                                  : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                                isPending && 'cursor-not-allowed opacity-50'
                              )}
                            >
                              <span>Resolve</span>
                              {isPending && displayStatus === 'resolved' ? <span>Updating...</span> : <span>→</span>}
                            </button>
                            <InfoDisclosure label="Resolve" className="shrink-0">{ALERT_DETAIL_HELP.resolve}</InfoDisclosure>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              disabled={isPending}
                              onClick={() => handleVerdictClick('false_positive')}
                              className={cn(
                                'flex min-w-0 flex-1 items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                                displayStatus === 'false_positive'
                                  ? 'border-action-border bg-action-bg text-action-accent'
                                  : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                                isPending && 'cursor-not-allowed opacity-50'
                              )}
                            >
                              <span>False Positive</span>
                              {isPending && displayStatus === 'false_positive' ? <span>Updating...</span> : <span>→</span>}
                            </button>
                            <InfoDisclosure label="False Positive" className="shrink-0">{ALERT_DETAIL_HELP.falsePositive}</InfoDisclosure>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <button
                              type="button"
                              disabled={isPending}
                              onClick={() => handleVerdictClick('escalated')}
                              className={cn(
                                'flex min-w-0 flex-1 items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                                displayStatus === 'escalated'
                                  ? 'border-severity-high-border bg-severity-high-bg text-severity-high-text'
                                  : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                                isPending && 'cursor-not-allowed opacity-50'
                              )}
                            >
                              <span>Escalate</span>
                              {isPending && displayStatus === 'escalated' ? <span>Updating...</span> : <span>→</span>}
                            </button>
                            <InfoDisclosure label="Escalate" className="shrink-0">{ALERT_DETAIL_HELP.escalate}</InfoDisclosure>
                          </div>
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
                          Recorded action label
                        </h3>
                        <p className="mb-2 text-[11px] leading-4 text-[var(--color-text-secondary)]">
                          This label may come from the confidence policy or a manual update. Saving it changes the alert record only; it does not send a WAF command or confirm the HTTP response.
                        </p>
                        {isActionableAlert && canUpdateAction ? (
                        <div className="flex flex-col gap-1.5">
                      <p className="text-[9px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-soft)]">
                        Update action label
                      </p>
                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          disabled={isActionPending}
                          onClick={() => handleActionClick('BLOCKED')}
                          className={cn(
                            'flex min-w-0 flex-1 items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                            displayAction === 'BLOCKED'
                              ? 'border-severity-high-border bg-severity-high-bg text-severity-high-text'
                              : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                            isActionPending && 'cursor-not-allowed opacity-50'
                          )}
                        >
                          {isActionPending && displayAction === 'BLOCKED' ? (
                            <span>Saving…</span>
                          ) : (
                            <>
                              <span>Save as {ALERT_DISPLAY_ACTION_ALIASES.BLOCKED}</span>
                              <span>→</span>
                            </>
                          )}
                        </button>
                        <InfoDisclosure label="Save as Blocked" className="shrink-0">{ALERT_DETAIL_HELP.saveBlocked}</InfoDisclosure>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          disabled={isActionPending}
                          onClick={() => handleActionClick('THROTTLED')}
                          className={cn(
                            'flex min-w-0 flex-1 items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                            displayAction === 'THROTTLED'
                              ? 'border-severity-blocked-border bg-severity-blocked-bg text-severity-blocked-text'
                              : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                            isActionPending && 'cursor-not-allowed opacity-50'
                          )}
                        >
                          {isActionPending && displayAction === 'THROTTLED' ? (
                            <span>Saving…</span>
                          ) : (
                            <>
                              <span>Save as {ALERT_DISPLAY_ACTION_ALIASES.THROTTLED}</span>
                              <span>→</span>
                            </>
                          )}
                        </button>
                        <InfoDisclosure label="Save as Throttled" className="shrink-0">{ALERT_DETAIL_HELP.saveThrottled}</InfoDisclosure>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <button
                          type="button"
                          disabled={isActionPending}
                          onClick={() => handleActionClick('ALLOWED')}
                          className={cn(
                            'flex min-w-0 flex-1 items-center justify-between rounded-md border px-2.5 py-1.5 text-left text-[11px] font-medium transition-colors',
                            displayAction === 'ALLOWED'
                              ? 'border-severity-safe-border bg-severity-safe-bg text-severity-safe-text'
                              : 'border-surface-border bg-surface-card text-[var(--color-text-primary)] hover:bg-surface-inset',
                            isActionPending && 'cursor-not-allowed opacity-50'
                          )}
                        >
                          {isActionPending && displayAction === 'ALLOWED' ? (
                            <span>Saving…</span>
                          ) : (
                            <>
                              <span>Save as {ALERT_DISPLAY_ACTION_ALIASES.ALLOWED}</span>
                              <span>→</span>
                            </>
                          )}
                        </button>
                        <InfoDisclosure label="Save as Allowed" className="shrink-0">{ALERT_DETAIL_HELP.saveAllowed}</InfoDisclosure>
                      </div>
                        </div>
                        ) : (
                          <p className="text-[11px] text-[var(--color-text-secondary)]">
                            {isActionableAlert
                              ? 'Action updates require Admin.'
                              : displayAction
                                ? `Recorded action label: ${getAlertActionLabel(displayAction, alert.confidence_level)}.`
                                : 'No action was recorded.'}
                          </p>
                        )}
                        {isActionError && (
                          <p role="alert" className="mt-2 text-[11px] text-severity-high-text">
                            Action label could not be saved. Please retry.
                          </p>
                        )}
                        <details className="mt-3 border-t border-surface-border pt-2">
                          <summary className="cursor-pointer text-[10px] font-semibold uppercase tracking-[0.08em] text-[var(--color-text-secondary)]">
                            Action change history
                          </summary>
                          {alert.action_history?.length ? (
                            <ol className="mt-2 space-y-2">
                              {alert.action_history.map((entry) => (
                                <li key={entry.id} className="rounded-md border border-surface-border bg-surface-inset p-2 text-[10px] leading-4">
                                  <p className="font-medium text-[var(--color-text-primary)]">
                                    {entry.previous_action ?? 'No previous action'} → {entry.new_action}
                                  </p>
                                  <p className="mt-1 text-[var(--color-text-secondary)]">
                                    {entry.actor_id} · {formatAlertDateTime(entry.changed_at)}
                                  </p>
                                  {entry.reason ? <p className="mt-1 text-[var(--color-text-secondary)]">{entry.reason}</p> : null}
                                </li>
                              ))}
                            </ol>
                          ) : (
                            <p className="mt-2 text-[10px] text-[var(--color-text-secondary)]">
                              No history entries are available. Changes made before action history was introduced may not be recorded here.
                            </p>
                          )}
                        </details>
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

export function AlertDrawer(props: AlertDrawerProps) {
  const detailId = props.alert && isActionableAttackClass(props.alert.prediction)
    ? props.alert.alert_id
    : null
  const { data: detailAlert, isPending, isError } = useAlert(detailId)
  const alert = props.alert && detailAlert?.alert_id === props.alert.alert_id
    ? { ...props.alert, ...detailAlert }
    : props.alert
  return (
    <AlertDrawerContent
      key={props.alert?.alert_id ?? 'closed'}
      {...props}
      alert={alert}
      detailLoading={detailId !== null && isPending}
      detailError={detailId !== null && isError}
    />
  )
}
