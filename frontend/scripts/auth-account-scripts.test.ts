import { beforeEach, describe, expect, it, vi } from 'vitest'

const MOCK_ARGON2_HASH =
  '$argon2id$v=19$m=19456,t=2,p=1$mockSalt$mockHash'

const argon2Harness = vi.hoisted(() => ({
  hash: vi.fn(),
}))

/**
 * This test validates provisioning-script control flow, not native Argon2.
 * Real Argon2id hash/verify coverage lives in password-hash.test.ts.
 * Keep this mock pure. Do not use importOriginal()/vi.importActual(),
 * because that loads the native argon2 addon in Vitest workers.
 */
vi.mock('argon2', () => ({
  default: {
    argon2id: 2,
    hash: argon2Harness.hash,
  },
}))

import {
  buildCreateAccountPayload,
} from './create_auth_account.mjs'
import { buildDisableUpdate } from './disable_auth_account.mjs'
import { SAFE_ACCOUNT_FIELDS } from './list_auth_accounts.mjs'
import { buildPasswordUpdate } from './set_auth_account_password.mjs'

describe('auth account provisioning scripts', () => {
  beforeEach(() => {
    argon2Harness.hash.mockReset()
    argon2Harness.hash.mockResolvedValue(MOCK_ARGON2_HASH)
  })

  it('rejects an unsupported account role', async () => {
    await expect(
      buildCreateAccountPayload({
        email: 'user@example.test',
        name: 'User',
        role: 'OWNER',
      })
    ).rejects.toThrow('Role must be ADMIN, ANALYST, or VIEWER.')
  })

  it('normalizes account data and requests approved Argon2id hashing', async () => {
    const plaintext = 'temporary-password'
    const payload = await buildCreateAccountPayload({
      email: ' User@Example.Test ',
      username: ' SOC-Analyst ',
      name: 'User',
      role: 'ANALYST',
      password: plaintext,
    })

    expect(payload).toMatchObject({
      email: 'user@example.test',
      username: 'soc-analyst',
      role: 'ANALYST',
      authz_version: 1,
      mfa_required: true,
    })
    expect(payload.password_hash).toBe(MOCK_ARGON2_HASH)
    expect(payload.password_hash).not.toContain(plaintext)
    expect(payload.password_set_at).not.toBeNull()
    expect(argon2Harness.hash).toHaveBeenCalledWith(plaintext, {
      type: 2,
      memoryCost: 19_456,
      timeCost: 2,
      parallelism: 1,
    })
  })

  it('rejects provisioning passwords shorter than six characters', async () => {
    await expect(
      buildCreateAccountPayload({
        email: 'user@example.test',
        name: 'User',
        role: 'ADMIN',
        password: 'short',
      })
    ).rejects.toThrow('Password must contain 6 to 256 characters.')

    await expect(
      buildPasswordUpdate('short', 7)
    ).rejects.toThrow('Password must contain 6 to 256 characters.')
  })

  it('defaults viewer MFA off and supports schema-backed setup-pending mode', async () => {
    const payload = await buildCreateAccountPayload({
      email: 'viewer@example.test',
      name: 'Viewer',
      role: 'VIEWER',
    })

    expect(payload).toMatchObject({
      mfa_required: false,
      password_hash: null,
      password_set_at: null,
    })
  })

  it('lists only explicitly safe account metadata', () => {
    expect(SAFE_ACCOUNT_FIELDS).not.toContain('password_hash')
    expect(SAFE_ACCOUNT_FIELDS).not.toMatch(/token|otp|backup|totp|secret/i)
  })

  it('sets password hash and timestamp together while incrementing authz_version', async () => {
    const update = await buildPasswordUpdate('replacement-password', 7)

    expect(update.password_hash).toBe(MOCK_ARGON2_HASH)
    expect(update.password_set_at).toBeTruthy()
    expect(update.authz_version).toBe(8)
    expect(argon2Harness.hash).toHaveBeenCalledWith('replacement-password', {
      type: 2,
      memoryCost: 19_456,
      timeCost: 2,
      parallelism: 1,
    })
  })

  it('disables without deletion and increments authz_version', () => {
    expect(buildDisableUpdate(4)).toMatchObject({
      disabled_at: expect.any(String),
      authz_version: 5,
    })
  })
})
