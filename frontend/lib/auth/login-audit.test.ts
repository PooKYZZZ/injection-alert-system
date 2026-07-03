import { afterEach, describe, expect, it, vi } from 'vitest'

import { writeLoginAudit } from './login-audit'

const originalRegistry = process.env.AUTH_USERS_JSON
const originalAuthSecret = process.env.AUTH_SECRET
const originalNextAuthSecret = process.env.NEXTAUTH_SECRET

function restoreEnvironment(name: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[name]
  } else {
    process.env[name] = value
  }
}

afterEach(() => {
  vi.restoreAllMocks()
  restoreEnvironment('AUTH_USERS_JSON', originalRegistry)
  restoreEnvironment('AUTH_SECRET', originalAuthSecret)
  restoreEnvironment('NEXTAUTH_SECRET', originalNextAuthSecret)
})

describe('writeLoginAudit', () => {
  it('writes a successful login as single-line JSON with allowed fields', () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)

    writeLoginAudit({
      event: 'auth.login_succeeded',
      level: 'info',
      outcome: 'success',
      userId: 'analyst-1',
      role: 'ANALYST',
      authzVersion: 2,
    })

    expect(log).toHaveBeenCalledTimes(1)
    const line = String(log.mock.calls[0][0])
    expect(line).not.toMatch(/[\r\n]/)
    expect(JSON.parse(line)).toMatchObject({
      level: 'info',
      event: 'auth.login_succeeded',
      component: 'auth',
      outcome: 'success',
      user_id: 'analyst-1',
      role: 'ANALYST',
      authz_version: 2,
    })
  })

  it('logs only identifier_hash and a fixed reason for failures', () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)
    const rawIdentifier = 'analyst@example.test'

    writeLoginAudit({
      event: 'auth.login_failed',
      level: 'warn',
      outcome: 'failure',
      identifierHash: 'abc123',
      reasonCode: 'INVALID_CREDENTIALS',
    })

    const line = String(log.mock.calls[0][0])
    expect(JSON.parse(line)).toMatchObject({
      identifier_hash: 'abc123',
      reason_code: 'INVALID_CREDENTIALS',
    })
    expect(line).not.toContain(rawIdentifier)
  })

  it('never serializes credentials, hashes, secrets, cookies, authorization, env JSON, or bodies', () => {
    const forbiddenValues = [
      'plaintext-password',
      'scrypt$v1$password-hash',
      'raw-auth-users-json',
      'auth-secret-value',
      'nextauth-secret-value',
      'session-cookie-value',
      'bearer-token-value',
      'raw-request-body',
    ]
    process.env.AUTH_USERS_JSON = forbiddenValues[2]
    process.env.AUTH_SECRET = forbiddenValues[3]
    process.env.NEXTAUTH_SECRET = forbiddenValues[4]
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)

    writeLoginAudit({
      event: 'auth.login_failed',
      level: 'warn',
      outcome: 'failure',
      identifierHash: 'safe-identifier-hash',
      reasonCode: 'INVALID_CREDENTIALS',
    })

    const line = String(log.mock.calls[0][0])
    for (const forbidden of forbiddenValues) {
      expect(line).not.toContain(forbidden)
    }
  })

  it('exposes no caller-controlled raw text fields', () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)

    writeLoginAudit({
      event: 'auth.login_throttled',
      level: 'warn',
      outcome: 'throttled',
      identifierHash: 'hash',
      reasonCode: 'GLOBAL_THROTTLED',
    })

    expect(Object.keys(JSON.parse(String(log.mock.calls[0][0]))).sort()).toEqual(
      [
        'component',
        'event',
        'identifier_hash',
        'level',
        'outcome',
        'reason_code',
        'timestamp',
      ].sort()
    )
  })

  it('strips control characters and caps the raw success user id', () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)

    writeLoginAudit({
      event: 'auth.login_succeeded',
      level: 'info',
      outcome: 'success',
      userId: `analyst\r\n\u0000${'x'.repeat(200)}`,
      role: 'ANALYST',
      authzVersion: 1,
    })

    const parsed = JSON.parse(String(log.mock.calls[0][0]))
    expect(parsed.user_id).not.toContain('\r')
    expect(parsed.user_id).not.toContain('\n')
    expect(parsed.user_id).not.toContain('\u0000')
    expect(parsed.user_id.length).toBeLessThanOrEqual(128)
  })

  it('does not let logging failure crash login behavior', () => {
    vi.spyOn(console, 'info').mockImplementation(() => {
      throw new Error('logger unavailable')
    })

    expect(() =>
      writeLoginAudit({
        event: 'auth.configuration_invalid',
        level: 'error',
        outcome: 'failure',
        identifierHash: 'hash',
        reasonCode: 'CONFIGURATION_INVALID',
      })
    ).not.toThrow()
  })

  it('writes authorization denials as safe parseable single-line JSON', () => {
    const forbiddenValues = [
      'plaintext-password',
      'scrypt$v1$password-hash',
      'raw-auth-users-json',
      'auth-secret-value',
      'nextauth-secret-value',
      'session-cookie-value',
      'bearer-token-value',
      'analyst@example.test',
      'raw-credentials',
      'raw-request-body',
    ]
    process.env.AUTH_USERS_JSON = forbiddenValues[2]
    process.env.AUTH_SECRET = forbiddenValues[3]
    process.env.NEXTAUTH_SECRET = forbiddenValues[4]
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)

    writeLoginAudit({
      event: 'auth.session_stale',
      level: 'warn',
      outcome: 'denied',
      userId: `analyst-1\r\n${'x'.repeat(200)}`,
      role: 'ANALYST',
      authzVersion: 1,
      reasonCode: 'AUTHZ_VERSION_MISMATCH',
    })

    const line = String(log.mock.calls[0][0])
    expect(line).not.toMatch(/[\r\n]/)
    const parsed = JSON.parse(line)
    expect(parsed).toMatchObject({
      event: 'auth.session_stale',
      outcome: 'denied',
      user_id: expect.any(String),
      role: 'ANALYST',
      authz_version: 1,
      reason_code: 'AUTHZ_VERSION_MISMATCH',
    })
    expect(parsed.user_id.length).toBeLessThanOrEqual(128)
    for (const forbidden of forbiddenValues) {
      expect(line).not.toContain(forbidden)
    }
  })
})
