import { z } from 'zod'
import {
  RETRAINING_DECISION_VALUES,
  RETRAINING_EVIDENCE_STATUS_VALUES,
  RETRAINING_RUN_STATE_VALUES,
  RETRAINING_TRIGGER_VALUES,
} from './contract'

const isoDate = z.string().datetime({ offset: true })
const digest = z.string().regex(/^[0-9a-f]{64}$/)
const runId = z.string().regex(/^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$/)
const modelVersion = z.string().regex(/^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$/)
const safeOperatorText = z
  .string()
  .max(500)
  .refine(
    (value) => ![...value].some((character) => {
      const code = character.charCodeAt(0)
      return code < 32 || code === 127
    }),
    'Text contains control characters.'
  )
  .refine(
    (value) =>
      !['model_input_text', 'http_request', 'API_SECRET_KEY', 'INTERNAL_API_KEY'].some(
        (marker) => value.includes(marker)
      ),
    'Text contains forbidden content.'
  )

export const RetrainingRunRequestSchema = z
  .object({
    trigger: z.enum(RETRAINING_TRIGGER_VALUES),
    operator_note: safeOperatorText.optional(),
  })
  .strict()

export const RetrainingExportRequestSchema = z.object({}).strict()

export const RetrainingRetryRequestSchema = z.object({}).strict()

export const RetrainingDecisionRequestSchema = z
  .object({
    decision: z.enum(RETRAINING_DECISION_VALUES),
    reason: safeOperatorText.nullable().optional(),
  })
  .strict()

export const RetrainingDeployRequestSchema = z
  .object({ expected_candidate_version: modelVersion })
  .strict()

export const RetrainingRollbackRequestSchema = z
  .object({
    previous_staging_version: modelVersion,
    reason: safeOperatorText.refine((value) => value.length > 0, 'Reason is required.'),
  })
  .strict()

export const RetrainingSummarySchema = z
  .object({
    active_model_version: z.string(),
    latest_run_state: z.enum(RETRAINING_RUN_STATE_VALUES).nullable(),
    approved_count: z.number().int().nonnegative(),
    unreviewed_count: z.number().int().nonnegative(),
    excluded_count: z.number().int().nonnegative(),
    latest_dataset_version: z.string().nullable(),
    run_in_progress: z.boolean(),
    last_trigger_time: isoDate.nullable(),
  })
  .strict()

export const RetrainingRunSchema = z
  .object({
    run_id: runId,
    state: z.enum(RETRAINING_RUN_STATE_VALUES),
    stage: z.string().max(64),
    attempt: z.number().int().nonnegative(),
    retry_count: z.number().int().nonnegative(),
    max_retries: z.number().int().nonnegative(),
    created_at: isoDate,
    updated_at: isoDate,
    heartbeat_at: isoDate.nullable(),
    trigger: z.enum(RETRAINING_TRIGGER_VALUES),
    requested_by: z.string().min(1).max(128),
    requested_timezone: z.string().min(1).max(64),
    input_fingerprint: digest,
    source_review_revisions: z.array(z.string()),
    source_dataset_version: z.string(),
    source_dataset_digest: digest,
    pipeline_fingerprint: digest,
    active_model_version: z.string(),
    active_model_digest: digest,
    approved_sample_count: z.number().int().nonnegative(),
    operator_note: z.string().max(500).nullable(),
    worker_id: z.string().max(128).nullable(),
    next_retry_at: isoDate.nullable(),
    dataset_version: z.string().nullable(),
    dataset_digest: digest.nullable(),
    candidate_model_version: z.string().nullable(),
    candidate_model_digest: digest.nullable(),
    evaluation_digest: digest.nullable(),
    error_code: z.string().max(64).nullable(),
    error_message: z.string().max(500).nullable(),
    generation: z.number().int().positive(),
  })
  .strict()

export const RetrainingRunStartSchema = z
  .object({
    run_id: runId,
    state: z.enum(RETRAINING_RUN_STATE_VALUES),
    stage: z.string().max(64),
    created: z.boolean(),
    attempt: z.number().int().nonnegative(),
  })
  .strict()

export const RetrainingRunListSchema = z
  .object({ runs: z.array(RetrainingRunSchema) })
  .strict()

export const RetrainingEventSchema = z
  .object({
    created_at: isoDate,
    stage: z.string().max(64),
    outcome: z.string().max(32),
    code: z.string().max(64),
    message: z.string().max(500).nullable(),
    duration_ms: z.number().int().nonnegative().nullable().optional(),
    actor_id: z.string().max(128).nullable().optional(),
    actor_role: z.string().max(32).nullable().optional(),
  })
  .strict()

export const RetrainingRunDetailSchema = RetrainingRunSchema.extend({
  events: z.array(RetrainingEventSchema),
  heartbeat_age_seconds: z.number().int().nonnegative().nullable(),
  evidence_status: z.enum(RETRAINING_EVIDENCE_STATUS_VALUES),
  retry_available: z.boolean(),
  evidence_summary: z
    .object({
      preprocessing_version: z.string().max(96).nullable(),
      evaluation_split: z.string().max(96).nullable(),
      evaluation_status: z.enum(['PASS', 'FAIL', 'NOT_RUN', 'NOT_ENOUGH_EVIDENCE']),
      comparison_status: z.enum(['PASS', 'FAIL', 'NOT_RUN', 'NOT_ENOUGH_EVIDENCE']),
      metrics: z.array(
        z
          .object({
            name: z.string().max(96),
            active_value: z.number().finite().nullable(),
            candidate_value: z.number().finite().nullable(),
            delta: z.number().finite().nullable(),
            support_count: z.number().int().nonnegative().nullable(),
            evidence_status: z.enum(RETRAINING_EVIDENCE_STATUS_VALUES),
          })
          .strict()
      ),
    })
    .strict()
    .default({
      preprocessing_version: null,
      evaluation_split: null,
      evaluation_status: 'NOT_RUN',
      comparison_status: 'NOT_RUN',
      metrics: [],
    }),
}).strict()

export const RetrainingExportResultSchema = z
  .object({
    export_id: runId,
    status: z.enum(['READY', 'EMPTY', 'QUARANTINED_FOR_REVIEW']),
    approved_count: z.number().int().nonnegative(),
    exported_count: z.number().int().nonnegative(),
    rejected_count: z.number().int().nonnegative(),
    excluded_count: z.number().int().nonnegative(),
    quarantined: z.boolean(),
  })
  .strict()

export const RetrainingDecisionResultSchema = z
  .object({
    decision: z.enum(RETRAINING_DECISION_VALUES),
    run: RetrainingRunSchema,
  })
  .strict()

export type RetrainingSummaryPayload = z.infer<typeof RetrainingSummarySchema>
export type RetrainingRunPayload = z.infer<typeof RetrainingRunSchema>
