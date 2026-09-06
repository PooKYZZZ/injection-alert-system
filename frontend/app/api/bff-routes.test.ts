import fs from 'node:fs'
import path from 'node:path'

import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ROLES, type UserRole } from '@/lib/auth/roles'

vi.mock('server-only', () => ({}))

const authMock = vi.fn()
const getAlertsMock = vi.fn()
const getAlertDetailMock = vi.fn()
const getStatsMock = vi.fn()
const getMlHealthMock = vi.fn()
const getRetrainingRunsMock = vi.fn()
const getRetrainingRunMock = vi.fn()
const exportRetrainingSamplesMock = vi.fn()
const updateAlertTriageMock = vi.fn()
const updateAlertActionMock = vi.fn()
const submitAlertLabelReviewMock = vi.fn()
const getAccountForSessionFreshnessMock = vi.fn()

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'

vi.mock('@/auth', () => ({
  auth: authMock,
}))

vi.mock('@/lib/bff-client', () => ({
  getAlerts: getAlertsMock,
  getAlertDetail: getAlertDetailMock,
  getStats: getStatsMock,
  getMlHealth: getMlHealthMock,
  getRetrainingRuns: getRetrainingRunsMock,
  getRetrainingRun: getRetrainingRunMock,
  exportRetrainingSamples: exportRetrainingSamplesMock,
  updateAlertTriage: updateAlertTriageMock,
  updateAlertAction: updateAlertActionMock,
  submitAlertLabelReview: submitAlertLabelReviewMock,
}))

vi.mock('@/lib/server/db/auth-accounts', () => ({
  getAccountForSessionFreshness: getAccountForSessionFreshnessMock,
}))

function session(role: UserRole = ROLES.ADMIN, authzVersion = 1) {
  return {
    user: {
      id: accountId,
      email: 'user@example.test',
      role,
      authz_version: authzVersion,
    },
    expires: '2099-01-01T00:00:00.000Z',
  }
}

function setCurrentAccount(
  role: UserRole,
  authzVersion = 1,
  mfaRequired = false
) {
  getAccountForSessionFreshnessMock.mockResolvedValue({
    id: accountId,
    role,
    authzVersion,
    mfaRequired,
    disabledAt: null,
  })
}

describe('BFF route handlers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    setCurrentAccount(ROLES.ADMIN)
  })

  it('awaits the central DB-backed permission guard in every protected BFF route', () => {
    const routeFiles = [
      'alerts/route.ts',
      'alerts/stream/route.ts',
      'alerts/[id]/route.ts',
      'alerts/[id]/triage/route.ts',
      'alerts/[id]/action/route.ts',
      'alerts/[id]/label-review/route.ts',
      'stats/route.ts',
      'ml-health/route.ts',
      'ml-model/summary/route.ts',
      'ml-model/export/route.ts',
      'ml-model/runs/route.ts',
      'ml-model/runs/[runId]/route.ts',
      'ml-model/runs/[runId]/decision/route.ts',
      'ml-model/runs/[runId]/deploy/route.ts',
      'ml-model/runs/[runId]/rollback/route.ts',
      'ml-model/runs/[runId]/retry/route.ts',
    ]

    for (const routeFile of routeFiles) {
      const source = fs.readFileSync(path.resolve(__dirname, routeFile), 'utf8')
      expect(source).toContain(
        "import { requirePermission } from '@/lib/auth/route-guard'"
      )
      expect(source).toMatch(/await\s+requirePermission\s*\(/)
    }
  })

  it('alerts route applies the existing session auth pattern', async () => {
    authMock.mockResolvedValueOnce(null)
    const { GET } = await import('./alerts/route')

    const response = await GET(new NextRequest('http://localhost:3000/api/alerts?page=1'))
    const body = await response.json()

    expect(getAlertsMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
    expect(body).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
  })

  it('alert detail route applies the existing session auth pattern', async () => {
    authMock.mockResolvedValueOnce(null)
    const { GET } = await import('./alerts/[id]/route')

    const response = await GET({} as never, {
      params: Promise.resolve({ id: '12' }),
    })
    const body = await response.json()

    expect(getAlertDetailMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
    expect(body).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
  })

  it('stats route applies the existing session auth pattern', async () => {
    authMock.mockResolvedValueOnce(null)
    const { GET } = await import('./stats/route')

    const response = await GET(new NextRequest('http://localhost:3000/api/stats'))
    const body = await response.json()

    expect(getStatsMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
    expect(body).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
  })

  it('ml-health route applies the existing session auth pattern', async () => {
    authMock.mockResolvedValueOnce(null)
    const { GET } = await import('./ml-health/route')

    const response = await GET()
    const body = await response.json()

    expect(getMlHealthMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
    expect(body).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
  })

  it('exposes BFF retrieval time without inventing source monitoring freshness', async () => {
    setCurrentAccount(ROLES.OWNER)
    authMock.mockResolvedValueOnce(session(ROLES.OWNER))
    getMlHealthMock.mockResolvedValueOnce({
      ok: true,
      data: { status: 'HEALTHY', model_version: 'active-v1' },
    })

    const { GET } = await import('./ml-health/route')
    const response = await GET()
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body).toMatchObject({ status: 'HEALTHY', model_version: 'active-v1' })
    expect(body.retrieved_at).toMatch(/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$/)
  })

  it.each([ROLES.ADMIN, ROLES.ANALYST, ROLES.VIEWER])(
    'rejects %s from reading ML Health through the BFF',
    async (role) => {
      authMock.mockResolvedValueOnce(session(role))
      setCurrentAccount(role)

      const { GET } = await import('./ml-health/route')
      const response = await GET()

      expect(response.status).toBe(403)
      expect(getMlHealthMock).not.toHaveBeenCalled()
    }
  )

  it('retraining run reads pass the authenticated actor to the BFF client', async () => {
    setCurrentAccount(ROLES.OWNER)
    authMock.mockResolvedValue(session(ROLES.OWNER))
    getRetrainingRunsMock.mockResolvedValue({ ok: true, data: { runs: [] } })
    getRetrainingRunMock.mockResolvedValue({ ok: true, data: { run_id: 'run-1' } })

    const { GET: getRuns } = await import('./ml-model/runs/route')
    const listResponse = await getRuns()
    expect(listResponse.status).toBe(200)
    expect(getRetrainingRunsMock).toHaveBeenCalledWith({
      id: accountId,
      role: ROLES.OWNER,
    })

    const { GET: getRun } = await import('./ml-model/runs/[runId]/route')
    const detailResponse = await getRun({} as never, {
      params: Promise.resolve({ runId: 'retrain-20260811T120000Z-000000000001' }),
    })
    expect(detailResponse.status).toBe(200)
    expect(getRetrainingRunMock).toHaveBeenCalledWith(
      'retrain-20260811T120000Z-000000000001',
      { id: accountId, role: ROLES.OWNER }
    )
  })

  it('retraining export rejects malformed JSON instead of treating it as an empty request', async () => {
    setCurrentAccount(ROLES.OWNER)
    authMock.mockResolvedValue(session(ROLES.OWNER))
    process.env.AUTH_APP_ORIGIN = 'http://localhost:3000'

    const { POST } = await import('./ml-model/export/route')
    const response = await POST(
      new NextRequest('http://localhost:3000/api/ml-model/export', {
        method: 'POST',
        headers: {
          origin: 'http://localhost:3000',
          'content-type': 'application/json',
        },
        body: '{',
      })
    )
    const body = await response.json()

    expect(response.status).toBe(400)
    expect(body).toEqual({
      error: { code: 'INVALID_REQUEST', message: 'Request body must be valid JSON.' },
    })
    expect(exportRetrainingSamplesMock).not.toHaveBeenCalled()
  })

  it('alerts route returns centralized client errors unchanged', async () => {
    authMock.mockResolvedValueOnce(session())
    getAlertsMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      error: {
        code: 'BFF_MISCONFIGURED',
        message: 'Server configuration is incomplete.',
      },
    })

    const { GET } = await import('./alerts/route')
    const response = await GET(
      new NextRequest('http://localhost:3000/api/alerts?page=1&page_size=20')
    )
    const body = await response.json()

    expect(getAlertsMock).toHaveBeenCalled()
    expect(response.status).toBe(500)
    expect(body).toEqual({
      error: {
        code: 'BFF_MISCONFIGURED',
        message: 'Server configuration is incomplete.',
      },
    })
  })

  it('alert detail route returns normalized data and propagates 404', async () => {
    authMock
      .mockResolvedValueOnce(session())
      .mockResolvedValueOnce(session())
    getAlertDetailMock
      .mockResolvedValueOnce({
        ok: true,
        data: {
          alert_id: '12',
          timestamp: '2026-03-15T00:00:00Z',
          source_ip: '203.0.113.10',
          request_path: '/login',
          request_method: 'POST',
          payload_snippet: 'payload',
          prediction: 'SQL Injection',
          confidence: 0.9,
          confidence_level: 'HIGH',
          action_taken: 'BLOCKED',
          crs_score: 9,
          crs_rule_ids: ['942100'],
          analyst_label: 'Normal',
          labeled_at: '2026-03-15T00:05:00Z',
          labeled_by: 'analyst@lares.test',
        },
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 404,
        error: {
          code: 'NOT_FOUND',
          message: 'Requested resource was not found.',
        },
      })

    const { GET } = await import('./alerts/[id]/route')

    const okResponse = await GET({} as never, {
      params: Promise.resolve({ id: '12' }),
    })
    const okBody = await okResponse.json()

    const notFoundResponse = await GET({} as never, {
      params: Promise.resolve({ id: '99' }),
    })
    const notFoundBody = await notFoundResponse.json()

    expect(okResponse.status).toBe(200)
    expect(okBody.alert_id).toBe('12')
    expect(okBody.crs_rule_ids).toEqual(['942100'])
    expect(okBody.analyst_label).toBe('Normal')
    expect(notFoundResponse.status).toBe(404)
    expect(notFoundBody).toEqual({
      error: {
        code: 'NOT_FOUND',
        message: 'Requested resource was not found.',
      },
    })
  })

  it('alert detail route rejects non-numeric ids locally', async () => {
    authMock
      .mockResolvedValueOnce(session())
      .mockResolvedValueOnce(session())
      .mockResolvedValueOnce(session())
    const { GET } = await import('./alerts/[id]/route')

    for (const id of ['NaN', '', undefined] as const) {
      const response = await GET({} as never, {
        params: Promise.resolve({ id: id as unknown as string }),
      })
      const body = await response.json()

      expect(response.status).toBe(400)
      expect(body).toEqual({
        error: {
          code: 'INVALID_ID',
          message: 'Alert ID must be a valid number.',
        },
      })
    }

    expect(getAlertDetailMock).not.toHaveBeenCalled()
  })

  it('stats route returns total_requests in the frontend shape', async () => {
    authMock.mockResolvedValueOnce(session())
    getStatsMock.mockResolvedValueOnce({
      ok: true,
      data: {
        actionable_alerts: 4,
        total_requests: 1234,
        avg_inference_latency_ms: 3.2,
      },
    })

    const { GET } = await import('./stats/route')
    const response = await GET(new NextRequest('http://localhost:3000/api/stats'))
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.total_requests).toBe(1234)
    expect(body.avg_inference_latency_ms).toBe(3.2)
  })

  it('stats route forwards window search param to BFF client', async () => {
    authMock.mockResolvedValueOnce(session())
    getStatsMock.mockResolvedValueOnce({
      ok: true,
      data: {
        actionable_alerts: 0,
        total_requests: 0,
        avg_inference_latency_ms: 0,
      },
    })

    const { GET } = await import('./stats/route')
    const response = await GET(new NextRequest('http://localhost:3000/api/stats?window=7d'))

    expect(response.status).toBe(200)
    expect(getStatsMock).toHaveBeenCalledWith('7d', undefined)
  })

  it('stats route forwards timezone search param to BFF client', async () => {
    authMock.mockResolvedValueOnce(session())
    getStatsMock.mockResolvedValueOnce({
      ok: true,
      data: {
        actionable_alerts: 0,
        total_requests: 0,
        avg_inference_latency_ms: 0,
      },
    })

    const { GET } = await import('./stats/route')
    const response = await GET(
      new NextRequest('http://localhost:3000/api/stats?window=24h&timezone=Asia/Manila')
    )

    expect(response.status).toBe(200)
    expect(getStatsMock).toHaveBeenCalledWith('24h', 'Asia/Manila')
  })

  it('stats route forwards timezone_name search param to BFF client', async () => {
    authMock.mockResolvedValueOnce(session())
    getStatsMock.mockResolvedValueOnce({
      ok: true,
      data: {
        actionable_alerts: 0,
        total_requests: 0,
        avg_inference_latency_ms: 0,
      },
    })

    const { GET } = await import('./stats/route')
    const response = await GET(
      new NextRequest('http://localhost:3000/api/stats?window=24h&timezone_name=Asia/Manila')
    )

    expect(response.status).toBe(200)
    expect(getStatsMock).toHaveBeenCalledWith('24h', 'Asia/Manila')
  })

  it('ml-health route returns the frontend component contract shape', async () => {
    setCurrentAccount(ROLES.OWNER)
    authMock.mockResolvedValueOnce(session(ROLES.OWNER))
    getMlHealthMock.mockResolvedValueOnce({
      ok: true,
      data: {
        model_version: 'distilbert-v1',
        status: 'HEALTHY',
        latency_ms: 2.5,
        latency_trend: null,
        drift_score: null,
        drift_status: 'NORMAL',
        traffic_processed: 44,
        thresholds: {
          low: 0.5,
          medium: null,
          high: 0.8,
        },
      },
    })

    const { GET } = await import('./ml-health/route')
    const response = await GET()
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.status).toBe('HEALTHY')
    expect(body.thresholds.medium).toBeNull()
    expect(body.thresholds.high).toBe(0.8)
  })

  it('alerts route propagates upstream 502 (invalid payload) as UPSTREAM_ERROR', async () => {
    authMock.mockResolvedValueOnce(session())
    getAlertsMock.mockResolvedValueOnce({
      ok: false,
      status: 502,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream response did not match expected shape.',
      },
    })

    const { GET } = await import('./alerts/route')
    const response = await GET(new NextRequest('http://localhost:3000/api/alerts'))
    const body = await response.json()

    expect(response.status).toBe(502)
    expect(body).toEqual({
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream response did not match expected shape.',
      },
    })
  })

  it('stats route propagates upstream 503 (service unavailable)', async () => {
    authMock.mockResolvedValueOnce(session())
    getStatsMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream service failed.',
      },
    })

    const { GET } = await import('./stats/route')
    const response = await GET(new NextRequest('http://localhost:3000/api/stats'))
    const body = await response.json()

    expect(response.status).toBe(503)
    expect(body).toEqual({
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream service failed.',
      },
    })
  })

  it('ml-health route propagates INTERNAL_SERVICE_AUTH_FAILED error', async () => {
    setCurrentAccount(ROLES.OWNER)
    authMock.mockResolvedValueOnce(session(ROLES.OWNER))
    getMlHealthMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      error: {
        code: 'INTERNAL_SERVICE_AUTH_FAILED',
        message: 'Internal service authentication failed.',
      },
    })

    const { GET } = await import('./ml-health/route')
    const response = await GET()
    const body = await response.json()

    expect(response.status).toBe(500)
    expect(body).toEqual({
      error: {
        code: 'INTERNAL_SERVICE_AUTH_FAILED',
        message: 'Internal service authentication failed.',
      },
    })
  })

  it('alerts route rejects unauthenticated request before calling BFF client', async () => {
    authMock.mockResolvedValueOnce(null)
    const { GET } = await import('./alerts/route')

    const response = await GET(new NextRequest('http://localhost:3000/api/alerts'))

    // BFF client must NOT be called when auth fails
    expect(getAlertsMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
  })

  it('alerts route fails closed when the DB freshness lookup is unavailable', async () => {
    authMock.mockResolvedValueOnce(session())
    getAccountForSessionFreshnessMock.mockRejectedValueOnce(
      new Error('raw database details')
    )
    const { GET } = await import('./alerts/route')

    const response = await GET(
      new NextRequest('http://localhost:3000/api/alerts')
    )

    expect(response.status).toBe(401)
    expect(await response.json()).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
    expect(getAlertsMock).not.toHaveBeenCalled()
  })

  it('alert detail route rejects unauthenticated request before calling BFF client', async () => {
    authMock.mockResolvedValueOnce(null)
    const { GET } = await import('./alerts/[id]/route')

    const response = await GET({} as never, {
      params: Promise.resolve({ id: '1' }),
    })

    // BFF client must NOT be called when auth fails
    expect(getAlertDetailMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
  })

  it('stats route rejects unauthenticated request before calling BFF client', async () => {
    authMock.mockResolvedValueOnce(null)
    const { GET } = await import('./stats/route')

    const response = await GET(new NextRequest('http://localhost:3000/api/stats'))

    // BFF client must NOT be called when auth fails
    expect(getStatsMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
  })

  it('alerts route returns 500 for unhandled exceptions', async () => {
    authMock.mockResolvedValueOnce(session())
    getAlertsMock.mockRejectedValueOnce(new Error('Unexpected failure'))

    const { GET } = await import('./alerts/route')
    const response = await GET(new NextRequest('http://localhost:3000/api/alerts'))
    const body = await response.json()

    expect(response.status).toBe(500)
    expect(body).toEqual({
      error: {
        code: 'INTERNAL_ERROR',
        message: 'An unexpected error occurred.',
      },
    })
  })

  it('stats route forwards Retry-After header from upstream 503', async () => {
    authMock.mockResolvedValueOnce(session())
    getStatsMock.mockResolvedValueOnce({
      ok: false,
      status: 503,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream service failed.',
      },
      retryAfter: '30',
    })

    const { GET } = await import('./stats/route')
    const response = await GET(new NextRequest('http://localhost:3000/api/stats'))

    expect(response.status).toBe(503)
    expect(response.headers.get('Retry-After')).toBe('30')
  })

  // --- Triage PATCH endpoint tests ---

  it('triage PATCH rejects unauthenticated request', async () => {
    authMock.mockResolvedValueOnce(null)
    const { PATCH } = await import('./alerts/[id]/triage/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/triage', {
      method: 'PATCH',
      body: JSON.stringify({ triage_status: 'in_review' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(updateAlertTriageMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
    expect(body).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
  })

  it('label review POST forwards canonical data and Owner session-derived identity', async () => {
    setCurrentAccount(ROLES.OWNER)
    authMock.mockResolvedValueOnce(session(ROLES.OWNER))
    submitAlertLabelReviewMock.mockResolvedValueOnce({
      ok: true,
      data: {
        id: 4,
        traffic_log_id: 1,
        revision: 1,
        verified_label: 'SQL Injection',
        approval_state: 'approved_for_training',
        reviewer_id: accountId,
        reviewer_role: 'OWNER',
        reviewed_at: '2026-08-02T00:00:00Z',
      },
    })
    const { POST } = await import('./alerts/[id]/label-review/route')
    const response = await POST(
      new NextRequest('http://localhost:3000/api/alerts/1/label-review', {
        method: 'POST',
        body: JSON.stringify({
          verified_label: 'SQL Injection',
          approval_state: 'approved_for_training',
          review_note: 'Confirmed',
        }),
      }),
      { params: Promise.resolve({ id: '1' }) }
    )

    expect(response.status).toBe(200)
    expect(submitAlertLabelReviewMock).toHaveBeenCalledWith(
      '1',
      {
        verified_label: 'SQL Injection',
        approval_state: 'approved_for_training',
        review_note: 'Confirmed',
      },
      { id: accountId, role: 'OWNER' }
    )
  })

  it.each([ROLES.ADMIN, ROLES.ANALYST, ROLES.VIEWER] as const)(
    'label review POST rejects %s before parsing or forwarding',
    async (role) => {
      setCurrentAccount(role)
      authMock.mockResolvedValueOnce(session(role))
      const jsonMock = vi.fn()
      const { POST } = await import('./alerts/[id]/label-review/route')
      const response = await POST(
        { json: jsonMock } as unknown as NextRequest,
        { params: Promise.resolve({ id: '1' }) }
      )

      expect(response.status).toBe(403)
      expect(jsonMock).not.toHaveBeenCalled()
      expect(submitAlertLabelReviewMock).not.toHaveBeenCalled()
    }
  )

  it('Owner label review POST rejects unknown body fields before forwarding', async () => {
    setCurrentAccount(ROLES.OWNER)
    authMock.mockResolvedValueOnce(session(ROLES.OWNER))
    const { POST } = await import('./alerts/[id]/label-review/route')
    const response = await POST(
      new NextRequest('http://localhost:3000/api/alerts/1/label-review', {
        method: 'POST',
        body: JSON.stringify({
          verified_label: 'Normal',
          approval_state: 'approved_for_training',
          reviewer_id: 'spoofed',
        }),
      }),
      { params: Promise.resolve({ id: '1' }) }
    )
    expect(response.status).toBe(400)
    expect(submitAlertLabelReviewMock).not.toHaveBeenCalled()
  })

  it('triage PATCH accepts valid triage_status and returns 200', async () => {
    authMock.mockResolvedValueOnce(session())
    updateAlertTriageMock.mockResolvedValueOnce({
      ok: true,
      data: { alert_id: '1', triage_status: 'in_review' },
    })
    const { PATCH } = await import('./alerts/[id]/triage/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/triage', {
      method: 'PATCH',
      body: JSON.stringify({ triage_status: 'in_review' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.triage_status).toBe('in_review')
    expect(updateAlertTriageMock).toHaveBeenCalledWith('1', 'in_review')
  })

  it('triage PATCH rejects invalid triage_status with 400', async () => {
    authMock.mockResolvedValueOnce(session())
    const { PATCH } = await import('./alerts/[id]/triage/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/triage', {
      method: 'PATCH',
      body: JSON.stringify({ triage_status: 'invalid_status' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(updateAlertTriageMock).not.toHaveBeenCalled()
    expect(response.status).toBe(400)
    expect(body.error.code).toBe('INVALID_REQUEST')
  })

  it('triage PATCH rejects malformed JSON with 400', async () => {
    authMock.mockResolvedValueOnce(session())
    const { PATCH } = await import('./alerts/[id]/triage/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/triage', {
      method: 'PATCH',
      body: '{"triage_status":',
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(updateAlertTriageMock).not.toHaveBeenCalled()
    expect(response.status).toBe(400)
    expect(body.error.code).toBe('INVALID_REQUEST')
  })

  it('triage PATCH rejects non-numeric alert ID with 400', async () => {
    authMock.mockResolvedValueOnce(session())
    const { PATCH } = await import('./alerts/[id]/triage/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/abc/triage', {
      method: 'PATCH',
      body: JSON.stringify({ triage_status: 'in_review' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: 'abc' }),
    })
    const body = await response.json()

    expect(updateAlertTriageMock).not.toHaveBeenCalled()
    expect(response.status).toBe(400)
    expect(body.error.code).toBe('INVALID_ID')
  })

  it('triage PATCH propagates 401 from upstream as INTERNAL_SERVICE_AUTH_FAILED', async () => {
    authMock.mockResolvedValueOnce(session())
    updateAlertTriageMock.mockResolvedValueOnce({
      ok: false,
      status: 500,
      error: {
        code: 'INTERNAL_SERVICE_AUTH_FAILED',
        message: 'Internal service authentication failed.',
      },
    })
    const { PATCH } = await import('./alerts/[id]/triage/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/triage', {
      method: 'PATCH',
      body: JSON.stringify({ triage_status: 'in_review' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(response.status).toBe(500)
    expect(body.error.code).toBe('INTERNAL_SERVICE_AUTH_FAILED')
  })

  it('triage PATCH propagates 404 from upstream as NOT_FOUND', async () => {
    authMock.mockResolvedValueOnce(session())
    updateAlertTriageMock.mockResolvedValueOnce({
      ok: false,
      status: 404,
      error: {
        code: 'NOT_FOUND',
        message: 'Requested resource was not found.',
      },
    })
    const { PATCH } = await import('./alerts/[id]/triage/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/999/triage', {
      method: 'PATCH',
      body: JSON.stringify({ triage_status: 'resolved' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '999' }),
    })
    const body = await response.json()

    expect(response.status).toBe(404)
    expect(body.error.code).toBe('NOT_FOUND')
  })

  it('triage PATCH returns 500 for unhandled exceptions', async () => {
    authMock.mockResolvedValueOnce(session())
    updateAlertTriageMock.mockRejectedValueOnce(new Error('Unexpected failure'))
    const { PATCH } = await import('./alerts/[id]/triage/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/triage', {
      method: 'PATCH',
      body: JSON.stringify({ triage_status: 'in_review' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(response.status).toBe(500)
    expect(body.error.code).toBe('INTERNAL_ERROR')
  })

  it('action PATCH accepts valid action_taken and returns 200', async () => {
    authMock.mockResolvedValueOnce(session())
    updateAlertActionMock.mockResolvedValueOnce({
      ok: true,
      data: { alert_id: '1', action_taken: 'BLOCKED' },
    })
    const { PATCH } = await import('./alerts/[id]/action/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/action', {
      method: 'PATCH',
      body: JSON.stringify({ action_taken: 'BLOCKED' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.action_taken).toBe('BLOCKED')
    expect(updateAlertActionMock).toHaveBeenCalledWith('1', 'BLOCKED')
  })

  it('action PATCH rejects invalid action_taken with 400', async () => {
    authMock.mockResolvedValueOnce(session())
    const { PATCH } = await import('./alerts/[id]/action/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/action', {
      method: 'PATCH',
      body: JSON.stringify({ action_taken: 'INVALID' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(updateAlertActionMock).not.toHaveBeenCalled()
    expect(response.status).toBe(400)
    expect(body.error.code).toBe('INVALID_REQUEST')
  })

  it('action PATCH rejects unauthenticated request with 401', async () => {
    authMock.mockResolvedValueOnce(null)
    const { PATCH } = await import('./alerts/[id]/action/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/action', {
      method: 'PATCH',
      body: JSON.stringify({ action_taken: 'BLOCKED' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(updateAlertActionMock).not.toHaveBeenCalled()
    expect(response.status).toBe(401)
    expect(body).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
  })

  it('action PATCH rejects malformed JSON with 400', async () => {
    authMock.mockResolvedValueOnce(session())
    const { PATCH } = await import('./alerts/[id]/action/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/1/action', {
      method: 'PATCH',
      body: '{"action_taken":',
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const body = await response.json()

    expect(updateAlertActionMock).not.toHaveBeenCalled()
    expect(response.status).toBe(400)
    expect(body.error.code).toBe('INVALID_REQUEST')
  })

  it('action PATCH rejects non-numeric alert ID with 400', async () => {
    authMock.mockResolvedValueOnce(session())
    const { PATCH } = await import('./alerts/[id]/action/route')

    const request = new NextRequest('http://localhost:3000/api/alerts/not-a-number/action', {
      method: 'PATCH',
      body: JSON.stringify({ action_taken: 'BLOCKED' }),
    })

    const response = await PATCH(request, {
      params: Promise.resolve({ id: 'not-a-number' }),
    })
    const body = await response.json()

    expect(updateAlertActionMock).not.toHaveBeenCalled()
    expect(response.status).toBe(400)
    expect(body.error.code).toBe('INVALID_ID')
  })

  it('allows VIEWER sessions to read alerts and stats but denies ML Health', async () => {
    setCurrentAccount(ROLES.VIEWER)
    authMock
      .mockResolvedValueOnce(session(ROLES.VIEWER))
      .mockResolvedValueOnce(session(ROLES.VIEWER))
      .mockResolvedValueOnce(session(ROLES.VIEWER))
      .mockResolvedValueOnce(session(ROLES.VIEWER))
    getAlertsMock.mockResolvedValueOnce({ ok: true, data: { items: [] } })
    getAlertDetailMock.mockResolvedValueOnce({ ok: true, data: { alert_id: '1' } })
    getStatsMock.mockResolvedValueOnce({ ok: true, data: { total_requests: 0 } })

    const [{ GET: getAlerts }, { GET: getAlert }, { GET: getStats }, { GET: getMlHealth }] =
      await Promise.all([
        import('./alerts/route'),
        import('./alerts/[id]/route'),
        import('./stats/route'),
        import('./ml-health/route'),
      ])

    expect(
      (await getAlerts(new NextRequest('http://localhost:3000/api/alerts'))).status
    ).toBe(200)
    expect(
      (
        await getAlert({} as never, {
          params: Promise.resolve({ id: '1' }),
        })
      ).status
    ).toBe(200)
    expect(
      (await getStats(new NextRequest('http://localhost:3000/api/stats'))).status
    ).toBe(200)
    expect((await getMlHealth()).status).toBe(403)
    expect(getMlHealthMock).not.toHaveBeenCalled()
  })

  it('allows only OWNER sessions to retrieve ML Health through the BFF', async () => {
    setCurrentAccount(ROLES.OWNER)
    authMock.mockResolvedValueOnce(session(ROLES.OWNER))
    getMlHealthMock.mockResolvedValueOnce({ ok: true, data: { status: 'HEALTHY' } })
    const { GET } = await import('./ml-health/route')

    const response = await GET()

    expect(response.status).toBe(200)
    expect(getMlHealthMock).toHaveBeenCalledWith({ id: accountId, role: ROLES.OWNER })
  })

  it('returns 403 before parsing or forwarding VIEWER mutation requests', async () => {
    setCurrentAccount(ROLES.VIEWER)
    authMock
      .mockResolvedValueOnce(session(ROLES.VIEWER))
      .mockResolvedValueOnce(session(ROLES.VIEWER))
    const jsonMock = vi.fn()
    const request = { json: jsonMock } as unknown as NextRequest
    const [{ PATCH: patchTriage }, { PATCH: patchAction }] = await Promise.all([
      import('./alerts/[id]/triage/route'),
      import('./alerts/[id]/action/route'),
    ])

    const triageResponse = await patchTriage(request, {
      params: Promise.resolve({ id: '1' }),
    })
    const actionResponse = await patchAction(request, {
      params: Promise.resolve({ id: '1' }),
    })

    expect(triageResponse.status).toBe(403)
    expect(actionResponse.status).toBe(403)
    expect(await triageResponse.json()).toEqual({
      error: { code: 'FORBIDDEN', message: 'Forbidden.' },
    })
    expect(jsonMock).not.toHaveBeenCalled()
    expect(updateAlertTriageMock).not.toHaveBeenCalled()
    expect(updateAlertActionMock).not.toHaveBeenCalled()
  })

  it('allows ANALYST triage but returns 403 before forwarding action updates', async () => {
    setCurrentAccount(ROLES.ANALYST)
    authMock
      .mockResolvedValueOnce(session(ROLES.ANALYST))
      .mockResolvedValueOnce(session(ROLES.ANALYST))
    updateAlertTriageMock.mockResolvedValueOnce({
      ok: true,
      data: { alert_id: '1', triage_status: 'in_review' },
    })
    const [{ PATCH: patchTriage }, { PATCH: patchAction }] = await Promise.all([
      import('./alerts/[id]/triage/route'),
      import('./alerts/[id]/action/route'),
    ])

    const triageResponse = await patchTriage(
      new NextRequest('http://localhost:3000/api/alerts/1/triage', {
        method: 'PATCH',
        body: JSON.stringify({ triage_status: 'in_review' }),
      }),
      { params: Promise.resolve({ id: '1' }) }
    )
    const actionResponse = await patchAction(
      new NextRequest('http://localhost:3000/api/alerts/1/action', {
        method: 'PATCH',
        body: JSON.stringify({ action_taken: 'BLOCKED' }),
      }),
      { params: Promise.resolve({ id: '1' }) }
    )

    expect(triageResponse.status).toBe(200)
    expect(actionResponse.status).toBe(403)
    expect(updateAlertTriageMock).toHaveBeenCalledWith('1', 'in_review')
    expect(updateAlertActionMock).not.toHaveBeenCalled()
  })

  it('returns 401 and skips the BFF client after a server-side registry version change', async () => {
    const unchangedClientSession = session(ROLES.ADMIN)
    authMock
      .mockResolvedValueOnce(unchangedClientSession)
      .mockResolvedValueOnce(unchangedClientSession)
    getAlertsMock.mockResolvedValueOnce({ ok: true, data: { items: [] } })
    const { GET } = await import('./alerts/route')

    const currentResponse = await GET(
      new NextRequest('http://localhost:3000/api/alerts')
    )
    setCurrentAccount(ROLES.ADMIN, 2)
    const staleResponse = await GET(
      new NextRequest('http://localhost:3000/api/alerts')
    )

    expect(currentResponse.status).toBe(200)
    expect(staleResponse.status).toBe(401)
    expect(await staleResponse.json()).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
    expect(getAlertsMock).toHaveBeenCalledTimes(1)
  })

  it('returns 401 and skips the BFF client when MFA becomes required', async () => {
    setCurrentAccount(ROLES.ADMIN, 1, true)
    authMock.mockResolvedValueOnce(session(ROLES.ADMIN))
    const { GET } = await import('./alerts/route')

    const response = await GET(
      new NextRequest('http://localhost:3000/api/alerts')
    )

    expect(response.status).toBe(401)
    expect(await response.json()).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
    expect(getAlertsMock).not.toHaveBeenCalled()
  })
})
