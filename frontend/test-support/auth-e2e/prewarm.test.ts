import { describe, expect, it, vi } from 'vitest'

import { AUTH_E2E_PREWARM_REQUESTS, prewarmAuthRoutes } from './prewarm'

describe('authentication E2E route prewarming', () => {
  it('compiles every critical route without following authentication redirects', async () => {
    const fetcher = vi.fn(async () => new Response(null, { status: 307 }))
    const sleep = vi.fn(async () => undefined)

    await prewarmAuthRoutes('http://127.0.0.1:3000', fetcher, sleep)

    expect(AUTH_E2E_PREWARM_REQUESTS).toEqual([
      { method: 'GET', path: '/dashboard' },
      { method: 'GET', path: '/mfa/enroll' },
      { method: 'GET', path: '/mfa/verify' },
      { method: 'GET', path: '/mfa/recover' },
      { method: 'GET', path: '/mfa/step-up' },
      { method: 'POST', path: '/api/auth/mfa/enroll' },
      { method: 'POST', path: '/api/auth/mfa/enroll/verify' },
      { method: 'POST', path: '/api/auth/mfa/enroll/finalize' },
      { method: 'POST', path: '/api/auth/mfa/verify' },
      { method: 'POST', path: '/api/auth/mfa/recovery/backup' },
      { method: 'POST', path: '/api/auth/mfa/recovery/email/request' },
      { method: 'POST', path: '/api/auth/mfa/recovery/email/verify' },
      { method: 'POST', path: '/api/auth/mfa/step-up' },
      { method: 'POST', path: '/api/auth/mfa/step-up/verify' },
    ])
    expect(fetcher).toHaveBeenCalledTimes(AUTH_E2E_PREWARM_REQUESTS.length)
    expect(fetcher).toHaveBeenCalledWith(
      'http://127.0.0.1:3000/dashboard',
      { method: 'GET', redirect: 'manual' }
    )
    expect(fetcher).toHaveBeenCalledWith(
      'http://127.0.0.1:3000/api/auth/mfa/enroll/verify',
      {
        headers: { origin: 'http://127.0.0.1:3000' },
        method: 'POST',
        redirect: 'manual',
      }
    )
    expect(sleep).toHaveBeenCalledWith(500)
  })
})
