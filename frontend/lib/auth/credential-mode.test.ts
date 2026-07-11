import { describe, expect, it } from 'vitest'

import { parseCredentialMode } from './credential-mode'

describe('Auth.js credential modes', () => {
  it('accepts a complete password-login mode', () => {
    expect(
      parseCredentialMode({
        identifier: 'admin@example.test',
        password: 'correct horse battery staple',
      })
    ).toEqual({
      kind: 'password',
      identifier: 'admin@example.test',
      password: 'correct horse battery staple',
    })
  })

  it('accepts each one-time completion mode in isolation', () => {
    expect(
      parseCredentialMode({ mfa_completion_token: 'a'.repeat(43) })
    ).toEqual({ kind: 'mfa_completion', token: 'a'.repeat(43) })
    expect(
      parseCredentialMode({ recovery_completion_token: 'b'.repeat(43) })
    ).toEqual({ kind: 'recovery_completion', token: 'b'.repeat(43) })
  })

  it.each([
    undefined,
    {},
    { identifier: 'admin@example.test' },
    { password: 'password-only' },
    { mfa_completion_token: 123 },
    { recovery_completion_token: '' },
    {
      identifier: 'admin@example.test',
      password: 'password',
      mfa_completion_token: 'a'.repeat(43),
    },
    {
      mfa_completion_token: 'a'.repeat(43),
      recovery_completion_token: 'b'.repeat(43),
    },
  ])('rejects malformed or mixed credential input %#', (credentials) => {
    expect(parseCredentialMode(credentials)).toBeNull()
  })
})
