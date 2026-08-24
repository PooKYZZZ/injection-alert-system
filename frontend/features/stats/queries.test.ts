import { afterEach, describe, expect, it, vi } from 'vitest'
import { statsOptions } from './queries'

const fetchMock = vi.fn<typeof fetch>()

afterEach(() => {
  vi.restoreAllMocks()
})

describe('statsOptions', () => {
  it('does not reuse placeholder stats across query key changes', () => {
    const options = statsOptions('24h', 'Asia/Manila')

    expect(options.placeholderData).toBeUndefined()
  })

  it('passes TanStack Query cancellation to the stats request', async () => {
    vi.stubGlobal('fetch', fetchMock)
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }))
    const options = statsOptions('6h', 'Asia/Manila')
    const signal = new AbortController().signal

    if (typeof options.queryFn !== 'function') throw new Error('stats query function missing')
    await options.queryFn({ queryKey: options.queryKey, signal } as never)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/stats?window=6h&timezone=Asia%2FManila',
      { signal }
    )
  })
})
