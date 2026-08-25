import { afterEach, describe, expect, it, vi } from 'vitest'

import { mlHealthKeys, mlHealthOptions } from './queries'

afterEach(() => {
  vi.restoreAllMocks()
})

describe('mlHealthOptions', () => {
  it('passes TanStack Query cancellation to the BFF request', async () => {
    const response = {
      ok: true,
      json: vi.fn().mockResolvedValue({}),
    }
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue(response as unknown as Response)
    const signal = new AbortController().signal
    const queryFn = mlHealthOptions().queryFn as (context: { signal: AbortSignal }) => Promise<unknown>

    await queryFn({ signal })

    expect(fetchMock).toHaveBeenCalledWith('/api/ml-health', { signal })
    expect(mlHealthKeys.health()).toEqual(['ml-health', 'status'])
  })
})
