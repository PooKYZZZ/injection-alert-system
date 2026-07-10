import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import { digestEmailOtp, generateEmailOtp } from './email-otp'

describe('email recovery OTP boundary', () => {
  beforeEach(() => {
    process.env.AUTH_EMAIL_OTP_KEY = 'test-email-otp-key-with-at-least-32-bytes'
  })

  it('generates six decimal digits and a domain-separated keyed digest', () => {
    const otp = generateEmailOtp()
    expect(otp).toMatch(/^\d{6}$/)
    expect(digestEmailOtp(otp)).toMatch(/^[a-f0-9]{64}$/)
    expect(digestEmailOtp(otp)).toBe(digestEmailOtp(otp))
    expect(digestEmailOtp(otp)).not.toBe(digestEmailOtp('000000'))
  })

  it('rejects malformed codes', () => {
    expect(() => digestEmailOtp('12345')).toThrow()
  })
})
