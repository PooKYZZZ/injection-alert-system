import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, waitFor } from '@testing-library/react'
import { useEffect } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { useActionMutation } from './queries'

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

  useEffect(() => {
    mutation.mutate({ id, action: 'BLOCKED' })
  }, [id, mutation])

  return null
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
