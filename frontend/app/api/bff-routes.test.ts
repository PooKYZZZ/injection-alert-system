import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const authMock = vi.fn()
const getAlertsMock = vi.fn()
const getAlertDetailMock = vi.fn()
const getStatsMock = vi.fn()
const getMlHealthMock = vi.fn()

vi.mock('@/auth', () => ({
  auth: authMock,
}))

vi.mock('@/lib/bff-client', () => ({
  getAlerts: getAlertsMock,
  getAlertDetail: getAlertDetailMock,
  getStats: getStatsMock,
  getMlHealth: getMlHealthMock,
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

    const response = await GET({} as never)
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

    const response = await GET({} as never)
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
    const response = await GET({} as never)
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.total_requests).toBe(1234)
    expect(body.avg_inference_latency_ms).toBe(3.2)
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
    const response = await GET({} as never)
    const body = await response.json()

    expect(response.status).toBe(200)
    expect(body.status).toBe('HEALTHY')
    expect(body.thresholds.medium).toBeNull()
    expect(body.thresholds.high).toBe(0.8)
  })
})
