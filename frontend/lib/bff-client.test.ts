import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const fetchMock = vi.fn()

vi.mock('server-only', () => ({}))

vi.stubGlobal('fetch', fetchMock)

async function loadClient() {
  vi.resetModules()
  return import('./bff-client')
}

describe('bff-client', () => {
  const originalEnv = process.env

  beforeEach(() => {
    process.env = {
      ...originalEnv,
      USE_MOCK_API: 'false',
      FASTAPI_BASE_URL: 'http://localhost:8000',
      INTERNAL_API_KEY: 'test-secret',
    }
    fetchMock.mockReset()
  })

  afterEach(() => {
    process.env = originalEnv
    vi.doUnmock('@/mocks/alerts')
  })

  it('maps alerts list pagination and field names from FastAPI', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: 7,
              timestamp: '2026-03-15T00:00:00Z',
              source_ip: '203.0.113.10',
              request_path: '/login',
              request_method: 'POST',
              payload_snippet: "username=admin' OR '1'='1",
              prediction: 'SQL Injection',
              confidence: 0.91,
              confidence_level: 'HIGH',
              action_taken: 'BLOCKED',
              crs_score: 9,
              crs_rule_ids: ['942100', '942110'],
              analyst_label: 'SQL Injection',
              labeled_at: '2026-03-15T00:05:00Z',
              labeled_by: 'analyst@lares.test',
            },
          ],
          total: 12,
          page: 2,
          page_size: 5,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getAlerts } = await loadClient()
    const result = await getAlerts(
      new URLSearchParams({
        page: '2',
        pageSize: '5',
        severity: 'HIGH',
        window: '24h',
        search: '203.0.113.10',
      })
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/alerts?page=2&page_size=5&severity=HIGH&search=203.0.113.10&window=24h',
      expect.objectContaining({
        cache: 'no-store',
        headers: {
          Authorization: 'Bearer test-secret',
          'Content-Type': 'application/json',
        },
      })
    )
    expect(result).toEqual({
      ok: true,
      data: {
        items: [
          {
            alert_id: '7',
            timestamp: '2026-03-15T00:00:00Z',
            source_ip: '203.0.113.10',
            request_path: '/login',
            request_method: 'POST',
            payload_snippet: "username=admin' OR '1'='1",
            prediction: 'SQL Injection',
            confidence: 0.91,
            confidence_level: 'HIGH',
            action_taken: 'BLOCKED',
            crs_score: 9,
            crs_rule_ids: ['942100', '942110'],
            analyst_label: 'SQL Injection',
            labeled_at: '2026-03-15T00:05:00Z',
            labeled_by: 'analyst@lares.test',
            triage_status: null,
          },
        ],
        total: 12,
        page: 2,
        pageSize: 5,
      },
    })
  })

  it('preserves nullable alert fields and missing action_taken without inventing defaults', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: 8,
              timestamp: '2026-03-15T00:00:00Z',
              source_ip: null,
              request_path: null,
              request_method: null,
              payload_snippet: 'payload',
              prediction: 'Normal',
              confidence: 0.12,
              confidence_level: 'LOW',
              crs_score: null,
              crs_rule_ids: null,
              analyst_label: null,
              labeled_at: null,
              labeled_by: null,
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getAlerts } = await loadClient()
    const result = await getAlerts(new URLSearchParams())

    expect(result).toEqual({
      ok: true,
      data: {
        items: [
          {
            alert_id: '8',
            timestamp: '2026-03-15T00:00:00Z',
            source_ip: null,
            request_path: null,
            request_method: null,
            payload_snippet: 'payload',
            prediction: 'Normal',
            confidence: 0.12,
            confidence_level: 'LOW',
            action_taken: null,
            crs_score: undefined,
            crs_rule_ids: null,
            analyst_label: null,
            labeled_at: null,
            labeled_by: null,
            triage_status: null,
          },
        ],
        total: 1,
        page: 1,
        pageSize: 20,
      },
    })
  })

  it('propagates alert detail 404 as NOT_FOUND', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 404 }))

    const { getAlertDetail } = await loadClient()
    const result = await getAlertDetail('99')

    expect(result).toEqual({
      ok: false,
      status: 404,
      error: {
        code: 'NOT_FOUND',
        message: 'Requested resource was not found.',
      },
    })
  })

  it('rejects non-digit alert ids locally with 400 before fetch', async () => {
    const { getAlertDetail } = await loadClient()
    const result = await getAlertDetail('NaN')

    expect(fetchMock).not.toHaveBeenCalled()
    expect(result).toEqual({
      ok: false,
      status: 400,
      error: {
        code: 'INVALID_ID',
        message: 'Alert ID must be a valid number.',
      },
    })
  })

  it('rejects whitespace-only alert ids locally with 400 before fetch', async () => {
    const { getAlertDetail } = await loadClient()
    const result = await getAlertDetail('   ')

    expect(fetchMock).not.toHaveBeenCalled()
    expect(result).toEqual({
      ok: false,
      status: 400,
      error: {
        code: 'INVALID_ID',
        message: 'Alert ID must be a valid number.',
      },
    })
  })

  it('rejects zero-like alert ids locally with 400 before fetch', async () => {
    const { getAlertDetail } = await loadClient()
    const result = await getAlertDetail('0')

    expect(fetchMock).not.toHaveBeenCalled()
    expect(result).toEqual({
      ok: false,
      status: 400,
      error: {
        code: 'INVALID_ID',
        message: 'Alert ID must be a valid number.',
      },
    })
  })

  it('maps stats and preserves total_requests', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          total_requests: 321,
          counts_by_label: {
            'SQL Injection': 2,
            'Code Injection': 1,
            'Other Attacks': 3,
            Normal: 10,
          },
          avg_inference_latency_ms: 4.5,
          blocked_count: 4,
          allowed_count: 2,
          avg_confidence: 0.82,
          activity_buckets: [
            { bucket_index: 0, total_count: 10, blocked_count: 2, timestamp_start: '2026-03-18T12:00:00Z' },
            { bucket_index: 1, total_count: 15, blocked_count: 3, timestamp_start: '2026-03-18T13:00:00Z' },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getStats } = await loadClient()
    const result = await getStats()

    expect(result).toEqual({
      ok: true,
      data: {
        actionable_alerts: 6,
        total_requests: 321,
        avg_inference_latency_ms: 4.5,
        blocked_count: 4,
        allowed_count: 2,
        throttled_count: 0,
        avg_confidence: 0.82,
        activity_buckets: [
          { bucket_index: 0, total_count: 10, blocked_count: 2, timestamp_start: new Date('2026-03-18T12:00:00Z') },
          { bucket_index: 1, total_count: 15, blocked_count: 3, timestamp_start: new Date('2026-03-18T13:00:00Z') },
        ],
        attack_distribution: {},
        top_source_ips: [],
        top_targeted_paths: [],
      },
    })
  })

  it('maps ml-health shape and preserves healthy/degraded semantics', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          model_version: 'distilbert-v1',
          loaded: true,
          status: 'degraded',
          avg_inference_latency_ms: 6.2,
          total_processed: 42,
          drift_detected: false,
          drift_score: 0.05, // Real drift data available
          confidence_thresholds: {
            low: 0.5,
            high: 0.8,
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getMlHealth } = await loadClient()
    const result = await getMlHealth()

    expect(result).toEqual({
      ok: true,
      data: {
        model_version: 'distilbert-v1',
        status: 'DEGRADED',
        latency_ms: 6.2,
        latency_trend: null,
        drift_score: 0.05,
        drift_status: 'NORMAL', // With real drift data, false = NORMAL
        traffic_processed: 42,
        thresholds: {
          low: 0.5,
          medium: 0.65,
          high: 0.8,
        },
        // Optional eval metadata defaults when not provided
        macro_f1: null,
        ece: null,
        per_class_f1: {},
        calibration_bins: [],
        prediction_distribution: {},
      },
    })
  })

  it('returns structured upstream error when normalization fails schema validation', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: 9,
              timestamp: '2026-03-15T00:00:00Z',
              source_ip: null,
              request_path: null,
              request_method: null,
              payload_snippet: 'payload',
              prediction: 'Not A Real Label',
              confidence: 0.12,
              confidence_level: 'LOW',
            },
          ],
          total: 1,
          page: 1,
          page_size: 20,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getAlerts } = await loadClient()
    const result = await getAlerts(new URLSearchParams())

    expect(result).toEqual({
      ok: false,
      status: 502,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream response did not match expected shape.',
      },
    })
  })

  it('returns structured upstream error on FastAPI 5xx', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 503 }))

    const { getStats } = await loadClient()
    const result = await getStats()

    expect(result).toEqual({
      ok: false,
      status: 503,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream service failed.',
      },
    })
  })

  it('returns BFF_MISCONFIGURED before constructing fetch when env is missing', async () => {
    delete process.env.FASTAPI_BASE_URL

    const { getStats } = await loadClient()
    const result = await getStats()

    expect(fetchMock).not.toHaveBeenCalled()
    expect(result).toEqual({
      ok: false,
      status: 500,
      error: {
        code: 'BFF_MISCONFIGURED',
        message: 'Server configuration is incomplete.',
      },
    })
  })

  it('returns INTERNAL_SERVICE_AUTH_FAILED when upstream returns 401 (internal auth failure)', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 401 }))

    const { getStats } = await loadClient()
    const result = await getStats()

    // Upstream 401 means the internal API key is invalid/missing/expired,
    // not that the browser user is unauthorized.
    // Note: retryAfter is NOT attached for auth failures (not a "wait and retry" scenario)
    expect(result).toEqual({
      ok: false,
      status: 500,
      error: {
        code: 'INTERNAL_SERVICE_AUTH_FAILED',
        message: 'Internal service authentication failed.',
      },
    })
  })

  it('returns INTERNAL_SERVICE_AUTH_FAILED when upstream returns 403 (internal auth failure)', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 403 }))

    const { getStats } = await loadClient()
    const result = await getStats()

    // Upstream 403 means the internal API key lacks permissions,
    // not that the browser user is forbidden.
    // Note: retryAfter is NOT attached for auth failures (not a "wait and retry" scenario)
    expect(result).toEqual({
      ok: false,
      status: 500,
      error: {
        code: 'INTERNAL_SERVICE_AUTH_FAILED',
        message: 'Internal service authentication failed.',
      },
    })
  })

  it('returns UPSTREAM_ERROR with 400 status when upstream returns 400', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 400 }))

    const { getAlerts } = await loadClient()
    const result = await getAlerts(new URLSearchParams())

    expect(result).toEqual({
      ok: false,
      status: 400,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream request failed.',
      },
    })
  })

  it('uses centralized mock mode with locked contract shapes', async () => {
    process.env.USE_MOCK_API = 'true'

    const { getAlerts, getStats, getMlHealth } = await loadClient()
    const alerts = await getAlerts(new URLSearchParams())
    const stats = await getStats()
    const mlHealth = await getMlHealth()

    expect(fetchMock).not.toHaveBeenCalled()
    expect(alerts.ok).toBe(true)
    expect(stats.ok).toBe(true)
    expect(mlHealth.ok).toBe(true)

    if (alerts.ok) {
      expect(alerts.data.items[0].action_taken).toBe('BLOCKED')
      expect(alerts.data.pageSize).toBe(20)
    }

    if (stats.ok) {
      expect(stats.data.total_requests).toBe(8400000)
    }

    if (mlHealth.ok) {
      expect(mlHealth.data.status).toBe('HEALTHY')
    }
  })

  it('returns INVALID_MOCK_DATA when mock alerts list does not match the contract', async () => {
    process.env.USE_MOCK_API = 'true'
    vi.doMock('@/mocks/alerts', () => ({
      MOCK_ALERTS: {
        items: [],
        total: 'bad-total',
        page: 1,
        pageSize: 20,
      },
    }))

    const { getAlerts } = await loadClient()
    const result = await getAlerts(new URLSearchParams())

    expect(result).toEqual({
      ok: false,
      status: 500,
      error: {
        code: 'INVALID_MOCK_DATA',
        message: 'Mock data does not match expected contract.',
      },
    })
  })

  it('returns INVALID_MOCK_DATA when mock alert detail does not match the contract', async () => {
    process.env.USE_MOCK_API = 'true'
    vi.doMock('@/mocks/alerts', () => ({
      MOCK_ALERTS: {
        items: [
          {
            alert_id: '1',
            timestamp: '2026-03-15T00:00:00Z',
            source_ip: '203.0.113.10',
            request_path: '/login',
            request_method: 'POST',
            payload_snippet: 'payload',
            prediction: 'SQL Injection',
            confidence: 0.9,
            confidence_level: 'HIGH',
            action_taken: 'INVALID_ACTION',
          },
        ],
        total: 1,
        page: 1,
        pageSize: 20,
      },
    }))

    const { getAlertDetail } = await loadClient()
    const result = await getAlertDetail('1')

    expect(result).toEqual({
      ok: false,
      status: 500,
      error: {
        code: 'INVALID_MOCK_DATA',
        message: 'Mock data does not match expected contract.',
      },
    })
  })
})
