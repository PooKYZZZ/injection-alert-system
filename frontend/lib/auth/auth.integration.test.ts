import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { hashPassword } from './password-hash'

const authHarness = vi.hoisted(() => ({
  config: null as
    | {
        providers: Array<{
          authorize: (
            credentials: Record<string, unknown>
          ) => Promise<Record<string, unknown> | null>
        }>
      }
    | null,
  argon2Verify: vi.fn(),
}))

vi.mock('next-auth', () => ({
  default: vi.fn((config: typeof authHarness.config) => {
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

vi.mock('argon2', async (importOriginal) => {
  const actual = await importOriginal<typeof import('argon2')>()
  authHarness.argon2Verify.mockImplementation((...args: Array<unknown>) =>
    actual.verify(...(args as Parameters<typeof actual.verify>))
  )
  return {
    ...actual,
    verify: authHarness.argon2Verify,
  }
})

vi.mock('./login-audit', () => ({
  writeLoginAudit: vi.fn(),
}))

function capturedAuthorize() {
  if (!authHarness.config) {
    throw new Error('Auth.js configuration was not captured')
  }
  return authHarness.config.providers[0].authorize
}

const originalAuthSecret = process.env.AUTH_SECRET
const originalRegistry = process.env.AUTH_USERS_JSON

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
})

beforeEach(() => {
  authHarness.config = null
  authHarness.argon2Verify.mockClear()
  process.env.AUTH_SECRET = 'test-auth-secret'
})

describe('Auth.js credential login', () => {
  it('accepts an AUTH_USERS_JSON account with an Argon2id hash and rejects wrong or legacy hashes safely', async () => {
    const password = 'correct horse battery staple'
    const hash = await hashPassword(password)
    process.env.AUTH_USERS_JSON = JSON.stringify([
      {
        id: 'admin-1',
        email: 'admin@example.test',
        name: 'SOC Admin',
        role: 'ADMIN',
        authz_version: 1,
        password_hash: hash,
      },
    ])

    await import('@/auth')

    const authorize = capturedAuthorize()
    await expect(
      authorize({
        identifier: 'admin@example.test',
        password,
      })
    ).resolves.toMatchObject({
      id: 'admin-1',
      email: 'admin@example.test',
      role: 'ADMIN',
      authz_version: 1,
    })

    await expect(
      authorize({
        identifier: 'admin@example.test',
        password: 'wrong password',
      })
    ).resolves.toBeNull()

    process.env.AUTH_USERS_JSON = JSON.stringify([
      {
        id: 'admin-1',
        email: 'admin@example.test',
        name: 'SOC Admin',
        role: 'ADMIN',
        authz_version: 1,
        password_hash:
          'scrypt$v1$N=131072,r=8,p=1,keylen=64,maxmem=268435456$c2FsdA$aGFzaA',
      },
    ])
    vi.resetModules()
    authHarness.config = null
    await import('@/auth')

    await expect(
      capturedAuthorize()({
        identifier: 'admin@example.test',
        password,
      })
    ).resolves.toBeNull()
  })

  it('runs the Argon2id dummy verification path for unknown accounts', async () => {
    process.env.AUTH_USERS_JSON = JSON.stringify([
      {
        id: 'admin-1',
        email: 'admin@example.test',
        name: 'SOC Admin',
        role: 'ADMIN',
        authz_version: 1,
        password_hash: await hashPassword('correct horse battery staple'),
      },
    ])

    await import('@/auth')

    await expect(
      capturedAuthorize()({
        identifier: 'unknown@example.test',
        password: 'not-the-password',
      })
    ).resolves.toBeNull()
    expect(authHarness.argon2Verify).toHaveBeenCalled()
  })
})
