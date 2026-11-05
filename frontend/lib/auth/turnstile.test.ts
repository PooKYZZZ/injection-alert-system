import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import {
  isTurnstileConfigured,
  readTurnstileConfiguration,
  shouldRequireTurnstile,
  verifyTurnstileToken,
} from './turnstile'

const TEST_SITE_KEY = '1x00000000000000000000AA'
const TEST_SECRET_KEY = '1x0000000000000000000000000000000AA'

describe('Turnstile boundary', () => {
  beforeEach(() => {
    vi.stubEnv('AUTH_TURNSTILE_ENABLED', 'true')
    vi.stubEnv('AUTH_TURNSTILE_SECRET_KEY', TEST_SECRET_KEY)
    vi.stubEnv('NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY', TEST_SITE_KEY)
    vi.stubEnv('AUTH_TURNSTILE_EXPECTED_HOSTNAME', 'localhost')
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it('requires a challenge after the configured third failed password', () => {
    expect(shouldRequireTurnstile(2)).toBe(false)
    expect(shouldRequireTurnstile(3)).toBe(true)
    expect(shouldRequireTurnstile(4)).toBe(true)
    expect(shouldRequireTurnstile(-1)).toBe(false)
  })

  it('validates token success, action and required hostname server-side', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({ success: true, action: 'login', hostname: 'localhost' }),
        { status: 200 }
      )
    )

    await expect(verifyTurnstileToken('token-value', fetchImpl)).resolves.toEqual({
      valid: true,
    })
    const [url, request] = fetchImpl.mock.calls[0]
    expect(url).toContain('siteverify')
    expect(request).toMatchObject({
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      signal: expect.any(AbortSignal),
    })
    const body = new URLSearchParams(request.body as string)
    expect(body.get('secret')).toBe(TEST_SECRET_KEY)
    expect(body.get('response')).toBe('token-value')
    expect(body.has('remoteip')).toBe(false)

    fetchImpl.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ success: true, action: 'reset', hostname: 'localhost' }),
        { status: 200 }
      )
    )
    await expect(verifyTurnstileToken('token-value', fetchImpl)).resolves.toEqual({
      valid: false,
      reason: 'invalid',
    })
  })

  it('accepts Cloudflare dummy-key responses only in managed loopback E2E', async () => {
    vi.stubEnv('NODE_ENV', 'production')
    vi.stubEnv('CYBERTRACE_E2E_MANAGED', 'true')
    vi.stubEnv('AUTH_APP_ORIGIN', 'http://127.0.0.1:3000')
    vi.stubEnv('SUPABASE_URL', 'http://127.0.0.1:54321')
    vi.stubEnv('AUTH_TURNSTILE_EXPECTED_HOSTNAME', '127.0.0.1')
    const fetchImpl = vi.fn().mockResolvedValue(
      new Response(
        JSON.stringify({
          success: true,
          hostname: 'example.com',
          'error-codes': [],
          metadata: { result_with_testing_key: true },
        }),
        { status: 200 }
      )
    )

    await expect(verifyTurnstileToken('token-value', fetchImpl)).resolves.toEqual({
      valid: true,
    })

    vi.stubEnv('CYBERTRACE_E2E_MANAGED', 'false')
    await expect(verifyTurnstileToken('token-value', fetchImpl)).resolves.toEqual({
      valid: false,
      reason: 'misconfigured',
    })
  })

  it('rejects missing, oversized, expired, replayed and wrong-host tokens', async () => {
    const fetchImpl = vi.fn()
    await expect(verifyTurnstileToken('', fetchImpl)).resolves.toMatchObject({
      valid: false,
      reason: 'invalid',
    })
    await expect(
      verifyTurnstileToken('x'.repeat(2049), fetchImpl)
    ).resolves.toMatchObject({ valid: false, reason: 'invalid' })
    expect(fetchImpl).not.toHaveBeenCalled()

    for (const result of [
      { success: false, 'error-codes': ['timeout-or-duplicate'] },
      { success: true, action: 'login', hostname: 'attacker.test' },
      { success: true, hostname: 'localhost' },
    ]) {
      fetchImpl.mockResolvedValueOnce(
        new Response(JSON.stringify(result), { status: 200 })
      )
      await expect(
        verifyTurnstileToken('token-value', fetchImpl)
      ).resolves.toMatchObject({ valid: false, reason: 'invalid' })
    }
  })

  it('fails closed with a bounded unavailable result on timeout or malformed responses', async () => {
    await expect(
      verifyTurnstileToken(
        'token-value',
        vi.fn().mockRejectedValue(new DOMException('timeout', 'TimeoutError'))
      )
    ).resolves.toEqual({ valid: false, reason: 'unavailable' })
    await expect(
      verifyTurnstileToken(
        'token-value',
        vi.fn().mockResolvedValue(new Response('not-json', { status: 200 }))
      )
    ).resolves.toEqual({ valid: false, reason: 'unavailable' })
    await expect(
      verifyTurnstileToken(
        'token-value',
        vi.fn().mockResolvedValue(new Response('offline', { status: 503 }))
      )
    ).resolves.toEqual({ valid: false, reason: 'unavailable' })
    for (const status of [400, 500]) {
      await expect(
        verifyTurnstileToken(
          'token-value',
          vi.fn().mockResolvedValue(new Response('offline', { status }))
        )
      ).resolves.toEqual({ valid: false, reason: 'unavailable' })
    }
  })

  it('requires complete configuration and rejects vendor test keys in production', () => {
    expect(readTurnstileConfiguration()).toMatchObject({
      siteKey: TEST_SITE_KEY,
      expectedHostname: 'localhost',
    })

    vi.stubEnv('AUTH_TURNSTILE_SECRET_KEY', '')
    expect(isTurnstileConfigured()).toBe(false)

    vi.stubEnv('AUTH_TURNSTILE_SECRET_KEY', TEST_SECRET_KEY)
    vi.stubEnv('NODE_ENV', 'production')
    expect(isTurnstileConfigured()).toBe(false)
    expect(readTurnstileConfiguration()).toBeNull()
  })

  it('fails closed when disabled or misconfigured', async () => {
    vi.stubEnv('AUTH_TURNSTILE_ENABLED', 'false')
    await expect(verifyTurnstileToken('token-value', vi.fn())).resolves.toEqual({
      valid: false,
      reason: 'misconfigured',
    })
    vi.stubEnv('AUTH_TURNSTILE_ENABLED', 'true')
    vi.stubEnv('NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY', '')
    await expect(verifyTurnstileToken('token-value', vi.fn())).resolves.toEqual({
      valid: false,
      reason: 'misconfigured',
    })
  })
})
