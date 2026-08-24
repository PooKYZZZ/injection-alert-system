import type { ReactNode } from 'react'
import { act, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { useStartRetrainingMutation } from './queries'

const fetchMock = vi.fn()
vi.stubGlobal('fetch', fetchMock)

afterEach(() => {
  fetchMock.mockReset()
  vi.restoreAllMocks()
})

describe('ML model queries', () => {
  it('sends the browser timezone when requesting a retraining run', async () => {
    vi.spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions').mockReturnValue({
      locale: 'en-US',
      calendar: 'gregory',
      numberingSystem: 'latn',
      timeZone: 'America/New_York',
    })
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: 'retrain-20260811T120000Z-000000000001',
          state: 'queued',
          stage: 'queued',
          created: true,
          attempt: 0,
        }),
        { status: 202, headers: { 'Content-Type': 'application/json' } }
      )
    )
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false } },
    })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    const { result } = renderHook(() => useStartRetrainingMutation(), { wrapper })

    await act(() => result.current.mutateAsync({ trigger: 'manual' }))

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/ml-model/runs',
      expect.objectContaining({
        headers: expect.objectContaining({
          'X-Requester-Timezone': 'America/New_York',
        }),
      })
    )
  })

  it('uses UTC when the browser cannot resolve a timezone', async () => {
    vi.spyOn(Intl.DateTimeFormat.prototype, 'resolvedOptions').mockImplementation(() => {
      throw new Error('timezone unavailable')
    })
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          run_id: 'retrain-20260811T120000Z-000000000001',
          state: 'queued',
          stage: 'queued',
          created: true,
          attempt: 0,
        }),
        { status: 202, headers: { 'Content-Type': 'application/json' } }
      )
    )
    const queryClient = new QueryClient({
      defaultOptions: { mutations: { retry: false } },
    })
    const wrapper = ({ children }: { children: ReactNode }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    )
    const { result } = renderHook(() => useStartRetrainingMutation(), { wrapper })

    await act(() => result.current.mutateAsync({ trigger: 'manual' }))

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/ml-model/runs',
      expect.objectContaining({
        headers: expect.objectContaining({ 'X-Requester-Timezone': 'UTC' }),
      })
    )
  })
})
