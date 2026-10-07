import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  auth: vi.fn(),
  requirePermission: vi.fn(),
  exportTrafficHistoryCsv: vi.fn(),
  requireTrustedOrigin: vi.fn(),
}))

vi.mock('@/auth', () => ({ auth: harness.auth }))
vi.mock('@/lib/auth/route-guard', () => ({
  requirePermission: harness.requirePermission,
}))
vi.mock('@/lib/bff-client', () => ({
  exportTrafficHistoryCsv: harness.exportTrafficHistoryCsv,
}))
vi.mock('@/lib/server/db/account-route-response', () => ({
  requireTrustedOrigin: harness.requireTrustedOrigin,
}))

describe('Traffic History export BFF route', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    harness.auth.mockResolvedValue({ user: { id: 'analyst-1', role: 'ANALYST' } })
    harness.requirePermission.mockResolvedValue({ ok: true })
    harness.requireTrustedOrigin.mockReturnValue(null)
    harness.exportTrafficHistoryCsv.mockResolvedValue({
      ok: true,
      data: {
        content: new TextEncoder().encode('traffic_log_id\r\n1\r\n'),
        filename: 'traffic-history_2026-10-01_to_2026-10-01.csv',
      },
    })
  })

  it('passes the session actor and returns safe CSV download headers', async () => {
    const { POST } = await import('./route')
    const response = await POST(
      new NextRequest('http://localhost/api/traffic-history/export', {
        method: 'POST',
        headers: {
          origin: 'http://localhost',
          'content-type': 'application/json',
        },
        body: JSON.stringify({
          start_date: '2026-10-01',
          end_date: '2026-10-01',
          timezone: 'UTC',
        }),
      })
    )

    expect(response.status).toBe(200)
    expect(response.headers.get('content-type')).toContain('text/csv')
    expect(response.headers.get('content-disposition')).toBe(
      'attachment; filename="traffic-history_2026-10-01_to_2026-10-01.csv"'
    )
    expect(response.headers.get('cache-control')).toBe('private, no-store')
    expect(response.headers.get('x-content-type-options')).toBe('nosniff')
    expect(await response.text()).toBe('traffic_log_id\r\n1\r\n')
    expect(harness.requirePermission).toHaveBeenCalledWith(
      expect.objectContaining({ user: expect.objectContaining({ role: 'ANALYST' }) }),
      'traffic:export'
    )
    expect(harness.exportTrafficHistoryCsv).toHaveBeenCalledWith(
      {
        start_date: '2026-10-01',
        end_date: '2026-10-01',
        timezone: 'UTC',
      },
      { id: 'analyst-1', role: 'ANALYST' }
    )
  })

  it('blocks roles denied by the central permission guard before reading the export request', async () => {
    harness.auth.mockResolvedValue({ user: { id: 'viewer-1', role: 'VIEWER' } })
    harness.requirePermission.mockResolvedValue({
      ok: false,
      response: Response.json(
        { error: { code: 'FORBIDDEN', message: 'Forbidden.' } },
        { status: 403 }
      ),
    })
    const { POST } = await import('./route')
    const response = await POST(
      new NextRequest('http://localhost/api/traffic-history/export', {
        method: 'POST',
        body: '{',
      })
    )

    expect(response.status).toBe(403)
    expect(response.headers.get('cache-control')).toBe('no-store')
    expect(harness.requireTrustedOrigin).not.toHaveBeenCalled()
    expect(harness.exportTrafficHistoryCsv).not.toHaveBeenCalled()
  })

  it('rejects malformed JSON before calling the BFF client', async () => {
    const { POST } = await import('./route')
    const response = await POST(
      new NextRequest('http://localhost/api/traffic-history/export', {
        method: 'POST',
        headers: { origin: 'http://localhost', 'content-type': 'application/json' },
        body: '{',
      })
    )

    expect(response.status).toBe(400)
    expect(harness.exportTrafficHistoryCsv).not.toHaveBeenCalled()
  })

  it('rejects an oversized request before proxying', async () => {
    const { POST } = await import('./route')
    const response = await POST(
      new NextRequest('http://localhost/api/traffic-history/export', {
        method: 'POST',
        headers: {
          origin: 'http://localhost',
          'content-type': 'application/json',
          'content-length': String(16 * 1024 + 1),
        },
        body: '{}',
      })
    )

    expect(response.status).toBe(413)
    expect(harness.exportTrafficHistoryCsv).not.toHaveBeenCalled()
  })

  it('rejects a missing trusted origin before proxying', async () => {
    harness.requireTrustedOrigin.mockReturnValue(
      Response.json({ error: { code: 'FORBIDDEN', message: 'Forbidden.' } }, { status: 403 })
    )
    const { POST } = await import('./route')
    const response = await POST(
      new NextRequest('http://localhost/api/traffic-history/export', {
        method: 'POST',
        body: JSON.stringify({
          start_date: '2026-10-01',
          end_date: '2026-10-01',
          timezone: 'UTC',
        }),
      })
    )

    expect(response.status).toBe(403)
    expect(response.headers.get('cache-control')).toBe('no-store')
    expect(harness.exportTrafficHistoryCsv).not.toHaveBeenCalled()
  })
})
