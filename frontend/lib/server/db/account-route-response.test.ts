import { describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import { recoveryErrorResponse, totpErrorResponse } from './account-route-response'

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
})
