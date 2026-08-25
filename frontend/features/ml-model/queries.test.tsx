import type { ReactNode } from 'react'
import { act, renderHook } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { afterEach, describe, expect, it, vi } from 'vitest'

import {
  mlModelSummaryOptions,
  RetrainingQueryError,
  useStartRetrainingMutation,
} from './queries'

const fetchMock = vi.fn()
vi.stubGlobal('fetch', fetchMock)

afterEach(() => {
  fetchMock.mockReset()
  vi.restoreAllMocks()
})

describe('ML model queries', () => {
  it('passes TanStack Query cancellation signals to model-operation fetches', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          active_model_version: 'active-v1',
          latest_run_state: 'queued',
          approved_count: 0,
          unreviewed_count: 0,
          excluded_count: 0,
          latest_dataset_version: 'dataset-v1',
          run_in_progress: false,
          last_trigger_time: '2026-08-11T04:00:00Z',
        }),
        { status: 200, headers: { 'Content-Type': 'application/json' } }
      )
    )
    const signal = new AbortController().signal
    const options = mlModelSummaryOptions()

    await options.queryFn?.({
      queryKey: options.queryKey,
      signal,
    } as never)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/ml-model/summary',
      expect.objectContaining({ cache: 'no-store', signal })
    )
  })

  it('surfaces a disabled Model Operations response without retrying it', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ error: 'Local retraining control is disabled.' }), { status: 503 })
    )
    const options = mlModelSummaryOptions()

    expect(options.queryFn).toBeDefined()
    const rejection = Promise.resolve(options.queryFn!({
      queryKey: options.queryKey,
      signal: new AbortController().signal,
    } as never) as Promise<unknown>)

    const error = await rejection.catch((reason: unknown) => reason)
    expect(error).toMatchObject({ status: 503 })
    expect(error).toBeInstanceOf(RetrainingQueryError)
    expect(typeof options.retry).toBe('function')
    if (typeof options.retry === 'function') {
      expect(options.retry(0, error as Error)).toBe(false)
    }
  })

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
