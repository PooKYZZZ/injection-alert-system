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
})
