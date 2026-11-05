import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { UserRole } from './roles'

const TEST_ARGON2_HASH =
  '$argon2id$v=19$m=19456,t=2,p=1$mockSalt$mockHash'

type LoginAccount = {
  id: string
  email: string
  username: string | null
  name: string
  role: UserRole
  authzVersion: number
  passwordHash: string | null
  mfaRequired: boolean
  disabledAt: string | null
}

type CapturedConfig = {
  providers: Array<{
    credentials: Record<string, unknown>
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
  config: null as CapturedConfig | null,
  findAccount: vi.fn(),
  verifyPasswordForAccount: vi.fn(),
  writeLoginAudit: vi.fn(),
  beginThrottleAttempt: vi.fn(),
  completeThrottleAttempt: vi.fn(),
  verifyTurnstileToken: vi.fn(),
  isTurnstileConfigured: vi.fn(),
  beginMfaChallenge: vi.fn(),
  consumeMfaCompletion: vi.fn(),
  consumeRecoveryCompletion: vi.fn(),
  setPreAuthCookie: vi.fn(),
}))

vi.mock('next-auth', () => ({
  CredentialsSignin: class CredentialsSignin extends Error {
    code = 'credentials'
    type = 'CredentialsSignin'
  },
  default: vi.fn((config: CapturedConfig) => {
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

/**
 * This test validates auth control flow, not native Argon2.
 * Real Argon2id hash/verify coverage lives in password-hash.test.ts.
 * Keep this mock pure. Do not use importOriginal()/vi.importActual(),
 * because that loads the native argon2 addon in Vitest workers.
 */
vi.mock('./password-hash', () => {
  return {
    PASSWORD_HASH_CONCURRENCY_LIMIT: 2,
    verifyPasswordForAccount: authHarness.verifyPasswordForAccount,
  }
})

vi.mock('../server/db/auth-accounts', () => ({
  findAuthAccountByIdentifier: authHarness.findAccount,
}))

vi.mock('../server/db/login-throttle', () => ({
  beginLoginThrottleAttempt: authHarness.beginThrottleAttempt,
  completeLoginThrottleAttempt: authHarness.completeThrottleAttempt,
}))

vi.mock('./turnstile', () => ({
  isTurnstileEnabled: () => process.env.AUTH_TURNSTILE_ENABLED === 'true',
  isTurnstileConfigured: authHarness.isTurnstileConfigured,
  shouldRequireTurnstile: (failureCount: number) => failureCount >= 3,
  verifyTurnstileToken: authHarness.verifyTurnstileToken,
}))

vi.mock('./login-audit', () => ({
  writeLoginAudit: authHarness.writeLoginAudit,
}))

vi.mock('server-only', () => ({}))
vi.mock('../server/db/mfa-challenges', () => ({
  beginLoginMfaChallenge: authHarness.beginMfaChallenge,
  consumeMfaCompletionToken: authHarness.consumeMfaCompletion,
}))
vi.mock('../server/db/mfa-recovery', () => ({
  consumeRecoveryCompletionToken: authHarness.consumeRecoveryCompletion,
}))
vi.mock('./preauth', () => ({
  setPreAuthCookie: authHarness.setPreAuthCookie,
}))

function capturedConfig(): CapturedConfig {
  if (!authHarness.config) {
    throw new Error('Auth.js configuration was not captured')
  }
  return authHarness.config
}

function validAccount(
  overrides: Partial<LoginAccount> = {}
): LoginAccount {
  return {
    id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
    email: 'admin@example.test',
    username: 'soc-admin',
    name: 'SOC Admin',
    role: 'ADMIN',
    authzVersion: 3,
    passwordHash: null,
    mfaRequired: false,
    disabledAt: null,
    ...overrides,
  }
}

const originalAuthSecret = process.env.AUTH_SECRET
const originalRegistry = process.env.AUTH_USERS_JSON
const originalIdentifierMaxFailures =
  process.env.AUTH_LOGIN_MAX_FAILURES_PER_IDENTIFIER
const originalTurnstileEnabled = process.env.AUTH_TURNSTILE_ENABLED
const originalTurnstileSecret = process.env.AUTH_TURNSTILE_SECRET_KEY
const originalTurnstileSiteKey = process.env.NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY
const originalTurnstileHostname = process.env.AUTH_TURNSTILE_EXPECTED_HOSTNAME

function restoreEnvironment(name: string, value: string | undefined): void {
  if (value === undefined) {
    delete process.env[name]
  } else {
    process.env[name] = value
  }
}

afterEach(() => {
  vi.resetModules()
  vi.restoreAllMocks()
  restoreEnvironment('AUTH_SECRET', originalAuthSecret)
  restoreEnvironment('AUTH_USERS_JSON', originalRegistry)
  restoreEnvironment(
    'AUTH_LOGIN_MAX_FAILURES_PER_IDENTIFIER',
    originalIdentifierMaxFailures
  )
  restoreEnvironment('AUTH_TURNSTILE_ENABLED', originalTurnstileEnabled)
  restoreEnvironment('AUTH_TURNSTILE_SECRET_KEY', originalTurnstileSecret)
  restoreEnvironment(
    'NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY',
    originalTurnstileSiteKey
  )
  restoreEnvironment('AUTH_TURNSTILE_EXPECTED_HOSTNAME', originalTurnstileHostname)
})

beforeEach(() => {
  authHarness.config = null
  authHarness.findAccount.mockReset()
  authHarness.verifyPasswordForAccount.mockReset()
  authHarness.verifyPasswordForAccount.mockResolvedValue(false)
  authHarness.writeLoginAudit.mockReset()
  authHarness.beginThrottleAttempt.mockReset()
  authHarness.beginThrottleAttempt.mockResolvedValue({
    allowed: true,
    failureCount: 0,
    attemptId: 'd5c60380-817f-4f07-aadc-0ff30a2cb6dc',
  })
  authHarness.completeThrottleAttempt.mockReset()
  authHarness.completeThrottleAttempt.mockResolvedValue({
    completed: true,
    failureCount: 0,
    cooldownActive: false,
  })
  authHarness.verifyTurnstileToken.mockReset()
  authHarness.verifyTurnstileToken.mockResolvedValue({ valid: true })
  authHarness.isTurnstileConfigured.mockReset()
  authHarness.isTurnstileConfigured.mockReturnValue(true)
  authHarness.beginMfaChallenge.mockReset()
  authHarness.consumeMfaCompletion.mockReset()
  authHarness.consumeRecoveryCompletion.mockReset()
  authHarness.setPreAuthCookie.mockReset()
  authHarness.beginMfaChallenge.mockResolvedValue({
    challenge_id: 'challenge-1',
    handle: 'a'.repeat(43),
  })
  authHarness.setPreAuthCookie.mockResolvedValue(undefined)
  process.env.AUTH_SECRET = 'test-auth-secret'
  delete process.env.AUTH_TURNSTILE_ENABLED
  delete process.env.AUTH_TURNSTILE_SECRET_KEY
  delete process.env.NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY
  delete process.env.AUTH_TURNSTILE_EXPECTED_HOSTNAME
  delete process.env.AUTH_USERS_JSON
})

describe('Auth.js credential login', () => {
  it('declares every credential field consumed by authorize', async () => {
    await import('@/auth')

    expect(Object.keys(capturedConfig().providers[0].credentials)).toEqual([
      'identifier',
      'password',
      'mfa_completion_token',
      'recovery_completion_token',
      'turnstile_token',
    ])
  })

  it.each([
    {
      identifier: 'admin@example.test',
      password: 'password',
      mfa_completion_token: 'a'.repeat(43),
    },
    {
      mfa_completion_token: 'a'.repeat(43),
      recovery_completion_token: 'b'.repeat(43),
    },
  ])('rejects mixed credential modes before consuming or querying', async (credentials) => {
    authHarness.consumeMfaCompletion.mockResolvedValue({
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      name: 'SOC Admin',
      email: 'admin@example.test',
      role: 'ADMIN',
      authz_version: 4,
      auth_level: 'mfa',
      auth_method: 'totp',
      verified_at: '2026-07-11T02:00:00.000Z',
      completion_purpose: 'login_mfa',
    })
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize(credentials)
    ).resolves.toBeNull()
    expect(authHarness.consumeMfaCompletion).not.toHaveBeenCalled()
    expect(authHarness.consumeRecoveryCompletion).not.toHaveBeenCalled()
    expect(authHarness.findAccount).not.toHaveBeenCalled()
  })

  it('logs in a DB account and preserves JWT/session claim shape', async () => {
    const password = 'correct horse battery staple'
    authHarness.verifyPasswordForAccount.mockImplementation(
      async (candidatePassword, candidateHash) =>
        candidatePassword === password && candidateHash === TEST_ARGON2_HASH
    )
    authHarness.findAccount.mockResolvedValue(
      validAccount({ passwordHash: TEST_ARGON2_HASH })
    )
    await import('@/auth')

    const config = capturedConfig()
    const user = await config.providers[0].authorize({
      identifier: 'admin@example.test',
      password,
    })

    expect(authHarness.findAccount).toHaveBeenCalledWith('admin@example.test')
    expect(authHarness.verifyPasswordForAccount).toHaveBeenCalledWith(
      password,
      TEST_ARGON2_HASH
    )
    expect(authHarness.beginThrottleAttempt).toHaveBeenCalledWith(
      '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      { turnstileEnabled: false, turnstileVerified: false }
    )
    expect(authHarness.verifyTurnstileToken).not.toHaveBeenCalled()
    expect(user).toMatchObject({
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      email: 'admin@example.test',
      name: 'SOC Admin',
      role: 'ADMIN',
      authz_version: 3,
      auth_level: 'password',
      auth_method: 'password',
      auth_time: expect.any(Number),
    })

    const token = await config.callbacks.jwt({ token: {}, user })
    expect(token).toMatchObject({
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      role: 'ADMIN',
      authz_version: 3,
    })
    const session = await config.callbacks.session({
      session: { user: {} },
      token,
    })
    expect(session.user).toMatchObject({
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      role: 'ADMIN',
      authz_version: 3,
    })
  })

  it('rejects a wrong password with the generic credential failure path', async () => {
    authHarness.findAccount.mockResolvedValue(
      validAccount({
        passwordHash: TEST_ARGON2_HASH,
      })
    )
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password: 'wrong password',
      })
    ).resolves.toBeNull()
    expect(authHarness.writeLoginAudit).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'auth.login_failed',
        reasonCode: 'INVALID_CREDENTIALS',
      })
    )
  })

  it('requires Turnstile at the authorization boundary after three failed passwords', async () => {
    process.env.AUTH_TURNSTILE_ENABLED = 'true'
    authHarness.findAccount.mockResolvedValue(validAccount())
    authHarness.beginThrottleAttempt.mockResolvedValue({
      allowed: false,
      failureCount: 3,
      reasonCode: 'VERIFICATION_REQUIRED',
    })
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password: 'fourth-password-guess',
      })
    ).rejects.toMatchObject({ code: 'verification_required' })
    expect(authHarness.verifyTurnstileToken).not.toHaveBeenCalled()
    expect(authHarness.verifyPasswordForAccount).not.toHaveBeenCalled()
    expect(authHarness.completeThrottleAttempt).not.toHaveBeenCalled()
  })

  it('verifies a required token before Argon2 and keeps wrong passwords counted', async () => {
    process.env.AUTH_TURNSTILE_ENABLED = 'true'
    authHarness.beginThrottleAttempt
      .mockResolvedValueOnce({
        allowed: false,
        failureCount: 3,
        reasonCode: 'VERIFICATION_REQUIRED',
      })
      .mockResolvedValueOnce({
        allowed: true,
        failureCount: 3,
        attemptId: 'd5c60380-817f-4f07-aadc-0ff30a2cb6dc',
      })
    authHarness.completeThrottleAttempt.mockResolvedValue({
      completed: true,
      failureCount: 4,
      cooldownActive: false,
    })
    authHarness.findAccount.mockResolvedValue(
      validAccount({ passwordHash: TEST_ARGON2_HASH })
    )
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password: 'wrong-password',
        turnstile_token: 'single-use-token',
      })
    ).rejects.toMatchObject({ code: 'verification_required' })
    expect(authHarness.verifyTurnstileToken).toHaveBeenCalledWith(
      'single-use-token'
    )
    expect(authHarness.beginThrottleAttempt).toHaveBeenNthCalledWith(
      2,
      '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      { turnstileEnabled: true, turnstileVerified: true }
    )
    expect(authHarness.verifyPasswordForAccount).toHaveBeenCalledOnce()
    expect(authHarness.completeThrottleAttempt).toHaveBeenCalledWith(
      '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      'd5c60380-817f-4f07-aadc-0ff30a2cb6dc',
      'failure'
    )
  })

  it('requires a fresh one-use token after a challenged password is wrong', async () => {
    process.env.AUTH_TURNSTILE_ENABLED = 'true'
    authHarness.beginThrottleAttempt
      .mockResolvedValueOnce({
        allowed: false,
        failureCount: 3,
        reasonCode: 'VERIFICATION_REQUIRED',
      })
      .mockResolvedValueOnce({
        allowed: true,
        failureCount: 3,
        attemptId: 'd5c60380-817f-4f07-aadc-0ff30a2cb6dc',
      })
      .mockResolvedValueOnce({
        allowed: false,
        failureCount: 4,
        reasonCode: 'VERIFICATION_REQUIRED',
      })
    authHarness.completeThrottleAttempt.mockResolvedValue({
      completed: true,
      failureCount: 4,
      cooldownActive: false,
    })
    authHarness.findAccount.mockResolvedValue(
      validAccount({ passwordHash: TEST_ARGON2_HASH })
    )
    await import('@/auth')
    const authorize = capturedConfig().providers[0].authorize

    await expect(
      authorize({
        identifier: 'admin@example.test',
        password: 'wrong-password',
        turnstile_token: 'first-single-use-token',
      })
    ).rejects.toMatchObject({ code: 'verification_required' })
    await expect(
      authorize({ identifier: 'admin@example.test', password: 'another-guess' })
    ).rejects.toMatchObject({ code: 'verification_required' })

    expect(authHarness.verifyTurnstileToken).toHaveBeenCalledOnce()
    expect(authHarness.verifyTurnstileToken).toHaveBeenCalledWith(
      'first-single-use-token'
    )
    expect(authHarness.verifyPasswordForAccount).toHaveBeenCalledOnce()
    expect(authHarness.completeThrottleAttempt).toHaveBeenCalledWith(
      '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      'd5c60380-817f-4f07-aadc-0ff30a2cb6dc',
      'failure'
    )
  })

  it('valid Turnstile permits only the password check and preserves the MFA handoff', async () => {
    process.env.AUTH_TURNSTILE_ENABLED = 'true'
    authHarness.beginThrottleAttempt
      .mockResolvedValueOnce({
        allowed: false,
        failureCount: 3,
        reasonCode: 'VERIFICATION_REQUIRED',
      })
      .mockResolvedValueOnce({
        allowed: true,
        failureCount: 3,
        attemptId: 'd5c60380-817f-4f07-aadc-0ff30a2cb6dc',
      })
    authHarness.verifyPasswordForAccount.mockResolvedValue(true)
    authHarness.findAccount.mockResolvedValue(
      validAccount({ passwordHash: TEST_ARGON2_HASH, mfaRequired: true })
    )
    await import('@/auth')

    const user = await capturedConfig().providers[0].authorize({
      identifier: 'admin@example.test',
      password: 'correct horse battery staple',
      turnstile_token: 'single-use-token',
    })

    expect(user).toMatchObject({ auth_level: 'password', auth_method: 'password' })
    expect(authHarness.beginMfaChallenge).toHaveBeenCalledWith(
      '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
    )
    expect(authHarness.completeThrottleAttempt).toHaveBeenCalledWith(
      '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      'd5c60380-817f-4f07-aadc-0ff30a2cb6dc',
      'success'
    )
  })

  it('fails closed when shared throttle storage is unavailable', async () => {
    authHarness.findAccount.mockResolvedValue(validAccount())
    authHarness.beginThrottleAttempt.mockRejectedValue(
      new Error('database URL and service role leaked')
    )
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password: 'password',
      })
    ).rejects.toThrow('Authentication account store unavailable')
    expect(authHarness.verifyPasswordForAccount).not.toHaveBeenCalled()
    expect(JSON.stringify(authHarness.writeLoginAudit.mock.calls)).not.toContain(
      'service role leaked'
    )
  })

  it('fails closed when a required challenge is enabled without valid keys', async () => {
    process.env.AUTH_TURNSTILE_ENABLED = 'true'
    authHarness.isTurnstileConfigured.mockReturnValue(false)
    authHarness.findAccount.mockResolvedValue(validAccount())
    authHarness.beginThrottleAttempt.mockResolvedValue({
      allowed: false,
      failureCount: 3,
      reasonCode: 'VERIFICATION_REQUIRED',
    })
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password: 'password',
      })
    ).rejects.toThrow('Login verification is unavailable.')
    expect(authHarness.verifyTurnstileToken).not.toHaveBeenCalled()
    expect(authHarness.verifyPasswordForAccount).not.toHaveBeenCalled()
    expect(authHarness.writeLoginAudit).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'auth.login_challenge_unavailable',
        reasonCode: 'CONFIGURATION_INVALID',
      })
    )
  })

  it('uses canonical account identity for email, username, and UUID attempts', async () => {
    authHarness.findAccount.mockResolvedValue(
      validAccount({ passwordHash: TEST_ARGON2_HASH })
    )
    await import('@/auth')
    const authorize = capturedConfig().providers[0].authorize

    await authorize({ identifier: 'admin@example.test', password: 'wrong' })
    await authorize({ identifier: 'soc-admin', password: 'wrong' })
    await authorize({
      identifier: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      password: 'wrong',
    })

    expect(authHarness.beginThrottleAttempt).toHaveBeenNthCalledWith(
      1,
      '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      expect.any(Object)
    )
    expect(authHarness.beginThrottleAttempt).toHaveBeenNthCalledWith(
      2,
      '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      expect.any(Object)
    )
    expect(authHarness.beginThrottleAttempt).toHaveBeenNthCalledWith(
      3,
      '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      expect.any(Object)
    )
  })

  it('bounds a password-level MFA session to the database challenge expiry', async () => {
    authHarness.verifyPasswordForAccount.mockResolvedValue(true)
    authHarness.findAccount.mockResolvedValue(
      validAccount({ passwordHash: TEST_ARGON2_HASH, mfaRequired: true })
    )
    authHarness.beginMfaChallenge.mockResolvedValue({
      challenge_id: 'challenge-1',
      handle: 'a'.repeat(43),
      purpose: 'login_mfa',
      expires_at: '2030-01-01T00:10:00.000Z',
    })
    await import('@/auth')

    const user = await capturedConfig().providers[0].authorize({
      identifier: 'admin@example.test',
      password: 'correct horse battery staple',
    })
    const token = await capturedConfig().callbacks.jwt({ token: {}, user })

    expect(user).toMatchObject({
      mfa_challenge_purpose: 'login_mfa',
      mfa_challenge_expires_at: '2030-01-01T00:10:00.000Z',
    })
    expect(token.exp).toBe(Math.floor(Date.parse('2030-01-01T00:10:00.000Z') / 1_000))
  })

  it('does not report an MFA challenge storage failure as invalid credentials', async () => {
    authHarness.verifyPasswordForAccount.mockResolvedValue(true)
    authHarness.findAccount.mockResolvedValue(
      validAccount({ passwordHash: TEST_ARGON2_HASH, mfaRequired: true })
    )
    authHarness.beginMfaChallenge.mockRejectedValue(
      new Error('raw database connection details')
    )
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password: 'correct horse battery staple',
      })
    ).rejects.toThrow('Authentication account store unavailable')
    expect(authHarness.writeLoginAudit).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'auth.account_lookup_failed',
        level: 'error',
        reasonCode: 'ACCOUNT_LOOKUP_FAILED',
      })
    )
    expect(JSON.stringify(authHarness.writeLoginAudit.mock.calls)).not.toContain(
      'raw database connection details'
    )
  })

  it('uses the dummy-verification contract when the DB account is missing', async () => {
    authHarness.findAccount.mockResolvedValue(undefined)
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'unknown@example.test',
        password: 'not-the-password',
      })
    ).resolves.toBeNull()
    expect(authHarness.verifyPasswordForAccount).toHaveBeenCalledWith(
      'not-the-password',
      null
    )
    expect(authHarness.beginThrottleAttempt).not.toHaveBeenCalled()
  })

  it.each([
    ['disabled account', { disabledAt: '2026-07-04T00:00:00Z' }],
    ['null password hash', { passwordHash: null }],
    [
      'legacy scrypt hash',
      {
        passwordHash:
          'scrypt$v1$N=131072,r=8,p=1,keylen=64,maxmem=268435456$salt$hash',
      },
    ],
    ['malformed hash', { passwordHash: 'not-a-password-hash' }],
    ['MFA-required account', { mfaRequired: true }],
  ] satisfies Array<[string, Partial<LoginAccount>]>)(
    'fails closed with a generic result for %s',
    async (_label, overrides) => {
      const password = 'correct horse battery staple'
      authHarness.verifyPasswordForAccount.mockResolvedValue(
        !('passwordHash' in overrides)
      )
      authHarness.findAccount.mockResolvedValue(
        validAccount({
          passwordHash: TEST_ARGON2_HASH,
          ...overrides,
        })
      )
      await import('@/auth')

      const result = await capturedConfig().providers[0].authorize({
          identifier: 'admin@example.test',
          password,
        })
      if ('mfaRequired' in overrides && overrides.mfaRequired) {
        expect(result).toMatchObject({ auth_level: 'password', auth_method: 'password' })
        expect(authHarness.beginMfaChallenge).toHaveBeenCalled()
      } else {
        expect(result).toBeNull()
        expect(authHarness.writeLoginAudit).toHaveBeenCalledWith(
          expect.objectContaining({
            event: 'auth.login_failed',
            reasonCode: 'INVALID_CREDENTIALS',
          })
        )
      }
    }
  )

  it('fails safely when account storage is unavailable', async () => {
    authHarness.findAccount.mockRejectedValue(
      new Error('raw database URL and service-role secret')
    )
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password: 'password',
      })
    ).rejects.toThrow('Authentication account store unavailable')
    expect(authHarness.writeLoginAudit).toHaveBeenCalledWith({
      event: 'auth.account_lookup_failed',
      level: 'error',
      outcome: 'failure',
      identifierHash: expect.any(String),
      reasonCode: 'ACCOUNT_LOOKUP_FAILED',
    })
    expect(JSON.stringify(authHarness.writeLoginAudit.mock.calls)).not.toContain(
      'service-role secret'
    )
  })

  it('ignores AUTH_USERS_JSON and does not fall back when the DB has no account', async () => {
    const legacyPassword = 'legacy password'
    process.env.AUTH_USERS_JSON = JSON.stringify([
      {
        id: 'legacy-admin',
        email: 'admin@example.test',
        name: 'Legacy Admin',
        role: 'ADMIN',
        authz_version: 1,
        password_hash: TEST_ARGON2_HASH,
      },
    ])
    authHarness.verifyPasswordForAccount.mockImplementation(
      async (candidatePassword, candidateHash) =>
        candidatePassword === legacyPassword &&
        candidateHash === TEST_ARGON2_HASH
    )
    authHarness.findAccount.mockResolvedValue(undefined)
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password: legacyPassword,
      })
    ).resolves.toBeNull()
    expect(authHarness.findAccount).toHaveBeenCalledOnce()
    expect(authHarness.verifyPasswordForAccount).toHaveBeenCalledWith(
      legacyPassword,
      null
    )
  })

  it('does not require AUTH_USERS_JSON when a valid DB account exists', async () => {
    const password = 'database password'
    authHarness.verifyPasswordForAccount.mockResolvedValue(true)
    authHarness.findAccount.mockResolvedValue(
      validAccount({ passwordHash: TEST_ARGON2_HASH })
    )
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password,
      })
    ).resolves.toMatchObject({
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      role: 'ADMIN',
    })
  })

  it('consumes a one-time MFA completion token into final MFA claims', async () => {
    authHarness.consumeMfaCompletion.mockResolvedValue({
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      role: 'ADMIN',
      authz_version: 4,
      auth_level: 'mfa',
      auth_method: 'totp',
      verified_at: '2026-07-11T02:00:00.000Z',
    })
    await import('@/auth')
    const user = await capturedConfig().providers[0].authorize({
      mfa_completion_token: 'a'.repeat(43),
    })
    expect(user).toMatchObject({
      auth_level: 'mfa',
      auth_method: 'totp',
      auth_time: Math.floor(Date.parse('2026-07-11T02:00:00.000Z') / 1_000),
    })
    expect(authHarness.consumeMfaCompletion).toHaveBeenCalledWith('a'.repeat(43))
  })

  it('consumes a recovery completion token into restricted recovery claims', async () => {
    authHarness.consumeRecoveryCompletion.mockResolvedValue({
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      name: 'SOC Analyst',
      email: 'analyst@example.test',
      role: 'ANALYST',
      authz_version: 5,
      auth_level: 'recovery',
      auth_method: 'backup_code',
      verified_at: '2026-07-11T02:00:00.000Z',
      completion_purpose: 'mfa_recovery',
    })
    await import('@/auth')
    const user = await capturedConfig().providers[0].authorize({
      recovery_completion_token: 'c'.repeat(43),
    })
    expect(user).toMatchObject({ auth_level: 'recovery', auth_method: 'backup_code' })
  })

  it('keeps audit payload inputs free of passwords and hashes', async () => {
    const password = 'must-never-be-logged'
    const passwordHash = TEST_ARGON2_HASH
    authHarness.verifyPasswordForAccount.mockResolvedValue(true)
    authHarness.findAccount.mockResolvedValue(
      validAccount({ passwordHash, mfaRequired: true })
    )
    await import('@/auth')

    await capturedConfig().providers[0].authorize({
      identifier: 'admin@example.test',
      password,
    })

    const serializedAudit = JSON.stringify(
      authHarness.writeLoginAudit.mock.calls
    )
    expect(serializedAudit).not.toContain(password)
    expect(serializedAudit).not.toContain(passwordHash)
    expect(serializedAudit).not.toContain('passwordHash')
  })

  it('preserves identifier throttling before DB lookup', async () => {
    process.env.AUTH_LOGIN_MAX_FAILURES_PER_IDENTIFIER = '2'
    authHarness.findAccount.mockResolvedValue(undefined)
    await import('@/auth')
    const authorize = capturedConfig().providers[0].authorize
    const credentials = {
      identifier: 'throttled@example.test',
      password: 'not-the-password',
    }

    await authorize(credentials)
    await authorize(credentials)
    authHarness.writeLoginAudit.mockClear()
    await expect(authorize(credentials)).resolves.toBeNull()

    expect(authHarness.findAccount).toHaveBeenCalledTimes(2)
    expect(authHarness.writeLoginAudit).toHaveBeenCalledWith(
      expect.objectContaining({
        event: 'auth.login_throttled',
        reasonCode: 'IDENTIFIER_THROTTLED',
      })
    )
  })
})
