import { afterEach, describe, expect, it, vi } from 'vitest'

import { readLoginThrottlePolicy } from './login-throttle-policy'

const names = [
  'AUTH_LOGIN_MAX_FAILURES_PER_IDENTIFIER',
  'AUTH_LOGIN_TURNSTILE_AFTER_FAILURES',
  'AUTH_LOGIN_IDENTIFIER_WINDOW_SECONDS',
  'AUTH_LOGIN_IDENTIFIER_COOLDOWN_SECONDS',
] as const

afterEach(() => {
  vi.unstubAllEnvs()
})

describe('login throttle policy', () => {
  it('uses the reviewed 3/5 thresholds, 300-second window, and 60-second cooldown', () => {
    for (const name of names) vi.stubEnv(name, '')
    expect(readLoginThrottlePolicy()).toEqual({
      challengeThreshold: 3,
      maxFailures: 5,
      windowSeconds: 300,
      cooldownSeconds: 60,
    })
  })

  it('keeps custom policy values within bounded, ordered limits', () => {
    vi.stubEnv('AUTH_LOGIN_MAX_FAILURES_PER_IDENTIFIER', '8')
    vi.stubEnv('AUTH_LOGIN_TURNSTILE_AFTER_FAILURES', '4')
    vi.stubEnv('AUTH_LOGIN_IDENTIFIER_WINDOW_SECONDS', '600')
    vi.stubEnv('AUTH_LOGIN_IDENTIFIER_COOLDOWN_SECONDS', '120')

    expect(readLoginThrottlePolicy()).toEqual({
      challengeThreshold: 4,
      maxFailures: 8,
      windowSeconds: 600,
      cooldownSeconds: 120,
    })
  })

  it('fails closed for malformed or incoherent thresholds', () => {
    vi.stubEnv('AUTH_LOGIN_MAX_FAILURES_PER_IDENTIFIER', '2')
    vi.stubEnv('AUTH_LOGIN_TURNSTILE_AFTER_FAILURES', '2')
    expect(() => readLoginThrottlePolicy()).toThrow(
      'Invalid login throttle configuration.'
    )

    vi.stubEnv('AUTH_LOGIN_TURNSTILE_AFTER_FAILURES', '')
    vi.stubEnv('AUTH_LOGIN_IDENTIFIER_WINDOW_SECONDS', '-1')
    expect(() => readLoginThrottlePolicy()).toThrow(
      'Invalid login throttle configuration.'
    )
  })
})
