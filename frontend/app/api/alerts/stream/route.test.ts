import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  auth: vi.fn(),
  requirePermission: vi.fn(),
  openAlertStream: vi.fn(),
}))

vi.mock('@/auth', () => ({ auth: harness.auth }))
vi.mock('@/lib/auth/route-guard', () => ({
  requirePermission: harness.requirePermission,
}))
vi.mock('@/lib/bff-client', () => ({
  openAlertStream: harness.openAlertStream,
}))

describe('alerts SSE BFF route', () => {
  beforeEach(() => vi.clearAllMocks())

  it('fails closed before opening the backend stream', async () => {
    harness.auth.mockResolvedValue(null)
    harness.requirePermission.mockResolvedValue({
      ok: false,
      response: Response.json(
        { error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' } },
        { status: 401 }
      ),
    })
    const { GET } = await import('./route')

    const response = await GET(
      new NextRequest('http://localhost:3000/api/alerts/stream')
    )

    expect(response.status).toBe(401)
    expect(harness.openAlertStream).not.toHaveBeenCalled()
  })

  it('does not open upstream when current-account checks deny a session', async () => {
    harness.auth.mockResolvedValue({ user: { role: 'ANALYST' } })
    harness.requirePermission.mockResolvedValue({
      ok: false,
      response: Response.json(
        { error: { code: 'FORBIDDEN', message: 'Forbidden.' } },
        { status: 403 }
      ),
    })
    const { GET } = await import('./route')

    const response = await GET(
      new NextRequest('http://localhost:3000/api/alerts/stream')
    )

    expect(response.status).toBe(403)
    expect(harness.openAlertStream).not.toHaveBeenCalled()
  })

  it('passes through the readable body with SSE-safe headers', async () => {
    const upstreamBody = new ReadableStream()
    harness.auth.mockResolvedValue({ user: { role: 'ANALYST' } })
    harness.requirePermission.mockResolvedValue({ ok: true })
    harness.openAlertStream.mockResolvedValue({
      ok: true,
      data: new Response(upstreamBody, {
        headers: { 'Content-Type': 'text/event-stream' },
      }),
    })
    const { GET } = await import('./route')
    const request = new NextRequest('http://localhost:3000/api/alerts/stream')

    const response = await GET(request)

    expect(harness.openAlertStream).toHaveBeenCalledWith(request.signal)
    expect(response.body).toBe(upstreamBody)
    expect(response.headers.get('Content-Type')).toBe('text/event-stream')
    expect(response.headers.get('Cache-Control')).toBe(
      'private, no-cache, no-store, no-transform'
    )
    expect(response.headers.get('X-Content-Type-Options')).toBe('nosniff')
    expect(response.headers.get('X-Accel-Buffering')).toBe('no')
    expect(response.headers.has('Connection')).toBe(false)
  })

  it('returns only the generic upstream error contract', async () => {
    harness.auth.mockResolvedValue({ user: { role: 'ANALYST' } })
    harness.requirePermission.mockResolvedValue({ ok: true })
    harness.openAlertStream.mockResolvedValue({
      ok: false,
      status: 502,
      error: { code: 'UPSTREAM_ERROR', message: 'Upstream service failed.' },
    })
    const { GET } = await import('./route')

    const response = await GET(
      new NextRequest('http://localhost:3000/api/alerts/stream')
    )
    const body = await response.json()

    expect(response.status).toBe(502)
    expect(body).toEqual({
      error: { code: 'UPSTREAM_ERROR', message: 'Upstream service failed.' },
    })
  })
})
