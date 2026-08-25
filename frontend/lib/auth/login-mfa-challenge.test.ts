import { describe, expect, it } from 'vitest'

import { canRenderLoginMfaPage } from './login-mfa-challenge'

const now = Date.parse('2026-08-25T04:00:00Z')

const passwordChallenge = {
  user: {
    auth_level: 'password',
    auth_method: 'password',
    mfa_challenge_purpose: 'login_mfa',
    mfa_challenge_expires_at: '2026-08-25T04:05:00Z',
  },
}

describe('login MFA page challenge boundary', () => {
  it('allows only an active password-level login challenge with a pre-auth handle', () => {
    expect(canRenderLoginMfaPage(passwordChallenge, 'opaque-handle', now)).toBe(true)
  })

  it.each([
    [{ ...passwordChallenge, user: { ...passwordChallenge.user, auth_level: 'mfa' } }, 'opaque-handle'],
    [{ ...passwordChallenge, user: { ...passwordChallenge.user, mfa_challenge_purpose: 'mfa_enrollment' } }, 'opaque-handle'],
    [{ ...passwordChallenge, user: { ...passwordChallenge.user, mfa_challenge_expires_at: '2026-08-25T03:59:00Z' } }, 'opaque-handle'],
    [passwordChallenge, null],
  ])('rejects an invalid page visit', (session, preAuthHandle) => {
    expect(canRenderLoginMfaPage(session, preAuthHandle, now)).toBe(false)
  })
})
