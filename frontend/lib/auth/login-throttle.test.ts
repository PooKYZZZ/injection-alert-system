import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  LoginThrottle,
  PasswordHashConcurrencyGate,
  hashNormalizedIdentifier,
} from './login-throttle'

type CapturedAuthConfig = {
  session: unknown
  jwt: unknown
  providers: Array<{
    credentials: unknown
    authorize: (
      credentials: Record<string, unknown>
    ) => Promise<Record<string, unknown> | null>
  }>
  callbacks: {
    jwt: (input: {
      token: Record<string, unknown>
      user: Record<string, unknown> | null
    }) => Promise<Record<string, unknown>>
    session: (input: {
      session: { user: Record<string, unknown> }
      token: Record<string, unknown>
    }) => Promise<{ user: Record<string, unknown> }>
  }
}

const authHarness = vi.hoisted(() => ({
  config: null as CapturedAuthConfig | null,
  verifyPasswordForAccount: vi.fn(),
  writeLoginAudit: vi.fn(),
}))

vi.mock('next-auth', () => ({
  default: vi.fn((config: CapturedAuthConfig) => {
    authHarness.config = config
    return {
      handlers: {},
      auth: vi.fn(),
      signIn: vi.fn(),
      signOut: vi.fn(),
    }
  }),
}))

vi.mock('next-auth/providers/credentials', () => ({
  default: vi.fn((config: Record<string, unknown>) => config),
}))

vi.mock('./password-hash', async (importOriginal) => {
  const actual = await importOriginal<typeof import('./password-hash')>()
  return {
    ...actual,
    verifyPasswordForAccount: authHarness.verifyPasswordForAccount,
  }
})

vi.mock('./login-audit', () => ({
  writeLoginAudit: authHarness.writeLoginAudit,
}))

function capturedAuthConfig(): CapturedAuthConfig {
  if (!authHarness.config) {
    throw new Error('Auth.js configuration was not captured')
  }
  return authHarness.config
}

const originalAuthSecret = process.env.AUTH_SECRET
const originalRegistry = process.env.AUTH_USERS_JSON
const originalSocDemoPassword = process.env.SOC_DEMO_PASSWORD
const originalDemoPassword = process.env.DEMO_PASSWORD

function restoreEnvironment(name: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[name]
  } else {
    process.env[name] = value
  }
}

afterEach(() => {
  restoreEnvironment('AUTH_SECRET', originalAuthSecret)
  restoreEnvironment('AUTH_USERS_JSON', originalRegistry)
  restoreEnvironment('SOC_DEMO_PASSWORD', originalSocDemoPassword)
  restoreEnvironment('DEMO_PASSWORD', originalDemoPassword)
})

function createThrottle(now: () => number) {
  return new LoginThrottle(
    {
      identifierMaxFailures: 2,
      identifierWindowMs: 1_000,
      identifierCooldownMs: 2_000,
      globalMaxFailures: 3,
      globalWindowMs: 1_000,
      globalCooldownMs: 2_000,
    },
    now
  )
}

describe('LoginThrottle', () => {
  it('blocks an identifier after its failure threshold', () => {
    const throttle = createThrottle(() => 0)
    const first = throttle.check(' Analyst@Example.Test ')

    expect(first.allowed).toBe(true)
    throttle.recordFailure(first.identifierHash)
    throttle.recordFailure(first.identifierHash)

    expect(throttle.check('analyst@example.test')).toMatchObject({
      allowed: false,
      reasonCode: 'IDENTIFIER_THROTTLED',
    })
  })

  it('successful login resets the identifier counter', () => {
    const throttle = createThrottle(() => 0)
    const attempt = throttle.check('analyst@example.test')
    throttle.recordFailure(attempt.identifierHash)
    throttle.recordSuccess(attempt.identifierHash)
    throttle.recordFailure(attempt.identifierHash)

    expect(throttle.check('analyst@example.test').allowed).toBe(true)
  })

  it('blocks all identifiers after the global threshold', () => {
    const throttle = createThrottle(() => 0)

    for (const identifier of ['one@example.test', 'two@example.test', 'three@example.test']) {
      const attempt = throttle.check(identifier)
      throttle.recordFailure(attempt.identifierHash)
    }

    expect(throttle.check('new@example.test')).toMatchObject({
      allowed: false,
      reasonCode: 'GLOBAL_THROTTLED',
    })
  })

  it('allows attempts again after cooldown without leaking a distinct user outcome', () => {
    let now = 0
    const throttle = createThrottle(() => now)
    const attempt = throttle.check('analyst@example.test')
    throttle.recordFailure(attempt.identifierHash)
    throttle.recordFailure(attempt.identifierHash)

    expect(throttle.check('analyst@example.test').allowed).toBe(false)
    now = 2_001
    expect(throttle.check('analyst@example.test')).toEqual({
      allowed: true,
      identifierHash: attempt.identifierHash,
    })
  })

  it('keeps an active cooldown after the counting window expires', () => {
    let now = 0
    const throttle = createThrottle(() => now)
    const attempt = throttle.check('analyst@example.test')
    now = 900
    throttle.recordFailure(attempt.identifierHash)
    throttle.recordFailure(attempt.identifierHash)

    now = 1_100
    expect(throttle.check('analyst@example.test')).toMatchObject({
      allowed: false,
      reasonCode: 'IDENTIFIER_THROTTLED',
    })

    now = 2_901
    expect(throttle.check('analyst@example.test').allowed).toBe(true)
  })

  it('keys counters by a hash of the normalized identifier', () => {
    const rawIdentifier = ' Analyst@Example.Test '
    const throttle = createThrottle(() => 0)
    const attempt = throttle.check(rawIdentifier)

    expect(attempt.identifierHash).toBe(
      hashNormalizedIdentifier('analyst@example.test')
    )
    expect(attempt.identifierHash).not.toContain('analyst')
    expect(JSON.stringify(attempt)).not.toContain(rawIdentifier)
  })

  it('keeps state isolated to each in-memory instance', () => {
    const first = createThrottle(() => 0)
    const attempt = first.check('analyst@example.test')
    first.recordFailure(attempt.identifierHash)
    first.recordFailure(attempt.identifierHash)

    const restartedProcess = createThrottle(() => 0)
    expect(restartedProcess.check('analyst@example.test').allowed).toBe(true)
  })

  it('does not accept or inspect IP or X-Forwarded-For input', () => {
    const throttle = createThrottle(() => 0)
    expect(throttle.check).toHaveLength(1)
  })
})

describe('PasswordHashConcurrencyGate', () => {
  it('allows two concurrent attempts and rejects a third', async () => {
    const gate = new PasswordHashConcurrencyGate(2)
    const releases: Array<() => void> = []
    const task = () =>
      new Promise<string>((resolve) => {
        releases.push(() => resolve('verified'))
      })

    const first = gate.run(task)
    const second = gate.run(task)
    const third = await gate.run(task)

    expect(third).toEqual({ ok: false, reasonCode: 'PASSWORD_HASH_BUSY' })
    expect(releases).toHaveLength(2)
    releases.forEach((release) => release())
    await expect(first).resolves.toEqual({ ok: true, value: 'verified' })
    await expect(second).resolves.toEqual({ ok: true, value: 'verified' })
  })

  it('uses the generic concurrency env var and ignores the old scrypt variable', async () => {
    vi.resetModules()
    process.env.AUTH_PASSWORD_HASH_CONCURRENCY_LIMIT = '2'
    process.env.AUTH_SCRYPT_CONCURRENCY_LIMIT = '1'
    const { passwordHashConcurrencyGate } = await import('./login-throttle')
    const releases: Array<() => void> = []
    const task = () =>
      new Promise<string>((resolve) => {
        releases.push(() => resolve('verified'))
      })

    const first = passwordHashConcurrencyGate.run(task)
    const second = passwordHashConcurrencyGate.run(task)
    const third = await passwordHashConcurrencyGate.run(task)

    expect(releases).toHaveLength(2)
    expect(third).toEqual({
      ok: false,
      reasonCode: 'PASSWORD_HASH_BUSY',
    })
    releases.forEach((release) => release())
    await Promise.all([first, second])
    delete process.env.AUTH_PASSWORD_HASH_CONCURRENCY_LIMIT
    delete process.env.AUTH_SCRYPT_CONCURRENCY_LIMIT
  })
})

describe('Auth.js account integration', () => {
  beforeEach(async () => {
    vi.resetModules()
    authHarness.config = null
    authHarness.verifyPasswordForAccount.mockReset()
    authHarness.writeLoginAudit.mockReset()
    process.env.AUTH_SECRET = 'test-auth-secret'
    process.env.AUTH_USERS_JSON = JSON.stringify([
      {
        id: 'analyst-1',
        email: 'analyst@example.test',
        name: 'SOC Analyst',
        role: 'ANALYST',
        authz_version: 3,
        password_hash: 'scrypt$v1$test-hash',
      },
    ])
    await import('@/auth')
  })

  it('uses identifier/password credentials and an eight-hour JWT session', () => {
    const config = capturedAuthConfig()
    expect(config.session).toEqual({
      strategy: 'jwt',
      maxAge: 8 * 60 * 60,
    })
    expect(config.jwt).toEqual({ maxAge: 8 * 60 * 60 })
    expect(config.providers[0].credentials).toEqual({
      identifier: expect.objectContaining({ type: 'text' }),
      password: expect.objectContaining({ type: 'password' }),
    })
  })

  it('wires unknown accounts through the dummy verification path', async () => {
    authHarness.verifyPasswordForAccount.mockResolvedValue(false)
    const authorize = capturedAuthConfig().providers[0].authorize

    await expect(
      authorize({
        identifier: 'unknown@example.test',
        password: 'not-the-password',
      })
    ).resolves.toBeNull()
    expect(authHarness.verifyPasswordForAccount).toHaveBeenCalledWith(
      'not-the-password',
      null
    )
  })

  it('returns named account claims and persists them through JWT/session callbacks', async () => {
    authHarness.verifyPasswordForAccount.mockResolvedValue(true)
    const config = capturedAuthConfig()
    const authorize = config.providers[0].authorize
    const user = await authorize({
      identifier: 'analyst@example.test',
      password: 'correct-password',
    })

    expect(user).toEqual({
      id: 'analyst-1',
      email: 'analyst@example.test',
      name: 'SOC Analyst',
      role: 'ANALYST',
      authz_version: 3,
    })

    const token = await config.callbacks.jwt({ token: {}, user })
    expect(token).toMatchObject({
      id: 'analyst-1',
      role: 'ANALYST',
      authz_version: 3,
    })

    const session = await config.callbacks.session({
      session: { user: {} },
      token,
    })
    expect(session.user).toMatchObject({
      id: 'analyst-1',
      role: 'ANALYST',
      authz_version: 3,
    })
  })

  it('has no reachable demo-password fallback when registry configuration is absent', async () => {
    delete process.env.AUTH_USERS_JSON
    process.env.SOC_DEMO_PASSWORD = 'legacy-password'
    process.env.DEMO_PASSWORD = 'legacy-password'
    authHarness.verifyPasswordForAccount.mockResolvedValue(true)
    const authorize = capturedAuthConfig().providers[0].authorize

    await expect(
      authorize({ identifier: 'soc', password: 'legacy-password' })
    ).resolves.toBeNull()
    expect(authHarness.writeLoginAudit).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'auth.configuration_invalid',
        reasonCode: 'CONFIGURATION_INVALID',
      })
    )
  })
})
