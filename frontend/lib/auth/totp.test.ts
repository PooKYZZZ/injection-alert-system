import { describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import {
  buildTotpProvisioningUri,
  generateTotpSecret,
  verifyTotpCode,
} from './totp'

describe('RFC 6238 TOTP', () => {
  it('generates a compatible secret and provisioning URI', () => {
    const secret = generateTotpSecret()
    expect(secret).toMatch(/^[A-Z2-7]+$/)
    const uri = buildTotpProvisioningUri('analyst@example.test', secret)
    expect(uri).toContain('otpauth://totp/')
    expect(uri).toContain('issuer=CyberTrace')
    expect(uri).toContain(`secret=${secret}`)
    expect(uri).toContain('algorithm=SHA1')
    expect(uri).toContain('digits=6')
    expect(uri).toContain('period=30')
  })

  it('accepts only the previous/current/next 30-second step', () => {
    const secret = 'JBSWY3DPEHPK3PXP'
    const now = 1_700_000_015_000
    expect(verifyTotpCode(secret, '000000', now).valid).toBe(false)
    expect(verifyTotpCode('GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ', '287082', 59_000)).toEqual({
      valid: true,
      timeStep: 1,
    })
  })

  it('rejects malformed codes', () => {
    expect(verifyTotpCode('JBSWY3DPEHPK3PXP', '12-3456', 1_700_000_000_000).valid).toBe(false)
  })
})
