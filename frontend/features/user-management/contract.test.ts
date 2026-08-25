import { describe, expect, it } from 'vitest'

import {
  createAccountSchema,
  managedEmailSchema,
  managedAccountsResponseSchema,
  mfaRequiredForRole,
} from './contract'

const safeAccount = {
  id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
  display_name: 'SOC Analyst',
  email: 'analyst@example.test',
  pending_email: null,
  role: 'ANALYST',
  enabled: true,
  email_verified: true,
  mfa_status: 'active',
  created_at: '2026-08-01T00:00:00Z',
}

describe('user management contract', () => {
  it('normalizes email without provider-specific rewriting', () => {
    const parsed = createAccountSchema.parse({
      email: ' First.Last+SOC@Gmail.com ',
      display_name: '  SOC Analyst  ',
      role: 'ANALYST',
    })

    expect(parsed).toEqual({
      email: 'first.last+soc@gmail.com',
      display_name: 'SOC Analyst',
      role: 'ANALYST',
    })
  })

  it('derives mandatory MFA only from the locked role policy', () => {
    expect(mfaRequiredForRole('ADMIN')).toBe(true)
    expect(mfaRequiredForRole('ANALYST')).toBe(true)
    expect(mfaRequiredForRole('VIEWER')).toBe(false)
  })

  it('rejects any ADMIN-supplied password field', () => {
    expect(
      createAccountSchema.safeParse({
        email: 'new@example.test',
        display_name: 'New User',
        role: 'VIEWER',
        password: 'admin-must-not-choose-this',
      }).success
    ).toBe(false)
  })

  it('validates managed email using the same normalization rule', () => {
    expect(managedEmailSchema.parse({ email: ' New@Example.Test ' })).toEqual({
      email: 'new@example.test',
    })
  })

  it('accepts the safe managed-account response contract', () => {
    expect(managedAccountsResponseSchema.parse({ accounts: [safeAccount] })).toEqual({
      accounts: [safeAccount],
    })
  })

  it('rejects malformed account records and unexpected sensitive fields', () => {
    expect(
      managedAccountsResponseSchema.safeParse({
        accounts: [{ ...safeAccount, created_at: 'not-a-timestamp' }],
      }).success
    ).toBe(false)
    expect(
      managedAccountsResponseSchema.safeParse({
        accounts: [{ ...safeAccount, password_hash: 'must-not-render' }],
      }).success
    ).toBe(false)
  })
})
