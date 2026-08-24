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

  it('keeps retraining BFF calls server-authenticated and schema validated', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          active_model_version: 'active-v1',
          latest_run_state: 'queued',
          approved_count: 2,
          unreviewed_count: 1,
          excluded_count: 0,
          latest_dataset_version: null,
          run_in_progress: true,
          last_trigger_time: '2026-08-11T12:00:00Z',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getRetrainingSummary, startRetrainingRun, getRetrainingRun } = await loadClient()
    const summary = await getRetrainingSummary()
    const invalidRequest = await startRetrainingRun(
      { trigger: 'manual', filesystem_path: 'C:/outside' },
      { id: 'analyst-1', role: 'ANALYST' }
    )
    const invalidRun = await getRetrainingRun('../outside', {
      id: 'analyst-1',
      role: 'ANALYST',
    })

    expect(summary.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/retraining/summary',
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer test-secret',
          'Content-Type': 'application/json',
        },
      })
    )
    expect(invalidRequest).toEqual({
      ok: false,
      status: 400,
      error: { code: 'INVALID_REQUEST', message: 'Invalid retraining request.' },
    })
    expect(invalidRun).toEqual({
      ok: false,
      status: 400,
      error: { code: 'INVALID_RUN_ID', message: 'Retraining run ID is invalid.' },
    })
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })

  it('forwards an explicitly supplied requester timezone instead of the server timezone', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: 'retrain-20260811T120000Z-000000000001',
          state: 'queued',
          stage: 'queued',
          created: true,
          attempt: 0,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { startRetrainingRun } = await loadClient()
    const result = await startRetrainingRun(
      { trigger: 'manual' },
      { id: 'analyst-1', role: 'ANALYST' },
      'America/New_York'
    )

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/retraining/runs',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Requester-Timezone': 'America/New_York',
        }),
      })
    )
  })

  it('rejects an invalid requester timezone before calling the backend', async () => {
    const { startRetrainingRun } = await loadClient()

    const result = await startRetrainingRun(
      { trigger: 'manual' },
      { id: 'analyst-1', role: 'ANALYST' },
      'not/a-real-timezone'
    )

    expect(result).toEqual({
      ok: false,
      status: 400,
      error: { code: 'INVALID_REQUEST', message: 'Requester timezone is invalid.' },
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('propagates the authenticated actor for retraining run reads', async () => {
    const run = {
      run_id: 'retrain-20260811T120000Z-000000000001',
      state: 'queued',
      stage: 'queued',
      attempt: 0,
      retry_count: 0,
      max_retries: 2,
      created_at: '2026-08-11T12:00:00.000Z',
      updated_at: '2026-08-11T12:00:00.000Z',
      heartbeat_at: null,
      trigger: 'manual',
      requested_by: 'analyst-1',
      requested_timezone: 'Asia/Manila',
      input_fingerprint: 'a'.repeat(64),
      source_review_revisions: [],
      source_dataset_version: 'v3_907k_cleaned',
      source_dataset_digest: 'b'.repeat(64),
      pipeline_fingerprint: 'c'.repeat(64),
      active_model_version: 'active-v1',
      active_model_digest: 'd'.repeat(64),
      approved_sample_count: 0,
      operator_note: null,
      worker_id: null,
      next_retry_at: null,
      dataset_version: null,
      dataset_digest: null,
      candidate_model_version: null,
      candidate_model_digest: null,
      evaluation_digest: null,
      error_code: null,
      error_message: null,
      generation: 1,
    }
    fetchMock
      .mockResolvedValueOnce(
        new Response(JSON.stringify({ runs: [] }), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            ...run,
            events: [],
            heartbeat_age_seconds: null,
            evidence_status: 'NOT_RUN',
            retry_available: false,
          }),
          { status: 200, headers: { 'Content-Type': 'application/json' } }
        )
      )

    const { getRetrainingRuns, getRetrainingRun } = await loadClient()
    const actor = { id: 'analyst-1', role: 'ANALYST' }
    expect((await getRetrainingRuns(actor)).ok).toBe(true)
    expect((await getRetrainingRun(run.run_id, actor)).ok).toBe(true)

    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      'http://localhost:8000/api/retraining/runs',
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer test-secret',
          'Content-Type': 'application/json',
          'X-Reviewer-Id': 'analyst-1',
          'X-Reviewer-Role': 'ANALYST',
        },
      })
    )
    expect(fetchMock).toHaveBeenNthCalledWith(
      2,
      `http://localhost:8000/api/retraining/runs/${run.run_id}`,
      expect.objectContaining({
        headers: {
          Authorization: 'Bearer test-secret',
          'Content-Type': 'application/json',
          'X-Reviewer-Id': 'analyst-1',
          'X-Reviewer-Role': 'ANALYST',
        },
      })
    )
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
              ingest_source: 'modsec_audit_bridge',
              matched_rule_messages: ['SQL Injection Attack Detected via libinjection'],
              matched_rule_tags: ['attack-sqli', 'paranoia-level/1'],
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
        timeRange: '24h',
        search: '203.0.113.10',
      })
    )

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/alerts?page=2&page_size=5&severity=HIGH&search=203.0.113.10&time_range=24h',
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
            ingest_source: 'modsec_audit_bridge',
            matched_rule_messages: ['SQL Injection Attack Detected via libinjection'],
            matched_rule_tags: ['attack-sqli', 'paranoia-level/1'],
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

  it('prefers confidence_tier when forwarding the alerts filter to FastAPI', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getAlerts } = await loadClient()
    const result = await getAlerts(
      new URLSearchParams({
        confidence_tier: 'HIGH',
        page: '1',
      })
    )

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/alerts?page=1&confidence_tier=HIGH',
      expect.any(Object)
    )
  })

  it('accepts CRITICAL confidence tiers from FastAPI alert payloads', async () => {
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
              confidence: 0.97,
              confidence_level: 'CRITICAL',
              action_taken: 'BLOCKED',
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
    const result = await getAlerts(new URLSearchParams({ confidence_tier: 'CRITICAL' }))

    expect(result.ok).toBe(true)
    if (!result.ok) {
      return
    }

    expect(result.data.items[0]?.confidence_level).toBe('CRITICAL')
  })

  it('rejects unsupported confidence tiers from FastAPI alert payloads', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [
            {
              id: 8,
              timestamp: '2026-03-15T00:00:00Z',
              source_ip: '203.0.113.11',
              request_path: '/login',
              request_method: 'POST',
              payload_snippet: 'payload',
              prediction: 'SQL Injection',
              confidence: 0.99,
              confidence_level: 'EXTREME',
              action_taken: 'BLOCKED',
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

  it('forwards both severity and confidence_tier when both exist', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [],
          total: 0,
          page: 1,
          page_size: 20,
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getAlerts } = await loadClient()
    const result = await getAlerts(
      new URLSearchParams({
        severity: 'LOW',
        confidence_tier: 'HIGH',
      })
    )

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/alerts?severity=LOW&confidence_tier=HIGH',
      expect.any(Object)
    )
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
            ingest_source: null,
            matched_rule_messages: null,
            matched_rule_tags: null,
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

  it('preserves upstream 404 as NOT_FOUND when updating alert action', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 404 }))

    const { updateAlertAction } = await loadClient()
    const result = await updateAlertAction('99', 'BLOCKED')

    expect(result).toEqual({
      ok: false,
      status: 404,
      error: {
        code: 'NOT_FOUND',
        message: 'Requested resource was not found.',
      },
    })
  })

  it('returns 502 UPSTREAM_ERROR when action update payload fails schema validation', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: 1,
          timestamp: '2026-03-15T00:00:00Z',
          payload_snippet: 'payload',
          prediction: 'SQL Injection',
          confidence: 0.9,
          confidence_level: 'HIGH',
          action_taken: 'NOT_A_REAL_ACTION',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { updateAlertAction } = await loadClient()
    const result = await updateAlertAction('1', 'BLOCKED')

    expect(result).toEqual({
      ok: false,
      status: 502,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream response did not match expected shape.',
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
          prev_high_alert_count: 123,
          activity_buckets: [
            { bucket_index: 0, total_count: 10, blocked_count: 2, allowed_count: 7, throttled_count: 1, timestamp_start: '2026-03-18T12:00:00Z', timestamp_end: '2026-03-18T13:00:00Z', bucket_width_seconds: 3600 },
            { bucket_index: 1, total_count: 15, blocked_count: 3, allowed_count: 11, throttled_count: 1, timestamp_start: '2026-03-18T13:00:00Z', timestamp_end: '2026-03-18T14:00:00Z', bucket_width_seconds: 3600 },
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
        false_positive_rate: 0,
        false_positive_count: 0,
        high_alert_count: 6,
        prev_high_alert_count: 123,
        prev_total_requests: null,
        prev_blocked_count: null,
        prev_allowed_count: null,
        prev_throttled_count: null,
        activity_buckets: [
          { bucket_index: 0, total_count: 10, blocked_count: 2, allowed_count: 7, throttled_count: 1, timestamp_start: '2026-03-18T12:00:00Z', timestamp_end: '2026-03-18T13:00:00Z', bucket_width_seconds: 3600 },
          { bucket_index: 1, total_count: 15, blocked_count: 3, allowed_count: 11, throttled_count: 1, timestamp_start: '2026-03-18T13:00:00Z', timestamp_end: '2026-03-18T14:00:00Z', bucket_width_seconds: 3600 },
        ],
        attack_distribution: {},
        top_source_ips: [],
        top_targeted_paths: [],
      },
    })
  })

  it('propagates window parameter when fetching stats', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          total_requests: 0,
          counts_by_label: {
            'SQL Injection': 0,
            'Code Injection': 0,
            'Other Attacks': 0,
            Normal: 0,
          },
          avg_inference_latency_ms: 0,
          blocked_count: 0,
          allowed_count: 0,
          throttled_count: 0,
          avg_confidence: null,
          activity_buckets: [],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getStats } = await loadClient()
    const result = await getStats('6h')

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/stats?window=6h',
      expect.any(Object)
    )
  })

  it('propagates timezone_name parameter when fetching stats', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          total_requests: 0,
          counts_by_label: {
            'SQL Injection': 0,
            'Code Injection': 0,
            'Other Attacks': 0,
            Normal: 0,
          },
          avg_inference_latency_ms: 0,
          blocked_count: 0,
          allowed_count: 0,
          throttled_count: 0,
          avg_confidence: null,
          activity_buckets: [],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getStats } = await loadClient()
    const result = await getStats('6h', 'Asia/Manila')

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/stats?window=6h&timezone_name=Asia%2FManila',
      expect.any(Object)
    )
  })

  it.each([
    'UTC',
    'Etc/GMT+8',
    'America/Argentina/Buenos_Aires',
  ])('forwards valid timezone_name %s', async (zone) => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          total_requests: 0,
          counts_by_label: {
            'SQL Injection': 0,
            'Code Injection': 0,
            'Other Attacks': 0,
            Normal: 0,
          },
          avg_inference_latency_ms: 0,
          blocked_count: 0,
          allowed_count: 0,
          throttled_count: 0,
          avg_confidence: null,
          activity_buckets: [],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getStats } = await loadClient()
    const result = await getStats('6h', zone)

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      `http://localhost:8000/api/stats?window=6h&timezone_name=${encodeURIComponent(zone)}`,
      expect.any(Object)
    )
  })

  it('omits invalid timezone_name values when fetching stats', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          total_requests: 0,
          counts_by_label: {
            'SQL Injection': 0,
            'Code Injection': 0,
            'Other Attacks': 0,
            Normal: 0,
          },
          avg_inference_latency_ms: 0,
          blocked_count: 0,
          allowed_count: 0,
          throttled_count: 0,
          avg_confidence: null,
          activity_buckets: [],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getStats } = await loadClient()
    const result = await getStats('6h', 'Not/AZone')

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/stats?window=6h',
      expect.any(Object)
    )
    expect(fetchMock).not.toHaveBeenCalledWith(
      expect.stringContaining('timezone_name='),
      expect.any(Object)
    )
  })

  it('sets a timeout signal for triage mutation requests', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
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
          triage_status: 'in_review',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { updateAlertTriage } = await loadClient()
    const result = await updateAlertTriage('7', 'in_review')

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/alerts/7/triage',
      expect.objectContaining({
        method: 'PATCH',
        signal: expect.any(AbortSignal),
      })
    )
  })

  it('sorts activity buckets by timestamp_start to keep timeline order stable', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          total_requests: 2,
          counts_by_label: {
            'SQL Injection': 1,
            'Code Injection': 0,
            'Other Attacks': 0,
            Normal: 1,
          },
          avg_inference_latency_ms: 3,
          blocked_count: 1,
          allowed_count: 1,
          throttled_count: 0,
          avg_confidence: 0.6,
          activity_buckets: [
            { bucket_index: 1, total_count: 1, blocked_count: 1, allowed_count: 0, throttled_count: 0, timestamp_start: '2026-03-18T13:00:00Z', timestamp_end: '2026-03-18T14:00:00Z', bucket_width_seconds: 3600 },
            { bucket_index: 0, total_count: 1, blocked_count: 0, allowed_count: 1, throttled_count: 0, timestamp_start: '2026-03-18T12:00:00Z', timestamp_end: '2026-03-18T13:00:00Z', bucket_width_seconds: 3600 },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getStats } = await loadClient()
    const result = await getStats('24h')

    expect(result.ok).toBe(true)
    if (!result.ok) {
      return
    }

    expect(result.data.activity_buckets[0].timestamp_start).toBe('2026-03-18T12:00:00Z')
    expect(result.data.activity_buckets[1].timestamp_start).toBe('2026-03-18T13:00:00Z')
  })

  it('returns UPSTREAM_ERROR when stats contain invalid bucket timestamp', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          total_requests: 1,
          counts_by_label: {
            'SQL Injection': 1,
            'Code Injection': 0,
            'Other Attacks': 0,
            Normal: 0,
          },
          avg_inference_latency_ms: 3,
          blocked_count: 1,
          allowed_count: 0,
          throttled_count: 0,
          avg_confidence: 0.9,
          activity_buckets: [
            {
              bucket_index: 0,
              total_count: 1,
              blocked_count: 1,
              allowed_count: 0,
              throttled_count: 0,
              timestamp_start: 'not-a-timestamp',
              timestamp_end: '2026-03-18T13:00:00Z',
            },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getStats } = await loadClient()
    const result = await getStats('24h')

    expect(result).toEqual({
      ok: false,
      status: 502,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream response contained invalid bucket timestamp at index 0: not-a-timestamp',
      },
    })
  })

  it('applies deterministic ordering when bucket timestamps are identical', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          total_requests: 2,
          counts_by_label: {
            'SQL Injection': 0,
            'Code Injection': 0,
            'Other Attacks': 0,
            Normal: 2,
          },
          avg_inference_latency_ms: 1.5,
          blocked_count: 0,
          allowed_count: 2,
          throttled_count: 0,
          avg_confidence: 0.2,
          activity_buckets: [
            { bucket_index: 2, total_count: 1, blocked_count: 0, allowed_count: 1, throttled_count: 0, timestamp_start: '2026-03-18T12:00:00Z', timestamp_end: '2026-03-18T13:00:00Z', bucket_width_seconds: 3600 },
            { bucket_index: 1, total_count: 1, blocked_count: 0, allowed_count: 1, throttled_count: 0, timestamp_start: '2026-03-18T12:00:00Z', timestamp_end: '2026-03-18T13:00:00Z', bucket_width_seconds: 3600 },
          ],
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getStats } = await loadClient()
    const result = await getStats('24h')

    expect(result.ok).toBe(true)
    if (!result.ok) {
      return
    }

    expect(result.data.activity_buckets.map((bucket) => bucket.bucket_index)).toEqual([1, 2])
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
            critical: 0.9,
          },
          queue: {
            enabled: true,
            max_size: 100,
            depth: 0,
            available_capacity: 100,
            worker_count: 1,
            worker_running: true,
            total_enqueued: 4,
            total_processed: 4,
            total_failed: 0,
            overflow_count: 0,
            last_error: null,
            last_error_at: null,
            last_processed_at: '2026-06-24T10:00:00+00:00',
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
          critical: 0.9,
        },
        // Optional eval metadata defaults when not provided
        macro_f1: null,
        ece: null,
        per_class_f1: {},
        calibration_bins: [],
        prediction_distribution: { baseline: {}, current: {} },
        queue: {
          enabled: true,
          max_size: 100,
          depth: 0,
          available_capacity: 100,
          worker_count: 1,
          worker_running: true,
          total_enqueued: 4,
          total_processed: 4,
          total_failed: 0,
          overflow_count: 0,
          last_error: null,
          last_error_at: null,
          last_processed_at: '2026-06-24T10:00:00+00:00',
        },
      },
    })
  })

  it('normalizes flat ml-health prediction_distribution payloads from backend', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          model_version: 'distilbert-v1',
          loaded: true,
          status: 'healthy',
          avg_inference_latency_ms: 2.1,
          total_processed: 8,
          drift_detected: false,
          drift_score: null,
          confidence_thresholds: {
            low: 0.5,
            high: 0.8,
            critical: 0.9,
          },
          prediction_distribution: {
            sqli: 3,
            benign: 5,
          },
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { getMlHealth } = await loadClient()
    const result = await getMlHealth()

    expect(result.ok).toBe(true)
    if (!result.ok) {
      return
    }

    expect(result.data.prediction_distribution).toEqual({
      baseline: {},
      current: {
        sqli: 3,
        benign: 5,
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

  it('bounds ordinary BFF reads and maps transport failure to the upstream contract', async () => {
    fetchMock.mockRejectedValueOnce(new DOMException('timed out', 'TimeoutError'))

    const { getStats } = await loadClient()
    const result = await getStats()

    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/stats',
      expect.objectContaining({ signal: expect.any(AbortSignal) })
    )
    expect(result).toEqual({
      ok: false,
      status: 502,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream service failed.',
      },
    })
  })

  it('maps mutation transport failures consistently and bounds every request', async () => {
    fetchMock.mockRejectedValue(new TypeError('connection failed'))

    const { submitAlertLabelReview, updateAlertAction, updateAlertTriage } =
      await loadClient()
    const results = [
      await submitAlertLabelReview(
        '7',
        { verified_label: 'Normal', approval_state: 'excluded_from_training' },
        { id: 'analyst-1', role: 'ANALYST' }
      ),
      await updateAlertTriage('7', 'in_review'),
      await updateAlertAction('7', 'BLOCKED'),
    ]

    expect(results).toEqual(
      Array.from({ length: 3 }, () => ({
        ok: false,
        status: 502,
        error: {
          code: 'UPSTREAM_ERROR',
          message: 'Upstream service failed.',
        },
      }))
    )
    expect(fetchMock).toHaveBeenCalledTimes(3)
    for (const [, options] of fetchMock.mock.calls) {
      expect(options).toEqual(expect.objectContaining({ signal: expect.any(AbortSignal) }))
    }
  })

  it('does not log upstream response data when schema validation fails', async () => {
    process.env = { ...process.env, NODE_ENV: 'development' }
    const log = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const sensitiveValue = 'raw-sensitive-upstream-value'
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ unexpected: sensitiveValue }), {
        status: 200,
        headers: { 'Content-Type': 'application/json' },
      })
    )

    const { getStats } = await loadClient()
    const result = await getStats()

    expect(result).toEqual({
      ok: false,
      status: 502,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream response did not match expected shape.',
      },
    })
    expect(JSON.stringify(log.mock.calls)).not.toContain(sensitiveValue)
  })

  it('does not log alert query values or upstream error bodies', async () => {
    process.env = { ...process.env, NODE_ENV: 'development' }
    const info = vi.spyOn(console, 'log').mockImplementation(() => undefined)
    const error = vi.spyOn(console, 'error').mockImplementation(() => undefined)
    const sensitiveQuery = 'operator-search-secret'
    const sensitiveBody = 'backend-diagnostic-secret'
    fetchMock.mockResolvedValueOnce(new Response(sensitiveBody, { status: 500 }))

    const { getAlerts } = await loadClient()
    await getAlerts(new URLSearchParams({ search: sensitiveQuery }))

    const output = JSON.stringify([...info.mock.calls, ...error.mock.calls])
    expect(output).not.toContain(sensitiveQuery)
    expect(output).not.toContain(sensitiveBody)
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

  it('submits a verified label review with server-derived identity and validates the response', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          id: 4,
          traffic_log_id: 7,
          revision: 1,
          predicted_label: 'SQL Injection',
          verified_label: 'Normal',
          approval_state: 'approved_for_training',
          reviewer_id: 'account-7',
          reviewer_role: 'ANALYST',
          reviewed_at: '2026-08-02T00:00:00Z',
          model_version: 'model-v1',
          input_hash: null,
          review_note: 'Confirmed',
          created_at: '2026-08-02T00:00:00Z',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )

    const { submitAlertLabelReview } = await loadClient()
    const result = await submitAlertLabelReview(
      '7',
      {
        verified_label: 'Normal',
        approval_state: 'approved_for_training',
        review_note: 'Confirmed',
      },
      { id: 'account-7', role: 'ANALYST' }
    )

    expect(result.ok).toBe(true)
    expect(fetchMock).toHaveBeenCalledWith(
      'http://localhost:8000/api/alerts/7/label-review',
      expect.objectContaining({
        method: 'POST',
        headers: {
          Authorization: 'Bearer test-secret',
          'Content-Type': 'application/json',
          'X-Reviewer-Id': 'account-7',
          'X-Reviewer-Role': 'ANALYST',
        },
        body: JSON.stringify({
          verified_label: 'Normal',
          approval_state: 'approved_for_training',
          review_note: 'Confirmed',
        }),
      })
    )
  })

  it('does not claim success for verified label review in mock mode', async () => {
    process.env.USE_MOCK_API = 'true'
    const { submitAlertLabelReview } = await loadClient()
    const result = await submitAlertLabelReview(
      '7',
      { verified_label: 'Normal', approval_state: 'excluded_from_training' },
      { id: 'account-7', role: 'ANALYST' }
    )

    expect(result).toEqual({
      ok: false,
      status: 503,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Verified label review is unavailable in mock mode.',
      },
    })
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
