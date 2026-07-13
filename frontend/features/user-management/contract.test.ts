import { describe, expect, it } from 'vitest'

import {
  createAccountSchema,
  managedEmailSchema,
  mfaRequiredForRole,
} from './contract'

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
})
