import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import { openAlertStream } from './bff-client'

describe('openAlertStream', () => {
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
    delete process.env.FASTAPI_BASE_URL
    delete process.env.INTERNAL_API_KEY
    delete process.env.USE_MOCK_API
  })

  it('adds the internal bearer credential server-side and propagates abort', async () => {
    process.env.FASTAPI_BASE_URL = 'http://backend:8000'
    process.env.INTERNAL_API_KEY = 'server-only-secret'
    const downstreamController = new AbortController()
    const upstream = new Response(new ReadableStream(), {
      headers: { 'Content-Type': 'text/event-stream' },
    })
    const fetchMock = vi.fn().mockResolvedValue(upstream)
    vi.stubGlobal('fetch', fetchMock)

    const result = await openAlertStream(downstreamController.signal)

    expect(result).toEqual({ ok: true, data: upstream })
    expect(fetchMock).toHaveBeenCalledWith(
      'http://backend:8000/api/alerts/stream',
      expect.objectContaining({
        cache: 'no-store',
        redirect: 'error',
        signal: expect.any(AbortSignal),
        headers: { Authorization: 'Bearer server-only-secret' },
      })
    )
    const upstreamSignal = fetchMock.mock.calls[0]?.[1]?.signal as AbortSignal
    expect(upstreamSignal.aborted).toBe(false)
    downstreamController.abort()
    expect(upstreamSignal.aborted).toBe(true)
  })

  it('rejects a content type that only contains the SSE media type as a prefix', async () => {
    process.env.FASTAPI_BASE_URL = 'http://backend:8000'
    process.env.INTERNAL_API_KEY = 'server-only-secret'
    const cancel = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(new ReadableStream({ cancel }), {
          headers: { 'Content-Type': 'text/event-streaming' },
        })
      )
    )

    const result = await openAlertStream(new AbortController().signal)

    expect(result).toEqual({
      ok: false,
      status: 502,
      error: {
        code: 'UPSTREAM_ERROR',
        message: 'Upstream response was not an event stream.',
      },
    })
    expect(cancel).toHaveBeenCalledOnce()
  })

  it('cancels a rejected upstream response body', async () => {
    process.env.FASTAPI_BASE_URL = 'http://backend:8000'
    process.env.INTERNAL_API_KEY = 'server-only-secret'
    const cancel = vi.fn()
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(
        new Response(new ReadableStream({ cancel }), { status: 503 })
      )
    )

    const result = await openAlertStream(new AbortController().signal)

    expect(result).toMatchObject({ ok: false, status: 503 })
    expect(cancel).toHaveBeenCalledOnce()
  })

  it('returns a generic gateway error when connection establishment fails', async () => {
    process.env.FASTAPI_BASE_URL = 'http://private-backend:8000'
    process.env.INTERNAL_API_KEY = 'server-only-secret'
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('secret details')))

    const result = await openAlertStream(new AbortController().signal)

    expect(result).toEqual({
      ok: false,
      status: 502,
      error: { code: 'UPSTREAM_ERROR', message: 'Upstream service failed.' },
    })
    expect(JSON.stringify(result)).not.toContain('secret')
    expect(JSON.stringify(result)).not.toContain('private-backend')
  })

  it('aborts connection establishment after ten seconds', async () => {
    vi.useFakeTimers()
    process.env.FASTAPI_BASE_URL = 'http://backend:8000'
    process.env.INTERNAL_API_KEY = 'server-only-secret'
    vi.stubGlobal(
      'fetch',
      vi.fn().mockImplementation((_url: string, init: RequestInit) =>
        new Promise((_resolve, reject) => {
          init.signal?.addEventListener(
            'abort',
            () => reject(new DOMException('Aborted', 'AbortError')),
            { once: true }
          )
        })
      )
    )

    const pending = openAlertStream(new AbortController().signal)
    await vi.advanceTimersByTimeAsync(10_000)

    expect(await pending).toEqual({
      ok: false,
      status: 502,
      error: { code: 'UPSTREAM_ERROR', message: 'Upstream service failed.' },
    })
  })
})
