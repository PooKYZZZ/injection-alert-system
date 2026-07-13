import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import { protectNotificationPayload } from '@/lib/server/notifications/payload-crypto'
import { readEmailRecoveryOtp, safeDatabaseErrorCode } from './database'

describe('authentication E2E database diagnostics', () => {
  beforeEach(() => {
    process.env.NOTIFICATION_PAYLOAD_ENCRYPTION_KEY = Buffer.alloc(
      32,
      9
    ).toString('base64')
  })

  afterEach(() => {
    delete process.env.NOTIFICATION_PAYLOAD_ENCRYPTION_KEY
  })

  it('retains only a bounded database error code', () => {
    expect(safeDatabaseErrorCode({ code: '42501', details: 'secret row' })).toBe(
      '42501'
    )
    expect(safeDatabaseErrorCode({ code: 'not safe!' })).toBe('UNKNOWN')
    expect(safeDatabaseErrorCode({ details: 'secret row' })).toBe('UNKNOWN')
  })

  it('reads an OTP only by decrypting its bound outbox envelope', () => {
    const email = 'recovery@example.test'
    const idempotencyKey = 'email-recovery/test'
    const payload = protectNotificationPayload(
      {
        kind: 'email_recovery_otp',
        recipient: email,
        idempotencyKey,
      },
      { otp: '123456' }
    )

    expect(readEmailRecoveryOtp(email, {
      payload_safe_json: payload,
      provider_idempotency_key: idempotencyKey,
    })).toBe('123456')
    expect(JSON.stringify(payload)).not.toContain('123456')
    expect(() =>
      readEmailRecoveryOtp('other@example.test', {
        payload_safe_json: payload,
        provider_idempotency_key: idempotencyKey,
      })
    ).toThrow('Authentication E2E database is unavailable.')
  })
})
