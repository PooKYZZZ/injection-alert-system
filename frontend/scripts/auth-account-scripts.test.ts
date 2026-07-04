import argon2 from 'argon2'
import { describe, expect, it } from 'vitest'

import {
  buildCreateAccountPayload,
} from './create_auth_account.mjs'
import { buildDisableUpdate } from './disable_auth_account.mjs'
import { SAFE_ACCOUNT_FIELDS } from './list_auth_accounts.mjs'
import { buildPasswordUpdate } from './set_auth_account_password.mjs'

describe('auth account provisioning scripts', () => {
  it('rejects an unsupported account role', async () => {
    await expect(
      buildCreateAccountPayload({
        email: 'user@example.test',
        name: 'User',
        role: 'OWNER',
      })
    ).rejects.toThrow('Role must be ADMIN, ANALYST, or VIEWER.')
  })

  it('normalizes account data and hashes a supplied password with Argon2id', async () => {
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
    expect(payload.password_hash).toMatch(/^\$argon2id\$/)
    expect(payload.password_hash).not.toContain(plaintext)
    expect(payload.password_set_at).not.toBeNull()
    await expect(argon2.verify(payload.password_hash!, plaintext)).resolves.toBe(
      true
    )
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

    expect(update.password_hash).toMatch(/^\$argon2id\$/)
    expect(update.password_set_at).toBeTruthy()
    expect(update.authz_version).toBe(8)
  })

  it('disables without deletion and increments authz_version', () => {
    expect(buildDisableUpdate(4)).toMatchObject({
      disabled_at: expect.any(String),
      authz_version: 5,
    })
  })
})
