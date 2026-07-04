import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const TEST_ARGON2_HASH =
  '$argon2id$v=19$m=19456,t=2,p=1$mockSalt$mockHash'

type LoginAccount = {
  id: string
  email: string
  username: string | null
  name: string
  role: 'ADMIN' | 'ANALYST' | 'VIEWER'
  authzVersion: number
  passwordHash: string | null
  mfaRequired: boolean
  disabledAt: string | null
}

type CapturedConfig = {
  providers: Array<{
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
}))

vi.mock('next-auth', () => ({
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

vi.mock('./login-audit', () => ({
  writeLoginAudit: authHarness.writeLoginAudit,
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
})

beforeEach(() => {
  authHarness.config = null
  authHarness.findAccount.mockReset()
  authHarness.verifyPasswordForAccount.mockReset()
  authHarness.verifyPasswordForAccount.mockResolvedValue(false)
  authHarness.writeLoginAudit.mockReset()
  process.env.AUTH_SECRET = 'test-auth-secret'
  delete process.env.AUTH_USERS_JSON
})

describe('Auth.js credential login', () => {
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
    expect(user).toEqual({
      id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
      email: 'admin@example.test',
      name: 'SOC Admin',
      role: 'ADMIN',
      authz_version: 3,
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

      await expect(
        capturedConfig().providers[0].authorize({
          identifier: 'admin@example.test',
          password,
        })
      ).resolves.toBeNull()
      expect(authHarness.writeLoginAudit).toHaveBeenCalledWith(
        expect.objectContaining({
          event: 'auth.login_failed',
          reasonCode: 'INVALID_CREDENTIALS',
        })
      )
    }
  )

  it('fails closed on account query or client configuration failure', async () => {
    authHarness.findAccount.mockRejectedValue(
      new Error('raw database URL and service-role secret')
    )
    await import('@/auth')

    await expect(
      capturedConfig().providers[0].authorize({
        identifier: 'admin@example.test',
        password: 'password',
      })
    ).resolves.toBeNull()
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
