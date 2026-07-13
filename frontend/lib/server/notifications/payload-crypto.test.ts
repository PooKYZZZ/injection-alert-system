import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import {
  protectNotificationPayload,
  unprotectNotificationPayload,
} from './payload-crypto'

const context = {
  kind: 'password_reset',
  recipient: 'owner@example.test',
  idempotencyKey: 'password-reset/test-event',
}

describe('notification payload protection', () => {
  beforeEach(() => {
    process.env.NOTIFICATION_PAYLOAD_ENCRYPTION_KEY = Buffer.alloc(
      32,
      7
    ).toString('base64')
  })

  afterEach(() => {
    delete process.env.NOTIFICATION_PAYLOAD_ENCRYPTION_KEY
  })

  it('round-trips an authenticated envelope with a unique nonce', () => {
    const payload = { reset_url: 'https://example.test/reset?token=opaque' }
    const first = protectNotificationPayload(context, payload)
    const second = protectNotificationPayload(context, payload)

    expect(first).not.toEqual(second)
    expect(first).toEqual({
      ciphertext: expect.stringMatching(/^[A-Za-z0-9_-]+$/),
      nonce: expect.stringMatching(/^[A-Za-z0-9_-]+$/),
      key_version: 1,
    })
    expect(unprotectNotificationPayload(context, first)).toEqual(payload)
  })

  it('fails closed for tampering, wrong context, wrong key, and unknown version', () => {
    const envelope = protectNotificationPayload(context, { otp: '123456' })
    const tampered = {
      ...envelope,
      ciphertext: `${envelope.ciphertext.slice(0, -1)}${
        envelope.ciphertext.endsWith('A') ? 'B' : 'A'
      }`,
    }

    expect(() => unprotectNotificationPayload(context, tampered)).toThrow(
      'Notification payload is unavailable.'
    )
    expect(() =>
      unprotectNotificationPayload(
        { ...context, idempotencyKey: 'different' },
        envelope
      )
    ).toThrow('Notification payload is unavailable.')
    process.env.NOTIFICATION_PAYLOAD_ENCRYPTION_KEY = Buffer.alloc(
      32,
      8
    ).toString('base64')
    expect(() => unprotectNotificationPayload(context, envelope)).toThrow(
      'Notification payload is unavailable.'
    )
    expect(() =>
      unprotectNotificationPayload(context, {
        ...envelope,
        key_version: 99,
      })
    ).toThrow('Notification payload is unavailable.')
  })

  it('fails safely when the dedicated key is missing', () => {
    delete process.env.NOTIFICATION_PAYLOAD_ENCRYPTION_KEY

    expect(() =>
      protectNotificationPayload(context, { otp: '123456' })
    ).toThrow('Notification payload is unavailable.')
  })

  it('rejects a non-canonical base64 key instead of decoding it permissively', () => {
    process.env.NOTIFICATION_PAYLOAD_ENCRYPTION_KEY = `${Buffer.alloc(
      32,
      7
    ).toString('base64')}!`

    expect(() =>
      protectNotificationPayload(context, { otp: '123456' })
    ).toThrow('Notification payload is unavailable.')
  })

  it('matches the backend AES-GCM interoperability vector', () => {
    expect(
      unprotectNotificationPayload(
        { ...context, idempotencyKey: 'password-reset/interoperability' },
        {
          nonce: 'AAECAwQFBgcICQoL',
          ciphertext:
            'Y6ObFW5srRYCwIm-2HoEjpVMxbQ3TRJJd6MT1uv5GWCtG2mQ8rxUicuRrN05mYhamkQ5C7ulgeQQLdjpgr3cAZPJ6BuUnuHpQ4VXEwYD',
          key_version: 1,
        }
      )
    ).toEqual({
      reset_url: 'https://example.test/reset?token=interoperable',
    })
  })
})
