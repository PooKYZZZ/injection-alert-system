'use client'

import { useState } from 'react'
import { PERMISSIONS, roleHasPermission } from '@/lib/auth/roles'
import {
  useDecisionRetrainingMutation,
  useDeployRetrainingMutation,
  useExportRetrainingMutation,
  useMLModelRun,
  useMLModelRuns,
  useMLModelSummary,
  useRollbackRetrainingMutation,
  useRetryRetrainingMutation,
  useStartRetrainingMutation,
} from '@/features/ml-model/queries'
import type { RetrainingDecision } from '@/features/ml-model/contract'
import { isRetrainingRunActive } from '@/features/ml-model/contract'
import type {
  RetrainingExportResult,
  RetrainingRunStart,
} from '@/features/ml-model/types'
import { MLModelComparisonPanel } from './MLModelComparisonPanel'
import { MLModelDecisionPanel } from './MLModelDecisionPanel'
import { MLModelOverviewSection } from './MLModelOverviewSection'
import { MLModelRunsTable } from './MLModelRunsTable'
import styles from './MLModelWorkspace.module.css'

interface Props {
  role?: unknown
}

function errorMessage(error: unknown): string | null {
  if (!(error instanceof Error) || !error.message) return null
  const message = error.message.slice(0, 240)
  if (/model_input_text|http_request|API_SECRET_KEY|INTERNAL_API_KEY|traceback|stack trace/i.test(message)) {
    return 'The retraining operation failed safely. Review the run state and manifest.'
  }
  return message
}

function isCapabilityUnavailable(error: unknown): boolean {
  return (
    typeof error === 'object' &&
    error !== null &&
    'status' in error &&
    (error as { status?: unknown }).status === 503
  )
}

function displayState(state: RetrainingRunStart['state']): string {
  return state.replaceAll('_', ' ')
}

function startNotice(result: RetrainingRunStart | undefined): string {
  if (!result) {
    return 'Retraining request was accepted. Review the run record for its current state.'
  }
  if (result.created) {
    return result.state === 'queued'
      ? 'Retraining request submitted. The worker will progress outside the request lifecycle.'
      : `Retraining request reached ${displayState(result.state)} at ${result.stage}.`
  }
  if (result.state === 'RETRYABLE_FAILED') {
    return 'A matching run already exists and remains retryable. No duplicate run was created.'
  }
  if (
    result.state === 'NOT_ENOUGH_EVIDENCE' ||
    result.state === 'SKIPPED_NO_APPROVED_DATA' ||
    result.state === 'failed'
  ) {
    return `A matching run already ended in ${displayState(result.state)}. No duplicate run was created.`
  }
  return `A matching run is already ${displayState(result.state)}. No duplicate run was created.`
}

function exportNotice(result: RetrainingExportResult | undefined): string {
  if (!result) return 'Approved sample export completed. Review its manifest and status.'
  if (result.status === 'QUARANTINED_FOR_REVIEW') {
    return `Approved sample export was quarantined for review (${result.exported_count} exported, ${result.rejected_count} rejected). No training run was started.`
  }
  if (result.status === 'EMPTY') {
    return 'No eligible approved samples were exported. Existing approved samples remain reusable.'
  }
  return `Approved sample export is ready (${result.exported_count} samples, ${result.rejected_count} rejected).`
}

export function MLModelWorkspace({ role }: Props) {
  const summaryQuery = useMLModelSummary()
  const runsQuery = useMLModelRuns()
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const startMutation = useStartRetrainingMutation()
  const exportMutation = useExportRetrainingMutation()
  const decisionMutation = useDecisionRetrainingMutation()
  const deployMutation = useDeployRetrainingMutation()
  const rollbackMutation = useRollbackRetrainingMutation()
  const retryMutation = useRetryRetrainingMutation()

  const summary = summaryQuery.data
  const runs = runsQuery.data?.runs ?? []
  const selectedRunIdForView =
    selectedRunId && runs.some((run) => run.run_id === selectedRunId)
      ? selectedRunId
      : runs[0]?.run_id ?? null

  const detailQuery = useMLModelRun(selectedRunIdForView ?? '')
  const selectedDetail =
    detailQuery.data?.run_id === selectedRunIdForView ? detailQuery.data : null

  const canRun = roleHasPermission(role, PERMISSIONS.ML_MODEL_RUN)
  const canDecide = roleHasPermission(role, PERMISSIONS.ML_MODEL_APPROVE)
  const canDeploy = roleHasPermission(role, PERMISSIONS.ML_MODEL_DEPLOY)
  const runInProgress = Boolean(summary?.run_in_progress || runs.some((run) => isRetrainingRunActive(run.state)))
  const mutationsBusy =
    startMutation.isPending ||
    exportMutation.isPending ||
    decisionMutation.isPending ||
    deployMutation.isPending ||
    rollbackMutation.isPending ||
    retryMutation.isPending

  const actionError =
    errorMessage(startMutation.error) ??
    errorMessage(exportMutation.error) ??
    errorMessage(decisionMutation.error) ??
    errorMessage(deployMutation.error) ??
    errorMessage(rollbackMutation.error) ??
    errorMessage(retryMutation.error)

  if (summaryQuery.isPending || runsQuery.isPending) {
    return (
      <div className={styles.loadingWrap} role="status">
        <strong>Loading Model Operations</strong>
        <span>Loading safe run and evidence state…</span>
      </div>
    )
  }

  if (summaryQuery.isError || runsQuery.isError || !summary) {
    const capabilityUnavailable =
      isCapabilityUnavailable(summaryQuery.error) || isCapabilityUnavailable(runsQuery.error)

    return (
      <div className={styles.page}>
        <section className={styles.unavailableState} role="alert" aria-labelledby="model-operations-state-title">
          <span className={styles.unavailableMarker} aria-hidden="true" />
          <div className={styles.unavailableCopy}>
            <p className={styles.stateLabel}>Model lifecycle</p>
            <h1 id="model-operations-state-title">
              {capabilityUnavailable ? 'Model Operations unavailable' : 'Failed to load Model Operations'}
            </h1>
            <p>
              {capabilityUnavailable
                ? 'Local retraining controls are disabled or unavailable. No run state was loaded.'
                : 'Run state is unavailable. Retry the workspace when the control plane is reachable.'}
            </p>
          </div>
          <div className={styles.stateActions}>
            <button
              type="button"
              className={styles.secondaryButton}
              onClick={() => {
                void summaryQuery.refetch()
                void runsQuery.refetch()
              }}
            >
              {capabilityUnavailable ? 'Retry Model Operations' : 'Retry'}
            </button>
            {capabilityUnavailable ? (
              <a className={styles.stateLink} href="/ml-health">
                Review ML Health
              </a>
            ) : null}
          </div>
        </section>
      </div>
    )
  }

  const handleRequest = () => {
    setNotice(null)
    void startMutation
      .mutateAsync({ trigger: 'manual' })
      .then((result) => setNotice(startNotice(result)))
      .catch(() => undefined)
  }

  const handleExport = () => {
    setNotice(null)
    void exportMutation
      .mutateAsync()
      .then((result) => setNotice(exportNotice(result)))
      .catch(() => undefined)
  }

  const handleDecision = async (decision: RetrainingDecision, reason: string | null) => {
    if (!selectedDetail) return
    setNotice(null)
    await decisionMutation.mutateAsync({ runId: selectedDetail.run_id, decision, reason })
    setNotice(`Candidate ${decision} recorded. Approved samples remain reusable.`)
  }

  const handleDeploy = async () => {
    if (!selectedDetail?.candidate_model_version) return
    setNotice(null)
    await deployMutation.mutateAsync({
      runId: selectedDetail.run_id,
      expectedCandidateVersion: selectedDetail.candidate_model_version,
    })
    setNotice('Local staging deployment requested explicitly.')
  }

  const handleRollback = async (reason: string) => {
    if (!selectedDetail) return
    setNotice(null)
    await rollbackMutation.mutateAsync({
      runId: selectedDetail.run_id,
      previousStagingVersion: selectedDetail.active_model_version,
      reason,
    })
    setNotice('Local staging rollback requested explicitly.')
  }

  const handleRetry = async () => {
    if (!selectedDetail) return
    setNotice(null)
    await retryMutation.mutateAsync(selectedDetail.run_id)
    setNotice('Retry requested within the run budget. The worker will resume from the durable artifacts.')
  }

  return (
    <div className={styles.page}>
      <MLModelOverviewSection
        summary={summary}
        runInProgress={runInProgress}
        canRun={canRun}
        actionsDisabled={runInProgress || mutationsBusy}
        onRequest={handleRequest}
        onExport={handleExport}
        actionError={actionError}
        notice={notice}
      />

      <MLModelRunsTable
        runs={runs}
        selectedRunId={selectedDetail?.run_id ?? selectedRunIdForView}
        onSelect={setSelectedRunId}
      />

      {selectedRunIdForView && !selectedDetail && (
        <div
          className={styles.noSelection}
          role={detailQuery.isPending ? 'status' : 'alert'}
          aria-label={detailQuery.isPending ? 'Loading selected run evidence' : 'Selected run evidence unavailable'}
        >
          {detailQuery.isPending
            ? 'Loading selected run evidence…'
            : 'Selected run evidence is unavailable. No candidate controls are shown.'}
        </div>
      )}

      {selectedDetail && (
        <div className={styles.detailGrid}>
          <MLModelComparisonPanel run={selectedDetail} />
          <MLModelDecisionPanel
            key={selectedDetail.run_id}
            run={selectedDetail}
            canRun={canRun}
            canDecide={canDecide}
            canDeploy={canDeploy}
            actionsDisabled={mutationsBusy}
            decisionPending={decisionMutation.isPending}
            deployPending={deployMutation.isPending}
            rollbackPending={rollbackMutation.isPending}
            retryPending={retryMutation.isPending}
            onDecision={handleDecision}
            onDeploy={handleDeploy}
            onRollback={handleRollback}
            onRetry={handleRetry}
            actionError={actionError}
          />
        </div>
      )}

      {!selectedDetail && runs.length === 0 && (
        <div className={styles.noSelection}>
          Run evidence and candidate controls will appear here after the first run is requested.
        </div>
      )}
    </div>
  )
}
