import 'server-only'

import { z } from 'zod'
import { AlertSchema, PaginatedAlertsSchema } from '@/features/alerts/schemas'
import type { Alert, PaginatedAlerts } from '@/features/alerts/types'
import type { MLHealthData } from '@/features/ml-health/types'
import type { DashboardStats } from '@/features/stats/types'
import { MOCK_ALERTS } from '@/mocks/alerts'
import { MOCK_ML_HEALTH } from '@/mocks/ml-health'
import { MOCK_STATS } from '@/mocks/stats'

export interface BffError {
  code: string
  message: string
}

export type BffResult<T> =
  | { ok: true; data: T }
  | { ok: false; status: number; error: BffError }

const BackendAlertSchema = z.object({
  id: z.number(),
  timestamp: z.string(),
  source_ip: z.string().nullable().optional(),
  request_path: z.string().nullable().optional(),
  request_method: z.string().nullable().optional(),
  payload_snippet: z.string(),
  prediction: z.enum(['SQL Injection', 'Code Injection', 'Other Attacks', 'Normal']),
  confidence: z.number(),
  confidence_level: z.enum(['LOW', 'MEDIUM', 'HIGH']),
  action_taken: z.enum(['BLOCKED', 'THROTTLED', 'ALLOWED']).nullable().optional(),
  crs_score: z.number().nullable().optional(),
  crs_rule_ids: z.array(z.string()).nullable().optional(),
  analyst_label: z.string().nullable().optional(),
  labeled_at: z.string().nullable().optional(),
  labeled_by: z.string().nullable().optional(),
})

const BackendPaginatedAlertsSchema = z.object({
  items: z.array(BackendAlertSchema),
  total: z.number(),
  page: z.number(),
  page_size: z.number(),
})

const BackendStatsSchema = z.object({
  total_requests: z.number(),
  counts_by_label: z.object({
    'SQL Injection': z.number(),
    'Code Injection': z.number(),
    'Other Attacks': z.number(),
    Normal: z.number(),
  }),
  avg_inference_latency_ms: z.number(),
})

const BackendMlHealthSchema = z.object({
  model_version: z.string(),
  loaded: z.boolean(),
  status: z.enum(['healthy', 'degraded']),
  avg_inference_latency_ms: z.number(),
  total_processed: z.number(),
  drift_detected: z.boolean(),
  confidence_thresholds: z.object({
    low: z.number().optional(),
    high: z.number().optional(),
  }),
})

function ok<T>(data: T): BffResult<T> {
  return { ok: true, data }
}

function err<T>(status: number, code: string, message: string): BffResult<T> {
  return { ok: false, status, error: { code, message } }
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

function normalizeWithSchema<T>(
  schema: z.ZodType<T>,
  payload: unknown
): BffResult<T> {
  const parsed = schema.safeParse(payload)
  if (!parsed.success) {
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
    analyst_label: alert.analyst_label ?? null,
    labeled_at: alert.labeled_at ?? null,
    labeled_by: alert.labeled_by ?? null,
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

function normalizeStats(payload: z.infer<typeof BackendStatsSchema>): DashboardStats {
  const actionableAlerts =
    (payload.counts_by_label['SQL Injection'] ?? 0) +
    (payload.counts_by_label['Code Injection'] ?? 0) +
    (payload.counts_by_label['Other Attacks'] ?? 0)

  return {
    actionable_alerts: actionableAlerts,
    total_requests: payload.total_requests,
    avg_inference_latency_ms: payload.avg_inference_latency_ms,
  }
}

function normalizeMlHealth(
  payload: z.infer<typeof BackendMlHealthSchema>
): MLHealthData {
  // BFF validation: ensure thresholds are valid
  const low = payload.confidence_thresholds.low
  const high = payload.confidence_thresholds.high
  let medium: number | null = null

  if (typeof low === 'number' && typeof high === 'number') {
    // BFF check: validate threshold range (0-1 or 0-100)
    const normalizedLow = low <= 1 ? low : low / 100
    const normalizedHigh = high <= 1 ? high : high / 100

    // BFF check: ensure low < high
    if (normalizedLow >= normalizedHigh) {
      console.warn('[BFF] Invalid thresholds: low >= high, using defaults')
    } else {
      // BFF transform: derive medium from low/high range
      medium = (normalizedLow + normalizedHigh) / 2
    }
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
    drift_score: null,
    drift_status: payload.drift_detected ? 'WARNING' : 'NORMAL',
    traffic_processed: payload.total_processed,
    thresholds: {
      low: low ?? null,
      medium,
      high: high ?? null,
    },
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
    })
  } catch {
    return err(500, 'INTERNAL_ERROR', 'An unexpected error occurred.')
  }

  if (!response.ok) {
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

export async function getAlerts(
  searchParams: URLSearchParams
): Promise<BffResult<PaginatedAlerts>> {
  if (isMockMode()) {
    return validateMockData(PaginatedAlertsSchema, MOCK_ALERTS)
  }

  const query = new URLSearchParams()
  for (const key of ['page', 'page_size', 'severity', 'time_range', 'search']) {
    const value = searchParams.get(key)
    if (value) {
      query.set(key, value)
    }
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

export async function getStats(): Promise<BffResult<DashboardStats>> {
  if (isMockMode()) {
    return ok(MOCK_STATS)
  }

  const upstream = await fetchUpstream('/api/stats', BackendStatsSchema)
  if (!upstream.ok) {
    return upstream
  }

  return ok(normalizeStats(upstream.data))
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
