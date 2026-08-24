import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import { useEffect, useRef } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { alertListOptions, useActionMutation, useLabelReviewMutation } from './queries'

const fetchMock = vi.fn<typeof fetch>()
const showSignInToastMock = vi.fn()

vi.mock('@/components/SignInToast', () => ({
  useSignInToast: () => ({
    showSignInToast: showSignInToastMock,
  }),
}))

interface MutationHarnessProps {
  id: string
}

function MutationHarness({ id }: MutationHarnessProps) {
  const mutation = useActionMutation()
  const submitted = useRef(false)

  useEffect(() => {
    if (submitted.current) return
    submitted.current = true
    mutation.mutate({ id, action: 'BLOCKED' })
  }, [id, mutation])

  return null
}

function LabelReviewMutationHarness({ id }: MutationHarnessProps) {
  const mutation = useLabelReviewMutation()
  return (
    <button
      type="button"
      onClick={() =>
        mutation.mutate({
          id,
          verifiedLabel: 'Normal',
          approvalState: 'excluded_from_training',
          reviewNote: 'Not suitable',
        })
      }
    >
      submit
    </button>
  )
}

describe('useActionMutation', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
    showSignInToastMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('surfaces sign-in toast intent and avoids raw-401 invalidation', async () => {
    fetchMock.mockResolvedValueOnce(new Response(null, { status: 401 }))

    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null)

    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    })

    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

    render(
      <QueryClientProvider client={queryClient}>
        <MutationHarness id="1" />
      </QueryClientProvider>
    )
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/alerts/1/action',
        expect.objectContaining({ method: 'PATCH' })
      )
    })

    await waitFor(() => {
      expect(showSignInToastMock).toHaveBeenCalledTimes(1)
    })

    expect(openSpy).not.toHaveBeenCalled()
    expect(invalidateQueriesSpy).not.toHaveBeenCalled()
  })
})

describe('alertListOptions', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('passes TanStack Query cancellation to the alerts request', async () => {
    fetchMock.mockResolvedValueOnce(new Response('{}', { status: 200 }))
    const options = alertListOptions({ confidenceTier: 'ALL', timeRange: '6h', search: '' })
    const signal = new AbortController().signal

    if (typeof options.queryFn !== 'function') throw new Error('alerts query function missing')
    await options.queryFn({ queryKey: options.queryKey, signal } as never)

    expect(fetchMock).toHaveBeenCalledWith(
      '/api/alerts?confidence_tier=ALL&timeRange=6h&search=',
      { signal }
    )
  })
})

describe('useLabelReviewMutation', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('posts the canonical review and invalidates the alert family after success', async () => {
    fetchMock.mockResolvedValueOnce(
      new Response(JSON.stringify({ id: 1, revision: 1 }), { status: 200 })
    )
    const queryClient = new QueryClient({
      defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
    })
    const invalidateQueriesSpy = vi.spyOn(queryClient, 'invalidateQueries')

    render(
      <QueryClientProvider client={queryClient}>
        <LabelReviewMutationHarness id="7" />
      </QueryClientProvider>
    )
    screen.getByRole('button', { name: 'submit' }).click()

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/alerts/7/label-review',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({
            verified_label: 'Normal',
            approval_state: 'excluded_from_training',
            review_note: 'Not suitable',
          }),
        })
      )
    })
    await waitFor(() => {
      expect(invalidateQueriesSpy).toHaveBeenCalledWith({ queryKey: ['alerts'] })
    })
  })
})
