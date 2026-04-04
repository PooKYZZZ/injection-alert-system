import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const authMock = vi.fn()
const getAlertsMock = vi.fn()
const getAlertDetailMock = vi.fn()
const getStatsMock = vi.fn()
const getMlHealthMock = vi.fn()
const updateAlertTriageMock = vi.fn()
const updateAlertActionMock = vi.fn()

vi.mock('@/auth', () => ({
  auth: authMock,
}))

vi.mock('@/lib/bff-client', () => ({
  getAlerts: getAlertsMock,
  getAlertDetail: getAlertDetailMock,
  getStats: getStatsMock,
  getMlHealth: getMlHealthMock,
  updateAlertTriage: updateAlertTriageMock,
  updateAlertAction: updateAlertActionMock,
}))

describe('BFF route handlers', () => {
  beforeEach(() => {
    vi.clearAllMocks()
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

  it('alerts route returns centralized client errors unchanged', async () => {
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
      .mockResolvedValueOnce({ user: { id: '1' } })
      .mockResolvedValueOnce({ user: { id: '1' } })
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
      .mockResolvedValueOnce({ user: { id: '1' } })
      .mockResolvedValueOnce({ user: { id: '1' } })
      .mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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

  it('triage PATCH accepts valid triage_status and returns 200', async () => {
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
    authMock.mockResolvedValueOnce({ user: { id: '1' } })
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
})
