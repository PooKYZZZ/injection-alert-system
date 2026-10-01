import { beforeEach, describe, expect, it, vi } from 'vitest'

const supabaseHarness = vi.hoisted(() => ({
  createClient: vi.fn(),
  readSupabaseServerEnv: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('@supabase/supabase-js', () => ({
  createClient: supabaseHarness.createClient,
}))
vi.mock('./env', () => ({
  readSupabaseServerEnv: supabaseHarness.readSupabaseServerEnv,
}))

import {
  createSupabaseFetchWithTimeout,
  getSupabaseServerClient,
} from './client'

describe('Supabase server client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    supabaseHarness.readSupabaseServerEnv.mockReturnValue({
      SUPABASE_URL: 'https://project.example.test',
      SUPABASE_SERVICE_ROLE_KEY: 'server-only-test-key',
    })
    supabaseHarness.createClient.mockReturnValue({})
  })

  it('registers its bounded fetch implementation as the client transport', () => {
    getSupabaseServerClient()

    expect(supabaseHarness.createClient).toHaveBeenCalledOnce()
    expect(supabaseHarness.createClient.mock.calls[0][2]).toMatchObject({
      global: { fetch: expect.any(Function) },
    })
  })

  it('aborts a Supabase request when it exceeds its deadline', async () => {
    const fetchImplementation: typeof fetch = (_input, init = {}) =>
      new Promise<Response>((_resolve, reject) => {
        const signal = init.signal
        if (!signal) {
          reject(new Error('Expected an abort signal.'))
          return
        }
        signal.addEventListener('abort', () => reject(signal.reason), {
          once: true,
        })
      })

    const request = createSupabaseFetchWithTimeout(
      25,
      fetchImplementation
    )('https://project.example.test/rest/v1/auth_accounts')

    await expect(request).rejects.toMatchObject({ name: 'TimeoutError' })
  })

  it('preserves cancellation from the caller', async () => {
    const fetchImplementation: typeof fetch = (_input, init = {}) =>
      new Promise<Response>((_resolve, reject) => {
        const signal = init.signal
        if (!signal) {
          reject(new Error('Expected an abort signal.'))
          return
        }
        signal.addEventListener('abort', () => reject(signal.reason), {
          once: true,
        })
      })
    const controller = new AbortController()
    const request = createSupabaseFetchWithTimeout(
      10_000,
      fetchImplementation
    )('https://project.example.test/rest/v1/auth_accounts', {
      signal: controller.signal,
    })

    controller.abort()

    await expect(request).rejects.toMatchObject({ name: 'AbortError' })
  })
})
