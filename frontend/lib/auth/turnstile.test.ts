import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import { shouldRequireTurnstile, verifyTurnstileToken } from './turnstile'

describe('Turnstile boundary', () => {
  beforeEach(() => {
    process.env.AUTH_TURNSTILE_ENABLED = 'true'
    process.env.AUTH_TURNSTILE_SECRET_KEY = 'test-secret-not-for-production'
  })

  it('requires a challenge after five failures', () => {
    expect(shouldRequireTurnstile(4)).toBe(false)
    expect(shouldRequireTurnstile(5)).toBe(true)
  })

  it('validates success, action, and hostname without logging the token', async () => {
    const fetchImpl = vi.fn().mockResolvedValue(new Response(JSON.stringify({ success: true, action: 'login', hostname: 'localhost' }), { status: 200 }))
    await expect(verifyTurnstileToken('token-value', 'login', 'localhost', fetchImpl)).resolves.toBe(true)
    expect(fetchImpl).toHaveBeenCalledWith(expect.stringContaining('siteverify'), expect.objectContaining({ method: 'POST' }))
    await expect(verifyTurnstileToken('token-value', 'reset', 'localhost', fetchImpl)).resolves.toBe(false)
  })

  it('fails closed when disabled, malformed, or unavailable', async () => {
    process.env.AUTH_TURNSTILE_ENABLED = 'false'
    await expect(verifyTurnstileToken('token', 'login', undefined, vi.fn())).resolves.toBe(false)
    process.env.AUTH_TURNSTILE_ENABLED = 'true'
    await expect(verifyTurnstileToken('', 'login', undefined, vi.fn())).resolves.toBe(false)
    await expect(verifyTurnstileToken('token', 'login', undefined, vi.fn().mockRejectedValue(new Error('offline')))).resolves.toBe(false)
  })
})
