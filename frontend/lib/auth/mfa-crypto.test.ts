import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import {
  decryptTotpSecret,
  encryptTotpSecret,
} from './mfa-crypto'

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
const factorId = '2c0d7d68-e70d-4f22-9487-57b3df572b6c'

describe('TOTP secret encryption', () => {
  beforeEach(() => {
    process.env.AUTH_MFA_ENCRYPTION_KEY = Buffer.alloc(32, 7).toString('base64')
  })

  it('round-trips with AES-GCM and unique nonces', () => {
    const first = encryptTotpSecret('JBSWY3DPEHPK3PXP', accountId, factorId)
    const second = encryptTotpSecret('JBSWY3DPEHPK3PXP', accountId, factorId)

    expect(first.nonce).not.toBe(second.nonce)
    expect(first.ciphertext).not.toContain('JBSWY3DPEHPK3PXP')
    expect(decryptTotpSecret(first, accountId, factorId)).toBe('JBSWY3DPEHPK3PXP')
  })

  it('fails closed when associated data or the key is wrong', () => {
    const encrypted = encryptTotpSecret('JBSWY3DPEHPK3PXP', accountId, factorId)
    expect(() => decryptTotpSecret(encrypted, accountId, 'different-factor')).toThrow()
    process.env.AUTH_MFA_ENCRYPTION_KEY = Buffer.alloc(32, 8).toString('base64')
    expect(() => decryptTotpSecret(encrypted, accountId, factorId)).toThrow()
  })
})
