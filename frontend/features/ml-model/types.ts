import type {
  RetrainingDecision,
  RetrainingEvidenceStatus,
  RetrainingRunState,
  RetrainingTrigger,
} from './contract'

export interface RetrainingSummary {
  active_model_version: string
  latest_run_state: RetrainingRunState | null
  approved_count: number
  unreviewed_count: number
  excluded_count: number
  latest_dataset_version: string | null
  run_in_progress: boolean
  last_trigger_time: string | null
}

export interface RetrainingRun {
  run_id: string
  state: RetrainingRunState
  stage: string
  attempt: number
  retry_count: number
  max_retries: number
  created_at: string
  updated_at: string
  heartbeat_at: string | null
  trigger: RetrainingTrigger
  requested_by: string
  requested_timezone: string
  input_fingerprint: string
  source_review_revisions: string[]
  source_dataset_version: string
  source_dataset_digest: string
  pipeline_fingerprint: string
  active_model_version: string
  active_model_digest: string
  approved_sample_count: number
  operator_note: string | null
  worker_id: string | null
  next_retry_at: string | null
  dataset_version: string | null
  dataset_digest: string | null
  candidate_model_version: string | null
  candidate_model_digest: string | null
  evaluation_digest: string | null
  error_code: string | null
  error_message: string | null
  generation: number
}

export interface RetrainingEvent {
  created_at: string
  stage: string
  outcome: string
  code: string
  message: string | null
  duration_ms?: number | null
  actor_id?: string | null
  actor_role?: string | null
}

export interface RetrainingRunDetail extends RetrainingRun {
  events: RetrainingEvent[]
  heartbeat_age_seconds: number | null
  evidence_status: RetrainingEvidenceStatus
  retry_available: boolean
}

export interface RetrainingRunStart {
  run_id: string
  state: RetrainingRunState
  stage: string
  created: boolean
  attempt: number
}

export interface RetrainingRunList {
  runs: RetrainingRun[]
}

export interface RetrainingExportResult {
  export_id: string
  status: 'READY' | 'EMPTY' | 'QUARANTINED_FOR_REVIEW'
  approved_count: number
  exported_count: number
  rejected_count: number
  excluded_count: number
  quarantined: boolean
}

export interface RetrainingDecisionResult {
  decision: RetrainingDecision
  run: RetrainingRun
}
