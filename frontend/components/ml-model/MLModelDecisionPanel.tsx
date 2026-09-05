'use client'

import { useState } from 'react'
import type { RetrainingRunDetail } from '@/features/ml-model/types'
import type { RetrainingDecision } from '@/features/ml-model/contract'
import styles from './MLModelWorkspace.module.css'

interface Props {
  run: RetrainingRunDetail
  canRun: boolean
  canDecide: boolean
  canDeploy: boolean
  actionsDisabled: boolean
  decisionPending: boolean
  deployPending: boolean
  rollbackPending: boolean
  retryPending: boolean
  onDecision: (decision: RetrainingDecision, reason: string | null) => Promise<void>
  onDeploy: () => Promise<void>
  onRollback: (reason: string) => Promise<void>
  onRetry: () => Promise<void>
  actionError?: string | null
}

function safeStateHeading(state: RetrainingRunDetail['state']): string {
  switch (state) {
    case 'QUARANTINED_FOR_REVIEW':
      return 'Quarantined for review'
    case 'failed':
      return 'Worker failed'
    case 'RETRYABLE_FAILED':
      return 'Retryable worker failure'
    case 'RECOVERY_REQUIRED':
      return 'Deployment recovery required'
    case 'NOT_ENOUGH_EVIDENCE':
      return 'Not enough evidence'
    case 'SKIPPED_NO_APPROVED_DATA':
      return 'No approved data available'
    default:
      return 'Run status'
  }
}

function safeNextAction(state: RetrainingRunDetail['state']): string {
  switch (state) {
    case 'QUARANTINED_FOR_REVIEW':
      return 'Review approved labels and export limits before requesting another run.'
    case 'failed':
    case 'RETRYABLE_FAILED':
      return 'Keep the active model and inspect the manifest before retrying.'
    case 'RECOVERY_REQUIRED':
      return 'Reconcile the durable staging pointer and explicitly roll back to the known-good version.'
    case 'NOT_ENOUGH_EVIDENCE':
      return 'Collect sufficient native evaluation evidence before making a candidate decision.'
    case 'SKIPPED_NO_APPROVED_DATA':
      return 'Approve eligible verified reviews before requesting retraining.'
    default:
      return 'Review the run evidence and state before taking the next action.'
  }
}

function isDecisionState(state: RetrainingRunDetail['state']): boolean {
  return state === 'pending_approval'
}

export function MLModelDecisionPanel({
  run,
  canRun,
  canDecide,
  canDeploy,
  actionsDisabled,
  decisionPending,
  deployPending,
  rollbackPending,
  retryPending,
  onDecision,
  onDeploy,
  onRollback,
  onRetry,
  actionError,
}: Props) {
  const [reason, setReason] = useState('')
  const [reasonError, setReasonError] = useState<string | null>(null)

  const hasCandidateEvidence = Boolean(
    run.candidate_model_version &&
      run.candidate_model_digest &&
      run.evaluation_digest &&
      (run.evidence_status === 'NATIVE' || run.evidence_status === 'VERIFIED')
  )
  const approvalEvidenceReady = Boolean(
    hasCandidateEvidence &&
      run.evidence_summary.evaluation_status === 'PASS' &&
      run.evidence_summary.comparison_status === 'PASS'
  )

  const submitDecision = async (decision: RetrainingDecision) => {
    const trimmedReason = reason.trim()
    if ((decision === 'hold' || decision === 'reject') && !trimmedReason) {
      setReasonError('A reason is required to hold or reject a candidate.')
      return
    }
    setReasonError(null)

    if (decision === 'approve') {
      if (!approvalEvidenceReady) {
        setReasonError('Approval is unavailable until all evidence gates pass.')
        return
      }
      if (!window.confirm('Approve this candidate for explicit local staging only?')) return
    }

    await onDecision(decision, trimmedReason || null)
  }

  if (isDecisionState(run.state)) {
    if (!canDecide) {
      return (
        <section className={styles.decisionSection} aria-labelledby="ml-model-decision-heading">
          <div className={styles.sectionHeaderCompact}>
            <div>
              <p className={styles.eyebrow}>Approval boundary</p>
              <h2 id="ml-model-decision-heading" className={styles.sectionTitle}>
                Candidate review is pending
              </h2>
            </div>
            <span className={styles.statusBadge}>OWNER ONLY</span>
          </div>
          <p className={styles.sectionDescription}>
            This account can inspect the candidate evidence but cannot approve, hold, or reject it.
          </p>
        </section>
      )
    }

    return (
      <section className={styles.decisionSection} aria-labelledby="ml-model-decision-heading">
        <div className={styles.sectionHeaderCompact}>
          <div>
            <p className={styles.eyebrow}>Approval boundary</p>
            <h2 id="ml-model-decision-heading" className={styles.sectionTitle}>
              Candidate decision
            </h2>
          </div>
          <span className={styles.statusBadge}>PENDING APPROVAL</span>
        </div>
        <p className={styles.sectionDescription}>
          A decision is bound to this run&apos;s candidate, evaluation, and active-model fingerprints. Approval does not deploy automatically.
        </p>
        <label className={styles.fieldLabel} htmlFor="ml-model-decision-reason">
          Decision reason
        </label>
        <textarea
          id="ml-model-decision-reason"
          aria-label="Decision reason"
          className={styles.reasonInput}
          value={reason}
          onChange={(event) => setReason(event.target.value)}
          maxLength={500}
          placeholder="Record the evidence-based decision context"
          disabled={actionsDisabled || decisionPending}
        />
        {reasonError && <p className={styles.formError} role="alert">{reasonError}</p>}
        {actionError && <p className={styles.formError} role="alert">{actionError}</p>}
        <div className={styles.decisionActions}>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={() => void submitDecision('approve').catch(() => undefined)}
            disabled={actionsDisabled || decisionPending || !approvalEvidenceReady}
          >
            Approve candidate
          </button>
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => void submitDecision('hold').catch(() => undefined)}
            disabled={actionsDisabled || decisionPending}
          >
            Hold for next cycle
          </button>
          <button
            type="button"
            className={styles.dangerButton}
            onClick={() => void submitDecision('reject').catch(() => undefined)}
            disabled={actionsDisabled || decisionPending}
          >
            Reject candidate
          </button>
        </div>
      </section>
    )
  }

  if (run.state === 'held' || run.state === 'rejected') {
    return (
      <section className={styles.decisionSection} aria-labelledby="ml-model-decision-heading">
        <div className={styles.sectionHeaderCompact}>
          <div>
            <p className={styles.eyebrow}>Decision recorded</p>
            <h2 id="ml-model-decision-heading" className={styles.sectionTitle}>
              Candidate {run.state}
            </h2>
          </div>
          <span className={styles.statusBadge}>{run.state.toUpperCase()}</span>
        </div>
        <p className={styles.retentionCallout}>
          Verified samples were retained for the next retraining cycle. Holding or rejecting this candidate did not remove approved training data.
        </p>
      </section>
    )
  }

  if (run.state === 'approved') {
    return (
      <section className={styles.decisionSection} aria-labelledby="ml-model-decision-heading">
        <div className={styles.sectionHeaderCompact}>
          <div>
            <p className={styles.eyebrow}>Explicit deployment boundary</p>
            <h2 id="ml-model-decision-heading" className={styles.sectionTitle}>
              Candidate approved
            </h2>
          </div>
          <span className={styles.statusBadge}>APPROVED</span>
        </div>
        <p className={styles.sectionDescription}>
          The candidate is approved for local staging only. Production activation is not part of this workspace.
        </p>
        {canDeploy ? (
          <button
            type="button"
            className={styles.primaryButton}
            onClick={() => {
              if (window.confirm('Deploy this approved candidate to local staging?')) {
                void onDeploy().catch(() => undefined)
              }
            }}
            disabled={actionsDisabled || deployPending}
          >
            Deploy to local staging
          </button>
        ) : (
          <p className={styles.sectionDescription}>Local staging deployment requires Owner permission.</p>
        )}
        {actionError && <p className={styles.formError} role="alert">{actionError}</p>}
      </section>
    )
  }

  if (run.state === 'deployed') {
    return (
      <section className={styles.decisionSection} aria-labelledby="ml-model-decision-heading">
        <div className={styles.sectionHeaderCompact}>
          <div>
            <p className={styles.eyebrow}>Local staging</p>
            <h2 id="ml-model-decision-heading" className={styles.sectionTitle}>
              Candidate deployed to local staging
            </h2>
          </div>
          <span className={styles.statusBadge}>DEPLOYED</span>
        </div>
        <p className={styles.sectionDescription}>
          Load verification remains an explicit operational step. Rollback restores the known-good staging version.
        </p>
        {canDeploy ? (
          <button
            type="button"
            className={styles.dangerButton}
            onClick={() => {
              if (window.confirm('Roll back local staging to the previous known-good version?')) {
                void onRollback('Owner requested rollback from ML Deployment.').catch(() => undefined)
              }
            }}
            disabled={actionsDisabled || rollbackPending}
          >
            Roll back local staging
          </button>
        ) : (
          <p className={styles.sectionDescription}>Local staging rollback requires Owner permission.</p>
        )}
        {actionError && <p className={styles.formError} role="alert">{actionError}</p>}
      </section>
    )
  }

  if (run.state === 'RECOVERY_REQUIRED') {
    return (
      <section className={styles.decisionSection} aria-labelledby="ml-model-decision-heading">
        <div className={styles.sectionHeaderCompact}>
          <div>
            <p className={styles.eyebrow}>Safe recovery boundary</p>
            <h2 id="ml-model-decision-heading" className={styles.sectionTitle}>
              Deployment state needs reconciliation
            </h2>
          </div>
          <span className={styles.statusBadge}>RECOVERY REQUIRED</span>
        </div>
        <p className={styles.sectionDescription}>
          The filesystem or loaded model changed while audit state was being recorded. The active model is not assumed from the run record.
        </p>
        {canDeploy ? (
          <button
            type="button"
            className={styles.dangerButton}
            onClick={() => {
              if (window.confirm('Roll back local staging to the recorded known-good version?')) {
                void onRollback('Reconcile the recoverable local staging state.').catch(() => undefined)
              }
            }}
            disabled={actionsDisabled || rollbackPending}
          >
            Reconcile with rollback
          </button>
        ) : (
          <p className={styles.sectionDescription}>Recovery requires Owner permission.</p>
        )}
        {actionError && <p className={styles.formError} role="alert">{actionError}</p>}
      </section>
    )
  }

  if (['QUARANTINED_FOR_REVIEW', 'failed', 'RETRYABLE_FAILED', 'NOT_ENOUGH_EVIDENCE', 'SKIPPED_NO_APPROVED_DATA'].includes(run.state)) {
    return (
      <section className={styles.decisionSection} aria-labelledby="ml-model-decision-heading">
        <div className={styles.sectionHeaderCompact}>
          <div>
            <p className={styles.eyebrow}>Safe next action</p>
            <h2 id="ml-model-decision-heading" className={styles.sectionTitle}>
              {safeStateHeading(run.state)}
            </h2>
          </div>
          <span className={styles.statusBadge}>{run.error_code ?? run.state}</span>
        </div>
        <p className={styles.sectionDescription}>{safeNextAction(run.state)}</p>
        <p className={styles.evidenceNotice}>The active model was not changed by this run.</p>
        {run.retry_available && canRun && (
          <button
            type="button"
            className={styles.secondaryButton}
            onClick={() => void onRetry().catch(() => undefined)}
            disabled={actionsDisabled || retryPending}
          >
            {retryPending ? 'Retrying…' : 'Retry run'}
          </button>
        )}
      </section>
    )
  }

  return null
}
