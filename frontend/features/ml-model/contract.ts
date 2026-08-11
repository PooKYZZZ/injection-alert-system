export const RETRAINING_RUN_STATE_VALUES = [
  'queued',
  'exporting',
  'dataset_validated',
  'training',
  'evaluating',
  'pending_approval',
  'approved',
  'deploying',
  'deployed',
  'held',
  'rejected',
  'NOT_ENOUGH_EVIDENCE',
  'QUARANTINED_FOR_REVIEW',
  'RETRYABLE_FAILED',
  'failed',
  'rolled_back',
  'RECOVERY_REQUIRED',
  'SKIPPED_NO_APPROVED_DATA',
] as const

export type RetrainingRunState = (typeof RETRAINING_RUN_STATE_VALUES)[number]

export const RETRAINING_ACTIVE_RUN_STATE_VALUES = [
  'queued',
  'exporting',
  'dataset_validated',
  'training',
  'evaluating',
  'deploying',
  'RECOVERY_REQUIRED',
] as const satisfies readonly RetrainingRunState[]

const RETRAINING_ACTIVE_RUN_STATES = new Set<RetrainingRunState>(
  RETRAINING_ACTIVE_RUN_STATE_VALUES
)

export function isRetrainingRunActive(state: RetrainingRunState): boolean {
  return RETRAINING_ACTIVE_RUN_STATES.has(state)
}

export const RETRAINING_DECISION_VALUES = ['approve', 'hold', 'reject'] as const
export type RetrainingDecision = (typeof RETRAINING_DECISION_VALUES)[number]

export const RETRAINING_TRIGGER_VALUES = ['manual', 'scheduled'] as const
export type RetrainingTrigger = (typeof RETRAINING_TRIGGER_VALUES)[number]

export const RETRAINING_EVIDENCE_STATUS_VALUES = [
  'VERIFIED',
  'NATIVE',
  'CONTROLLED_SMOKE',
  'NOT_RUN',
  'NOT_ENOUGH_EVIDENCE',
] as const
export type RetrainingEvidenceStatus =
  (typeof RETRAINING_EVIDENCE_STATUS_VALUES)[number]
