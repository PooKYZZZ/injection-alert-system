'use client'

import { useMemo, useState } from 'react'
import { PERMISSIONS, roleHasPermission } from '@/lib/auth/roles'
import {
  useDecisionRetrainingMutation,
  useDeployRetrainingMutation,
  useExportRetrainingMutation,
  useMLModelRun,
  useMLModelRuns,
  useMLModelSummary,
  useRollbackRetrainingMutation,
  useStartRetrainingMutation,
} from '@/features/ml-model/queries'
import type { RetrainingRunDetail } from '@/features/ml-model/types'
import type { RetrainingDecision } from '@/features/ml-model/contract'
import { MLModelComparisonPanel } from './MLModelComparisonPanel'
import { MLModelDecisionPanel } from './MLModelDecisionPanel'
import { MLModelOverviewSection } from './MLModelOverviewSection'
import { MLModelRunsTable } from './MLModelRunsTable'
import styles from './MLModelWorkspace.module.css'

interface Props {
  role?: unknown
}

const ACTIVE_RUN_STATES = new Set([
  'queued',
  'exporting',
  'dataset_validated',
  'training',
  'evaluating',
  'deploying',
])

function errorMessage(error: unknown): string | null {
  if (!(error instanceof Error) || !error.message) return null
  const message = error.message.slice(0, 240)
  if (/model_input_text|http_request|API_SECRET_KEY|INTERNAL_API_KEY|traceback|stack trace/i.test(message)) {
    return 'The retraining operation failed safely. Review the run state and manifest.'
  }
  return message
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

  const summary = summaryQuery.data
  const runs = runsQuery.data?.runs ?? []
  const selectedRunIdForView =
    selectedRunId && runs.some((run) => run.run_id === selectedRunId)
      ? selectedRunId
      : runs[0]?.run_id ?? null
  const selectedListRun = runs.find((run) => run.run_id === selectedRunIdForView) ?? null

  const detailQuery = useMLModelRun(selectedRunIdForView ?? '')
  const selectedDetail = useMemo<RetrainingRunDetail | null>(() => {
    if (!selectedRunIdForView) return null
    if (detailQuery.data?.run_id === selectedRunIdForView) return detailQuery.data
    if (!selectedListRun) return null

    return {
      ...selectedListRun,
      events: [],
      heartbeat_age_seconds: null,
      evidence_status: 'NOT_RUN',
      retry_available: false,
    }
  }, [detailQuery.data, selectedListRun, selectedRunIdForView])

  const canRun = roleHasPermission(role, PERMISSIONS.ML_MODEL_RUN)
  const canDecide = roleHasPermission(role, PERMISSIONS.ML_MODEL_APPROVE)
  const canDeploy = roleHasPermission(role, PERMISSIONS.ML_MODEL_DEPLOY)
  const runInProgress = Boolean(
    summary?.run_in_progress || runs.some((run) => ACTIVE_RUN_STATES.has(run.state))
  )
  const mutationsBusy =
    startMutation.isPending ||
    exportMutation.isPending ||
    decisionMutation.isPending ||
    deployMutation.isPending ||
    rollbackMutation.isPending

  const actionError =
    errorMessage(startMutation.error) ??
    errorMessage(exportMutation.error) ??
    errorMessage(decisionMutation.error) ??
    errorMessage(deployMutation.error) ??
    errorMessage(rollbackMutation.error)

  if (summaryQuery.isPending || runsQuery.isPending) {
    return (
      <div className={styles.loadingWrap} role="status">
        <strong>Loading Model Operations</strong>
        <span>Loading safe run and evidence state…</span>
      </div>
    )
  }

  if (summaryQuery.isError || runsQuery.isError || !summary) {
    return (
      <div className={styles.loadingWrap} role="alert">
        <strong>Failed to load Model Operations</strong>
        <span>Run state is unavailable. Retry the workspace when the control plane is reachable.</span>
        <button
          type="button"
          className={styles.secondaryButton}
          onClick={() => {
            void summaryQuery.refetch()
            void runsQuery.refetch()
          }}
        >
          Retry
        </button>
      </div>
    )
  }

  const handleRequest = () => {
    setNotice(null)
    void startMutation.mutateAsync({ trigger: 'manual' }).then(() => {
      setNotice('Retraining request submitted. The worker will progress outside the request lifecycle.')
    }).catch(() => undefined)
  }

  const handleExport = () => {
    setNotice(null)
    void exportMutation.mutateAsync().then(() => {
      setNotice('Approved sample export completed with its manifest and review summary.')
    }).catch(() => undefined)
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

      {selectedDetail && (
        <div className={styles.detailGrid}>
          <MLModelComparisonPanel run={selectedDetail} />
          <MLModelDecisionPanel
            run={selectedDetail}
            canDecide={canDecide}
            canDeploy={canDeploy}
            actionsDisabled={mutationsBusy}
            decisionPending={decisionMutation.isPending}
            deployPending={deployMutation.isPending}
            rollbackPending={rollbackMutation.isPending}
            onDecision={handleDecision}
            onDeploy={handleDeploy}
            onRollback={handleRollback}
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
