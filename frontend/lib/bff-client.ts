import 'server-only'

import { z } from 'zod'
import { AlertSchema, LabelReviewSchema, PaginatedAlertsSchema } from '@/features/alerts/schemas'
import {
  ALERT_ACTION_TAKEN_VALUES,
  type AlertAction,
} from '@/features/alerts/contract'
import type { Alert, LabelReview, PaginatedAlerts } from '@/features/alerts/types'
import type { MLHealthData } from '@/features/ml-health/types'
import type { DashboardStats } from '@/features/stats/types'
import {
  RetrainingDecisionRequestSchema,
  RetrainingDecisionResultSchema,
  RetrainingDeployRequestSchema,
  RetrainingExportRequestSchema,
  RetrainingExportResultSchema,
  RetrainingRetryRequestSchema,
  RetrainingRollbackRequestSchema,
  RetrainingRunDetailSchema,
  RetrainingRunListSchema,
  RetrainingRunRequestSchema,
  RetrainingRunSchema,
  RetrainingRunStartSchema,
  RetrainingSummarySchema,
} from '@/features/ml-model/schemas'
import type {
  RetrainingDecisionResult,
  RetrainingExportResult,
  RetrainingRun,
  RetrainingRunDetail,
  RetrainingRunList,
  RetrainingRunStart,
  RetrainingSummary,
} from '@/features/ml-model/types'
import { MOCK_ALERTS } from '@/mocks/alerts'
import { MOCK_ML_HEALTH } from '@/mocks/ml-health'
import { MOCK_STATS } from '@/mocks/stats'

export interface BffError {
  code: string
  message: string
}

export type BffResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; error: BffError; retryAfter?: string }

const BackendAlertSchema = z.object({
  id: z.number(),
  timestamp: z.string(),
  source_ip: z.string().nullable().optional(),
  request_path: z.string().nullable().optional(),
  request_method: z.string().nullable().optional(),
  payload_snippet: z.string(),
  prediction: z.enum(['SQL Injection', 'Code Injection', 'Other Attacks', 'Normal']),
  confidence: z.number(),
  confidence_level: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
  action_taken: z.enum(ALERT_ACTION_TAKEN_VALUES).nullable().optional(),
  crs_score: z.number().nullable().optional(),
  crs_rule_ids: z.array(z.string()).nullable().optional(),
  ingest_source: z.string().nullable().optional(),
  matched_rule_messages: z.array(z.string()).nullable().optional(),
  matched_rule_tags: z.array(z.string()).nullable().optional(),
  analyst_label: z.string().nullable().optional(),
  labeled_at: z.string().nullable().optional(),
  labeled_by: z.string().nullable().optional(),
  triage_status: z.enum([
    'new', 'in_review', 'escalated', 'resolved', 'false_positive'
  ]).nullable().optional(),
  label_review: z.unknown().nullable().optional(),
})

const BackendPaginatedAlertsSchema = z.object({
  items: z.array(BackendAlertSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
})

const BackendActivityBucketSchema = z.object({
  bucket_index: z.number(),
  total_count: z.number(),
  blocked_count: z.number(),
  allowed_count: z.number(),
  throttled_count: z.number(),
  timestamp_start: z.string(),
  timestamp_end: z.string().nullable().optional(),
  bucket_width_seconds: z.number().nullable().optional(),
})

const BackendSourceIPSchema = z.object({
  ip: z.string(),
  count: z.number(),
  action: z.string().nullable().optional(),
})

const BackendTargetPathSchema = z.object({
  path: z.string(),
  hits: z.number(),
})

type BackendSourceIp = {
  ip: string
  count: number
  action?: string | null
}

type BackendTargetPath = {
  path: string
  hits: number
}

type BackendStatsPayload = {
  total_requests: number
  counts_by_label: {
    'SQL Injection': number
    'Code Injection': number
    'Other Attacks': number
    Normal: number
  }
  avg_inference_latency_ms: number
  blocked_count: number
  allowed_count: number
  throttled_count?: number
  avg_confidence: number | null
  false_positive_rate?: number
  false_positive_count?: number
  high_alert_count?: number
  prev_high_alert_count?: number | null
  prev_total_requests?: number | null
  prev_blocked_count?: number | null
  prev_allowed_count?: number | null
  prev_throttled_count?: number | null
  activity_buckets: z.infer<typeof BackendActivityBucketSchema>[]
  attack_distribution?: Record<string, number>
  top_source_ips?: BackendSourceIp[]
  top_targeted_paths?: BackendTargetPath[]
}

const BackendStatsSchema = z.object({
  total_requests: z.number(),
  counts_by_label: z.object({
    'SQL Injection': z.number(),
    'Code Injection': z.number(),
    'Other Attacks': z.number(),
    Normal: z.number(),
  }),
  avg_inference_latency_ms: z.number(),
  blocked_count: z.number(),
  allowed_count: z.number(),
  throttled_count: z.number().optional(),
  avg_confidence: z.number().nullable(),
  false_positive_rate: z.number().optional(),
  false_positive_count: z.number().optional(),
  high_alert_count: z.number().optional(),
  prev_high_alert_count: z.number().nullable().optional(),
  prev_total_requests: z.number().nullable().optional(),
  prev_blocked_count: z.number().nullable().optional(),
  prev_allowed_count: z.number().nullable().optional(),
  prev_throttled_count: z.number().nullable().optional(),
  activity_buckets: z.array(BackendActivityBucketSchema),
  attack_distribution: z.record(z.string(), z.number()).optional(),
  top_source_ips: z.array(BackendSourceIPSchema).default([]),
  top_targeted_paths: z.array(BackendTargetPathSchema).default([]),
})

const CalibrationBinSchema = z.object({
  bin_idx: z.number(),
  bin_center: z.number(),
  accuracy: z.number(),
  confidence: z.number(),
  count: z.number(),
})

const QueueHealthSchema = z.object({
  enabled: z.boolean(),
  max_size: z.number(),
  depth: z.number(),
  available_capacity: z.number(),
  worker_count: z.number(),
  worker_running: z.boolean(),
  total_enqueued: z.number(),
  total_processed: z.number(),
  total_failed: z.number(),
  overflow_count: z.number(),
  last_error: z.string().nullable(),
  last_error_at: z.string().nullable(),
  last_processed_at: z.string().nullable(),
})

const BackendMlHealthSchema = z.object({
  model_version: z.string(),
  loaded: z.boolean(),
  status: z.enum(['healthy', 'degraded']),
  avg_inference_latency_ms: z.number(),
  total_processed: z.number(),
  drift_detected: z.boolean(),
  drift_score: z.number().nullable().optional(),
  confidence_thresholds: z.object({
    low: z.number().optional(),
    high: z.number().optional(),
    critical: z.number().optional(),
  }),
  // Optional eval metadata from model registry artifacts
  macro_f1: z.number().nullable().optional(),
  ece: z.number().nullable().optional(),
  per_class_f1: z.record(z.string(), z.number()).optional(),
  calibration_bins: z.array(CalibrationBinSchema).optional(),
  prediction_distribution: z
    .union([
      z.object({
        baseline: z.record(z.string(), z.number()),
        current: z.record(z.string(), z.number()),
      }),
      z.record(z.string(), z.number()),
    ])
    .optional(),
  queue: QueueHealthSchema.nullable().optional(),
})

function ok<T>(data: T): BffResult<T> {
  return { ok: true, data }
}

function err<T>(status: number, code: string, message: string, retryAfter?: string): BffResult<T> {
  return { ok: false, status, error: { code, message }, retryAfter }
}

const UPSTREAM_REQUEST_TIMEOUT_MS = 30_000

function upstreamRequestSignal(): AbortSignal {
  return AbortSignal.timeout(UPSTREAM_REQUEST_TIMEOUT_MS)
}

function upstreamTransportFailure<T>(): BffResult<T> {
  return err(502, 'UPSTREAM_ERROR', 'Upstream service failed.')
}

function isValidTimeZone(timeZone: string): boolean {
  try {
    Intl.DateTimeFormat(undefined, { timeZone })
    return true
  } catch {
    return false
  }
}

function parseAlertId(alertId: string): BffResult<number> {
  const trimmedId = alertId.trim()
  if (!/^[1-9]\d*$/.test(trimmedId)) {
    return err(400, 'INVALID_ID', 'Alert ID must be a valid number.')
  }

  return ok(Number(trimmedId))
}

function isMockMode(): boolean {
  return process.env.USE_MOCK_API === 'true'
}

function getUpstreamConfig(): BffResult<{ baseUrl: string; apiKey: string }> {
  if (isMockMode()) {
    return ok({ baseUrl: '', apiKey: '' })
  }

  const baseUrl = process.env.FASTAPI_BASE_URL
  const apiKey = process.env.INTERNAL_API_KEY

  if (!baseUrl || !apiKey) {
    return err(
      500,
      'BFF_MISCONFIGURED',
      'Server configuration is incomplete.'
    )
  }

  return ok({ baseUrl, apiKey })
}

export async function openAlertStream(
  signal: AbortSignal
): Promise<BffResult<Response>> {
  const config = getUpstreamConfig()
  if (!config.ok) return config
  if (isMockMode()) {
    return err(503, 'UPSTREAM_ERROR', 'Real-time alert updates are unavailable in mock mode.')
  }

  let response: Response
  const handshakeController = new AbortController()
  const handshakeTimeout = setTimeout(
    () => handshakeController.abort(),
    10_000
  )
  try {
    response = await fetch(`${config.data.baseUrl}/api/alerts/stream`, {
      method: 'GET',
      cache: 'no-store',
      redirect: 'error',
      signal: AbortSignal.any([signal, handshakeController.signal]),
      headers: {
        Authorization: `Bearer ${config.data.apiKey}`,
      },
    })
  } catch {
    return err(502, 'UPSTREAM_ERROR', 'Upstream service failed.')
  } finally {
    clearTimeout(handshakeTimeout)
  }

  if (!response.ok) {
    cancelResponseBody(response)
    if (response.status === 401 || response.status === 403) {
      return err(
        500,
        'INTERNAL_SERVICE_AUTH_FAILED',
        'Internal service authentication failed.'
      )
    }
    return err(
      response.status >= 500 ? response.status : 502,
      'UPSTREAM_ERROR',
      'Upstream service failed.'
    )
  }

  const mediaType = response.headers
    .get('Content-Type')
    ?.split(';', 1)[0]
    ?.trim()
    .toLowerCase()
  if (mediaType !== 'text/event-stream') {
    cancelResponseBody(response)
    return err(502, 'UPSTREAM_ERROR', 'Upstream response was not an event stream.')
  }

  return ok(response)
}

function cancelResponseBody(response: Response): void {
  try {
    void response.body?.cancel().catch(() => undefined)
  } catch {
    // A rejected upstream response must not replace the generic BFF error.
  }
}

function normalizeWithSchema<T>(
  schema: z.ZodType<T>,
  payload: unknown
): BffResult<T> {
  const parsed = schema.safeParse(payload)
  if (!parsed.success) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[BFF] Upstream schema mismatch', {
        issueCount: parsed.error.issues.length,
      })
    }

    return err(
      502,
      'UPSTREAM_ERROR',
      'Upstream response did not match expected shape.'
    )
  }

  return ok(parsed.data)
}

function validateMockData<T>(
  schema: z.ZodType<T>,
  payload: unknown
): BffResult<T> {
  try {
    const parsed = schema.safeParse(payload)
    if (!parsed.success) {
      return err(
        500,
        'INVALID_MOCK_DATA',
        'Mock data does not match expected contract.'
      )
    }

    return ok(parsed.data)
  } catch {
    return err(
      500,
      'INVALID_MOCK_DATA',
      'Mock data does not match expected contract.'
    )
  }
}

function normalizeAlert(alert: z.infer<typeof BackendAlertSchema>): BffResult<Alert> {
  let labelReview: z.infer<typeof LabelReviewSchema> | null = null
  if (alert.label_review != null) {
    const parsedReview = normalizeWithSchema(LabelReviewSchema, alert.label_review)
    if (!parsedReview.ok) return parsedReview
    labelReview = parsedReview.data
  }

  return normalizeWithSchema(AlertSchema, {
    alert_id: String(alert.id),
    timestamp: alert.timestamp,
    source_ip: alert.source_ip ?? null,
    request_path: alert.request_path ?? null,
    request_method: alert.request_method ?? null,
    payload_snippet: alert.payload_snippet,
    prediction: alert.prediction,
    confidence: alert.confidence,
    confidence_level: alert.confidence_level,
    action_taken: alert.action_taken ?? null,
    crs_score: alert.crs_score ?? undefined,
    crs_rule_ids: alert.crs_rule_ids ?? null,
    ingest_source: alert.ingest_source ?? null,
    matched_rule_messages: alert.matched_rule_messages ?? null,
    matched_rule_tags: alert.matched_rule_tags ?? null,
    analyst_label: alert.analyst_label ?? null,
    labeled_at: alert.labeled_at ?? null,
    labeled_by: alert.labeled_by ?? null,
    triage_status: alert.triage_status ?? null,
    ...(labelReview != null ? { label_review: labelReview } : {}),
  })
}

function normalizeAlertList(
  payload: z.infer<typeof BackendPaginatedAlertsSchema>
): BffResult<PaginatedAlerts> {
  const normalizedItems: Alert[] = []
  for (const item of payload.items) {
    const normalizedAlert = normalizeAlert(item)
    if (!normalizedAlert.ok) {
      return normalizedAlert
    }
    normalizedItems.push(normalizedAlert.data)
  }

  return normalizeWithSchema(PaginatedAlertsSchema, {
    items: normalizedItems,
    total: payload.total,
    page: payload.page,
    pageSize: payload.page_size,
  })
}

function normalizeAlertAction(value: string | null | undefined): AlertAction | null {
  if (
    typeof value === 'string' &&
    ALERT_ACTION_TAKEN_VALUES.includes(value as AlertAction)
  ) {
    return value as AlertAction
  }
  return null
}

type NormalizedBucket = DashboardStats['activity_buckets'][number] & {
  _sortTimestampMs: number
  _originalIndex: number
}

function normalizeStats(payload: BackendStatsPayload): BffResult<DashboardStats> {
  const actionableAlerts =
    (payload.counts_by_label['SQL Injection'] ?? 0) +
    (payload.counts_by_label['Code Injection'] ?? 0) +
    (payload.counts_by_label['Other Attacks'] ?? 0)

  // Normalize new fields with safe defaults for staged rollout
  const throttledCount = payload.throttled_count ?? 0
  const attackDistribution = payload.attack_distribution ?? {}
  const topSourceIps = (payload.top_source_ips ?? []).map((ip) => ({
    ip: ip.ip,
    count: ip.count,
    action: normalizeAlertAction(ip.action),
  }))
  const topTargetedPaths = (payload.top_targeted_paths ?? []).map((path) => ({
    path: path.path,
    hits: path.hits,
  }))
  const highAlertCount =
    payload.high_alert_count ??
    Object.entries(payload.counts_by_label)
      .filter(([label]) => label !== 'Normal')
      .reduce((sum, [, count]) => sum + count, 0)

  const normalizedBuckets: NormalizedBucket[] = []
  for (let idx = 0; idx < payload.activity_buckets.length; idx += 1) {
    const bucket = payload.activity_buckets[idx]
    const parsedTimestamp = new Date(bucket.timestamp_start)
    if (Number.isNaN(parsedTimestamp.getTime())) {
      return err(
        502,
        'UPSTREAM_ERROR',
        `Upstream response contained invalid bucket timestamp at index ${idx}: ${bucket.timestamp_start}`
      )
    }

    const parsedTimestampEnd =
      bucket.timestamp_end != null ? new Date(bucket.timestamp_end) : null
    if (parsedTimestampEnd != null && Number.isNaN(parsedTimestampEnd.getTime())) {
      return err(
        502,
        'UPSTREAM_ERROR',
        `Upstream response contained invalid bucket end timestamp at index ${idx}: ${bucket.timestamp_end}`
      )
    }

    normalizedBuckets.push({
      bucket_index: bucket.bucket_index,
      total_count: bucket.total_count,
      blocked_count: bucket.blocked_count,
      allowed_count: bucket.allowed_count,
      throttled_count: bucket.throttled_count,
      timestamp_start: bucket.timestamp_start,
      timestamp_end: bucket.timestamp_end ?? null,
      bucket_width_seconds: bucket.bucket_width_seconds ?? null,
      _sortTimestampMs: parsedTimestamp.getTime(),
      _originalIndex: idx,
    })
  }

  normalizedBuckets.sort(
    (a, b) =>
      a._sortTimestampMs - b._sortTimestampMs ||
      a.bucket_index - b.bucket_index ||
      a._originalIndex - b._originalIndex
  )

  return ok({
    actionable_alerts: actionableAlerts,
    total_requests: payload.total_requests,
    avg_inference_latency_ms: payload.avg_inference_latency_ms,
    blocked_count: payload.blocked_count,
    allowed_count: payload.allowed_count,
    throttled_count: throttledCount,
    avg_confidence: payload.avg_confidence,
    false_positive_rate: payload.false_positive_rate ?? 0,
    false_positive_count: payload.false_positive_count ?? 0,
    high_alert_count: highAlertCount,
    prev_high_alert_count: payload.prev_high_alert_count ?? null,
    prev_total_requests: payload.prev_total_requests ?? null,
    prev_blocked_count: payload.prev_blocked_count ?? null,
    prev_allowed_count: payload.prev_allowed_count ?? null,
    prev_throttled_count: payload.prev_throttled_count ?? null,
    activity_buckets: normalizedBuckets.map(
      ({ _sortTimestampMs: _, _originalIndex: __, ...bucket }) => bucket
    ),
    attack_distribution: attackDistribution,
    top_source_ips: topSourceIps,
    top_targeted_paths: topTargetedPaths,
  })
}

function normalizeMlHealth(
  payload: z.infer<typeof BackendMlHealthSchema>
): MLHealthData {
  // BFF validation: ensure thresholds are valid
  const low = payload.confidence_thresholds.low
  const high = payload.confidence_thresholds.high
  const critical = payload.confidence_thresholds.critical
  let medium: number | null = null
  let normalizedCritical: number | null = null

  if (typeof low === 'number' && typeof high === 'number') {
    // BFF check: validate threshold range (0-1 or 0-100)
    const normalizedLow = low <= 1 ? low : low / 100
    const normalizedHigh = high <= 1 ? high : high / 100
    normalizedCritical =
      typeof critical === 'number' ? (critical <= 1 ? critical : critical / 100) : null

    // BFF check: ensure low < high
    if (normalizedLow >= normalizedHigh || (normalizedCritical !== null && normalizedHigh >= normalizedCritical)) {
      console.warn('[BFF] Invalid thresholds: low >= high, using defaults')
    } else {
      // BFF transform: derive medium from low/high range
      medium = (normalizedLow + normalizedHigh) / 2
    }
  }

  // BFF honesty: drift_detected comes from real database analysis (comparing
  // recent confidence vs baseline). drift_score is also from the backend.
  // If drift_score is null/undefined, drift computation was unavailable,
  // so we must NOT claim "NORMAL" - set to null to indicate unavailable.
  const driftScore = payload.drift_score ?? null
  const hasRealDriftData = typeof driftScore === 'number'
  let driftStatus: 'NORMAL' | 'WARNING' | 'CRITICAL' | null = null

  if (hasRealDriftData) {
    // Real drift data available - determine status based on drift_detected
    driftStatus = payload.drift_detected ? 'WARNING' : 'NORMAL'
  } else {
    // No real drift data - cannot claim NORMAL, set to null for unavailable
    driftStatus = null
  }

  const rawPredictionDistribution = payload.prediction_distribution as unknown
  const predictionDistribution: MLHealthData['prediction_distribution'] =
    rawPredictionDistribution &&
    typeof rawPredictionDistribution === 'object' &&
    !Array.isArray(rawPredictionDistribution) &&
    'baseline' in rawPredictionDistribution &&
    'current' in rawPredictionDistribution
      ? {
          baseline: (rawPredictionDistribution as { baseline: Record<string, number> }).baseline,
          current: (rawPredictionDistribution as { current: Record<string, number> }).current,
        }
      : {
          baseline: {},
          current:
            (rawPredictionDistribution && typeof rawPredictionDistribution === 'object' && !Array.isArray(rawPredictionDistribution)
              ? (rawPredictionDistribution as Record<string, number>)
              : {}),
        }

  return {
    model_version: payload.model_version,
    status: payload.loaded
      ? payload.status === 'healthy'
        ? 'HEALTHY'
        : 'DEGRADED'
      : 'DOWN',
    latency_ms: payload.avg_inference_latency_ms,
    latency_trend: null,
    drift_score: driftScore,
    drift_status: driftStatus,
    traffic_processed: payload.total_processed,
    thresholds: {
      low: low ?? null,
      medium: medium ?? null,
      high: high ?? null,
      critical: normalizedCritical,
    },
    // Optional eval metadata from model registry artifacts
    macro_f1: payload.macro_f1 ?? null,
    ece: payload.ece ?? null,
    per_class_f1: payload.per_class_f1 ?? {},
    calibration_bins: payload.calibration_bins ?? [],
    prediction_distribution: predictionDistribution,
    ...(payload.queue !== undefined ? { queue: payload.queue } : {}),
  }
}

async function fetchUpstream<T>(
  path: string,
  schema: z.ZodType<T>
): Promise<BffResult<T>> {
  const config = getUpstreamConfig()
  if (!config.ok) {
    return config
  }

  if (isMockMode()) {
    return err(500, 'INTERNAL_ERROR', 'Mock mode must be handled explicitly.')
  }

  let response: Response
  try {
    response = await fetch(`${config.data.baseUrl}${path}`, {
      method: 'GET',
      cache: 'no-store',
      headers: {
        Authorization: `Bearer ${config.data.apiKey}`,
        'Content-Type': 'application/json',
      },
      signal: upstreamRequestSignal(),
    })
  } catch {
    return upstreamTransportFailure()
  }

  if (!response.ok) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[BFF] Upstream returned non-OK status', {
        status: response.status,
      })
    }

    // Route handlers enforce auth before calling BFF client, so upstream 401/403
    // indicates an internal auth failure (e.g., invalid, expired, or unauthorized
    // INTERNAL_API_KEY). Map to INTERNAL_SERVICE_AUTH_FAILED to accurately reflect
    // the possible causes while remaining browser-safe (no sensitive details leaked).
    // Note: retryAfter is NOT attached for auth failures - those are not "wait and retry" semantics.
    if (response.status === 401 || response.status === 403) {
      return err(
        500,
        'INTERNAL_SERVICE_AUTH_FAILED',
        'Internal service authentication failed.'
      )
    }

    // Capture Retry-After header for retryable upstream failures
    const retryAfter = response.headers.get('Retry-After') ?? undefined

    if (response.status === 404) {
      return err(404, 'NOT_FOUND', 'Requested resource was not found.', retryAfter)
    }

    if (response.status >= 500) {
      return err(response.status, 'UPSTREAM_ERROR', 'Upstream service failed.', retryAfter)
    }

    return err(response.status, 'UPSTREAM_ERROR', 'Upstream request failed.', retryAfter)
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    return err(502, 'UPSTREAM_ERROR', 'Upstream service failed.')
  }

  return normalizeWithSchema(schema, payload)
}

export type RetrainingActor = { id: string; role: string }

function parseRetrainingRunId(runId: string): BffResult<string> {
  if (!/^retrain-\d{8}T\d{6}Z-[0-9a-f]{12}$/.test(runId)) {
    return err(400, 'INVALID_RUN_ID', 'Retraining run ID is invalid.')
  }
  return ok(runId)
}

function actorHeaders(actor?: RetrainingActor): Record<string, string> {
  return actor
    ? {
        'X-Reviewer-Id': actor.id,
        'X-Reviewer-Role': actor.role,
      }
    : {}
}

async function fetchRetrainingUpstream<T>(
  path: string,
  schema: z.ZodType<T>,
  options: {
    method: 'POST' | 'GET'
    body?: unknown
    actor?: RetrainingActor
  }
): Promise<BffResult<T>> {
  const config = getUpstreamConfig()
  if (!config.ok) return config
  if (isMockMode()) {
    return err(503, 'UPSTREAM_ERROR', 'Retraining operations are unavailable in mock mode.')
  }

  let response: Response
  try {
    response = await fetch(`${config.data.baseUrl}${path}`, {
      method: options.method,
      cache: 'no-store',
      headers: {
        Authorization: `Bearer ${config.data.apiKey}`,
        'Content-Type': 'application/json',
        ...actorHeaders(options.actor),
        ...(options.method === 'POST'
          ? {
              'X-Requester-Timezone': Intl.DateTimeFormat().resolvedOptions().timeZone,
            }
          : {}),
      },
      ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
      signal: upstreamRequestSignal(),
    })
  } catch {
    return upstreamTransportFailure()
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      return err(500, 'INTERNAL_SERVICE_AUTH_FAILED', 'Internal service authentication failed.')
    }
    if (response.status === 404) {
      return err(404, 'NOT_FOUND', 'Requested resource was not found.')
    }
    if (response.status >= 500) {
      return err(response.status, 'UPSTREAM_ERROR', 'Upstream service failed.')
    }
    return err(response.status, 'UPSTREAM_ERROR', 'Upstream request failed.')
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    return err(502, 'UPSTREAM_ERROR', 'Upstream service failed.')
  }
  return normalizeWithSchema(schema, payload)
}

export async function getRetrainingSummary(): Promise<BffResult<RetrainingSummary>> {
  return fetchRetrainingUpstream('/api/retraining/summary', RetrainingSummarySchema, {
    method: 'GET',
  })
}

export async function exportRetrainingSamples(
  actor: RetrainingActor
): Promise<BffResult<RetrainingExportResult>> {
  const payload = RetrainingExportRequestSchema.parse({})
  return fetchRetrainingUpstream('/api/retraining/export', RetrainingExportResultSchema, {
    method: 'POST',
    body: payload,
    actor,
  })
}

export async function startRetrainingRun(
  input: unknown,
  actor: RetrainingActor
): Promise<BffResult<RetrainingRunStart>> {
  const parsed = RetrainingRunRequestSchema.safeParse(input)
  if (!parsed.success) return err(400, 'INVALID_REQUEST', 'Invalid retraining request.')
  return fetchRetrainingUpstream('/api/retraining/runs', RetrainingRunStartSchema, {
    method: 'POST',
    body: parsed.data,
    actor,
  })
}

export async function getRetrainingRuns(
  actor: RetrainingActor
): Promise<BffResult<RetrainingRunList>> {
  return fetchRetrainingUpstream('/api/retraining/runs', RetrainingRunListSchema, {
    method: 'GET',
    actor,
  })
}

export async function getRetrainingRun(
  runId: string,
  actor: RetrainingActor
): Promise<BffResult<RetrainingRunDetail>> {
  const parsed = parseRetrainingRunId(runId)
  if (!parsed.ok) return parsed
  return fetchRetrainingUpstream(
    `/api/retraining/runs/${encodeURIComponent(parsed.data)}`,
    RetrainingRunDetailSchema,
    { method: 'GET', actor }
  )
}

export async function retryRetrainingRun(
  runId: string,
  payload: z.infer<typeof RetrainingRetryRequestSchema>,
  actor: RetrainingActor
): Promise<BffResult<RetrainingRun>> {
  const parsedId = parseRetrainingRunId(runId)
  if (!parsedId.ok) return parsedId
  return fetchRetrainingUpstream(
    `/api/retraining/runs/${encodeURIComponent(parsedId.data)}/retry`,
    RetrainingRunSchema,
    { method: 'POST', body: payload, actor }
  )
}

export async function decideRetrainingRun(
  runId: string,
  input: unknown,
  actor: RetrainingActor
): Promise<BffResult<RetrainingDecisionResult>> {
  const parsedId = parseRetrainingRunId(runId)
  if (!parsedId.ok) return parsedId
  const parsed = RetrainingDecisionRequestSchema.safeParse(input)
  if (!parsed.success) return err(400, 'INVALID_REQUEST', 'Invalid retraining decision.')
  return fetchRetrainingUpstream(
    `/api/retraining/runs/${encodeURIComponent(parsedId.data)}/decision`,
    RetrainingDecisionResultSchema,
    { method: 'POST', body: parsed.data, actor }
  )
}

export async function deployRetrainingRun(
  runId: string,
  input: unknown,
  actor: RetrainingActor
): Promise<BffResult<RetrainingRun>> {
  const parsedId = parseRetrainingRunId(runId)
  if (!parsedId.ok) return parsedId
  const parsed = RetrainingDeployRequestSchema.safeParse(input)
  if (!parsed.success) return err(400, 'INVALID_REQUEST', 'Invalid deployment request.')
  return fetchRetrainingUpstream(
    `/api/retraining/runs/${encodeURIComponent(parsedId.data)}/deploy`,
    RetrainingRunSchema,
    { method: 'POST', body: parsed.data, actor }
  )
}

export async function rollbackRetrainingRun(
  runId: string,
  input: unknown,
  actor: RetrainingActor
): Promise<BffResult<RetrainingRun>> {
  const parsedId = parseRetrainingRunId(runId)
  if (!parsedId.ok) return parsedId
  const parsed = RetrainingRollbackRequestSchema.safeParse(input)
  if (!parsed.success) return err(400, 'INVALID_REQUEST', 'Invalid rollback request.')
  return fetchRetrainingUpstream(
    `/api/retraining/runs/${encodeURIComponent(parsedId.data)}/rollback`,
    RetrainingRunSchema,
    { method: 'POST', body: parsed.data, actor }
  )
}

const PARAM_MAP: Record<string, string> = {
  page: 'page',
  pageSize: 'page_size',
  severity: 'severity',
  confidence_tier: 'confidence_tier',
  action: 'action',
  triage_status: 'triage_status',
  prediction: 'prediction',
  source_ip: 'source_ip',
  search: 'search',
  window: 'time_range',
  timeRange: 'time_range',
  sort_by: 'sort_by',
  sort_dir: 'sort_dir',
}

export async function getAlerts(
  searchParams: URLSearchParams
): Promise<BffResult<PaginatedAlerts>> {
  if (isMockMode()) {
    return validateMockData(PaginatedAlertsSchema, MOCK_ALERTS)
  }

  const query = new URLSearchParams()

  for (const [frontendKey, backendKey] of Object.entries(PARAM_MAP)) {
    const value = searchParams.get(frontendKey)
    if (value) query.set(backendKey, value)
  }

  // Forward triage_status values (including 'new') directly to upstream.
  // Previously we attempted to omit the param for 'new' which caused the
  // upstream to return unexpected results; send the explicit value so the
  // backend can apply its intended filtering logic.

  for (const value of searchParams.getAll('confidence_level')) {
    if (value) query.append('confidence_level', value)
  }

  const path = query.size > 0 ? `/api/alerts?${query.toString()}` : '/api/alerts'

  const upstream = await fetchUpstream(path, BackendPaginatedAlertsSchema)
  if (!upstream.ok) {
    return upstream
  }

  return normalizeAlertList(upstream.data)
}

export async function getAlertDetail(alertId: string): Promise<BffResult<Alert>> {
  if (isMockMode()) {
    const match = MOCK_ALERTS.items.find((item) => item.alert_id === alertId)
    if (!match) {
      return err(404, 'NOT_FOUND', 'Requested resource was not found.')
    }

    return validateMockData(AlertSchema, match)
  }

  const parsedId = parseAlertId(alertId)
  if (!parsedId.ok) {
    return parsedId
  }

  const upstream = await fetchUpstream(`/api/alerts/${parsedId.data}`, BackendAlertSchema)
  if (!upstream.ok) {
    return upstream
  }

  return normalizeAlert(upstream.data)
}

export async function submitAlertLabelReview(
  alertId: string,
  review: {
    verified_label: z.infer<typeof LabelReviewSchema>['verified_label']
    approval_state: Extract<
      z.infer<typeof LabelReviewSchema>['approval_state'],
      'approved_for_training' | 'excluded_from_training'
    >
    review_note?: string
  },
  reviewer: { id: string; role: string }
): Promise<BffResult<LabelReview>> {
  if (isMockMode()) {
    return err(503, 'UPSTREAM_ERROR', 'Verified label review is unavailable in mock mode.')
  }

  const parsedId = parseAlertId(alertId)
  if (!parsedId.ok) return parsedId

  const config = getUpstreamConfig()
  if (!config.ok) return config

  let response: Response
  try {
    response = await fetch(
      `${config.data.baseUrl}/api/alerts/${parsedId.data}/label-review`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${config.data.apiKey}`,
          'Content-Type': 'application/json',
          'X-Reviewer-Id': reviewer.id,
          'X-Reviewer-Role': reviewer.role,
        },
        body: JSON.stringify(review),
        signal: upstreamRequestSignal(),
      }
    )
  } catch {
    return upstreamTransportFailure()
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      return err(500, 'INTERNAL_SERVICE_AUTH_FAILED', 'Internal service authentication failed.')
    }
    if (response.status === 404) return err(404, 'NOT_FOUND', 'Requested resource was not found.')
    if (response.status >= 500) return err(response.status, 'UPSTREAM_ERROR', 'Upstream service failed.')
    return err(response.status, 'UPSTREAM_ERROR', 'Upstream request failed.')
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    return err(502, 'UPSTREAM_ERROR', 'Upstream service failed.')
  }
  return normalizeWithSchema(LabelReviewSchema, payload)
}

export async function getStats(
  window?: string,
  timezoneName?: string
): Promise<BffResult<DashboardStats>> {
  if (isMockMode()) {
    return ok(MOCK_STATS)
  }

  const query = new URLSearchParams()
  if (window) query.set('window', window)
  if (timezoneName && isValidTimeZone(timezoneName)) {
    query.set('timezone_name', timezoneName)
  }
  const path = query.size > 0 ? `/api/stats?${query.toString()}` : '/api/stats'
  const upstream = await fetchUpstream(path, BackendStatsSchema)
  if (!upstream.ok) {
    return upstream
  }

  return normalizeStats(upstream.data)
}

export async function getMlHealth(): Promise<BffResult<MLHealthData>> {
  if (isMockMode()) {
    return ok(MOCK_ML_HEALTH)
  }

  const upstream = await fetchUpstream('/api/ml-health', BackendMlHealthSchema)
  if (!upstream.ok) {
    return upstream
  }

  return ok(normalizeMlHealth(upstream.data))
}

export async function updateAlertTriage(
  alertId: string,
  status: 'new' | 'in_review' | 'escalated' | 'resolved' | 'false_positive'
): Promise<BffResult<Alert>> {
  if (isMockMode()) {
    // Find the matching alert in MOCK_ALERTS
    const match = MOCK_ALERTS.items.find((item) => item.alert_id === alertId)
    if (!match) {
      return err(404, 'NOT_FOUND', 'Requested resource was not found.')
    }
    // Update in-memory
    match.triage_status = status
    return validateMockData(AlertSchema, match)
  }

  const parsedId = parseAlertId(alertId)
  if (!parsedId.ok) {
    return parsedId
  }

  const config = getUpstreamConfig()
  if (!config.ok) {
    return config
  }

  let response: Response
  try {
    response = await fetch(
      `${config.data.baseUrl}/api/alerts/${parsedId.data}/triage`,
      {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${config.data.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ triage_status: status }),
        signal: upstreamRequestSignal(),
      }
    )
  } catch {
    return upstreamTransportFailure()
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      return err(
        500,
        'INTERNAL_SERVICE_AUTH_FAILED',
        'Internal service authentication failed.'
      )
    }

    if (response.status === 404) {
      return err(404, 'NOT_FOUND', 'Requested resource was not found.')
    }

    if (response.status >= 500) {
      return err(response.status, 'UPSTREAM_ERROR', 'Upstream service failed.')
    }

    return err(response.status, 'UPSTREAM_ERROR', 'Upstream request failed.')
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    return err(502, 'UPSTREAM_ERROR', 'Upstream service failed.')
  }

  const parsed = BackendAlertSchema.safeParse(payload)
  if (!parsed.success) {
    return err(
      502,
      'UPSTREAM_ERROR',
      'Upstream response did not match expected shape.'
    )
  }

  return normalizeAlert(parsed.data)
}

export async function updateAlertAction(
  alertId: string,
  action: AlertAction
): Promise<BffResult<Alert>> {
  if (isMockMode()) {
    const match = MOCK_ALERTS.items.find((item) => item.alert_id === alertId)
    if (!match) {
      return err(404, 'NOT_FOUND', 'Requested resource was not found.')
    }
    match.action_taken = action
    return validateMockData(AlertSchema, match)
  }

  const parsedId = parseAlertId(alertId)
  if (!parsedId.ok) {
    return parsedId
  }

  const config = getUpstreamConfig()
  if (!config.ok) {
    return config
  }

  let response: Response
  try {
    response = await fetch(
      `${config.data.baseUrl}/api/alerts/${parsedId.data}/action`,
      {
        method: 'PATCH',
        headers: {
          Authorization: `Bearer ${config.data.apiKey}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action_taken: action }),
        signal: upstreamRequestSignal(),
      }
    )
  } catch {
    return upstreamTransportFailure()
  }

  if (!response.ok) {
    if (process.env.NODE_ENV === 'development') {
      console.error('[BFF] updateAlertAction upstream non-OK', {
        status: response.status,
      })
    }
    if (response.status === 401 || response.status === 403) {
      return err(
        500,
        'INTERNAL_SERVICE_AUTH_FAILED',
        'Internal service authentication failed.'
      )
    }

    if (response.status === 404) {
      return err(404, 'NOT_FOUND', 'Requested resource was not found.')
    }

    if (response.status >= 500) {
      return err(response.status, 'UPSTREAM_ERROR', 'Upstream service failed.')
    }

    return err(response.status, 'UPSTREAM_ERROR', 'Upstream request failed.')
  }

  let payload: unknown
  try {
    payload = await response.json()
  } catch {
    return err(502, 'UPSTREAM_ERROR', 'Upstream service failed.')
  }

  const parsed = BackendAlertSchema.safeParse(payload)
  if (!parsed.success) {
    return err(
      502,
      'UPSTREAM_ERROR',
      'Upstream response did not match expected shape.'
    )
  }

  return normalizeAlert(parsed.data)
}
