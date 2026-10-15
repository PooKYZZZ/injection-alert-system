import { describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import { AccountManagementError } from './account-management'
import {
  accountErrorResponse,
  recoveryErrorResponse,
  requireTrustedOrigin,
  totpErrorResponse,
} from './account-route-response'

describe('account route error responses', () => {
  it('maps fixed local validation errors to safe client failures', async () => {
    const recovery = recoveryErrorResponse(new Error('INVALID_CODE'))
    const totp = totpErrorResponse(new Error('INVALID_REQUEST'))

    expect(recovery.status).toBe(400)
    expect(await recovery.json()).toEqual({
      error: {
        code: 'RECOVERY_UNAVAILABLE',
        message: 'That recovery code is invalid or expired.',
      },
    })
    expect(totp.status).toBe(400)
  })

  it('preserves terminal TOTP challenge states for the client', async () => {
    const expired = Object.assign(new Error('EXPIRED'), { code: 'EXPIRED' })
    const locked = Object.assign(new Error('LOCKED'), { code: 'LOCKED' })
    const invalid = Object.assign(new Error('INVALID_CODE'), { code: 'INVALID_CODE' })

    expect(await totpErrorResponse(expired).json()).toEqual({
      error: {
        code: 'MFA_CHALLENGE_EXPIRED',
        message: 'This sign-in challenge has expired. Start sign-in again.',
      },
    })
    expect(await totpErrorResponse(locked).json()).toEqual({
      error: {
        code: 'MFA_CHALLENGE_LOCKED',
        message: 'This sign-in challenge has reached its attempt limit. Start sign-in again.',
      },
    })
    expect(await totpErrorResponse(invalid).json()).toEqual({
      error: {
        code: 'INVALID_CODE',
        message: 'That authenticator code is invalid. Try again.',
      },
    })
  })

  it('returns a stable conflict response for the last-enabled-Owner guard', async () => {
    const response = accountErrorResponse(
      new AccountManagementError('LAST_ENABLED_OWNER')
    )

    expect(response.status).toBe(409)
    expect(await response.json()).toEqual({
      error: {
        code: 'LAST_ENABLED_OWNER',
        message: 'At least one enabled Owner must remain.',
      },
    })
  })

  it('returns a distinct safe response for a rejected request origin', async () => {
    process.env.AUTH_APP_ORIGIN = 'http://localhost'
    const response = requireTrustedOrigin(
      new Request('http://localhost/api/admin/users', {
        headers: { origin: 'https://attacker.example' },
      })
    )

    expect(response).not.toBeNull()
    await expect(response?.json()).resolves.toEqual({
      error: {
        code: 'TRUSTED_ORIGIN_REJECTED',
        message: 'The request could not be verified. Reload the page and try again.',
      },
    })
  })
})
