import { randomBytes } from 'node:crypto'

import { describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

import { decryptTotpSecret } from '@/lib/auth/mfa-crypto'
import {
  backupCodeLookupPrefix,
  encodeBase32,
  encryptTotpSecretForSeed,
  generateBackupCode,
  generateTestPassword,
  generateTotpSecret,
} from './seed-material'

describe('authentication E2E seed material', () => {
  it('encodes and generates RFC-compatible Base32 secrets', () => {
    expect(encodeBase32(Buffer.from('foo', 'utf8'))).toBe('MZXW6')
    expect(generateTotpSecret(() => Buffer.alloc(20, 7))).toMatch(/^[A-Z2-7]{32}$/)
  })

  it('creates factor ciphertext that the production decryptor accepts', () => {
    const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
    const factorId = '8b8bb9de-1dff-44b7-9a44-12efe8a6716f'
    const key = randomBytes(32).toString('base64')
    process.env.AUTH_MFA_ENCRYPTION_KEY = key
    const secret = generateTotpSecret()

    const first = encryptTotpSecretForSeed(secret, accountId, factorId, key)
    const second = encryptTotpSecretForSeed(secret, accountId, factorId, key)

    expect(first).not.toEqual(second)
    expect(decryptTotpSecret(first, accountId, factorId)).toBe(secret)
    expect(decryptTotpSecret(second, accountId, factorId)).toBe(secret)
  })

  it('generates non-static passwords and correctly shaped backup codes', () => {
    expect(generateTestPassword()).not.toBe(generateTestPassword())
    expect(generateTestPassword()).toHaveLength(36)

    const code = generateBackupCode()
    expect(code).toMatch(/^[2-9A-HJ-NP-Z]{4}(?:-[2-9A-HJ-NP-Z]{4}){2}$/)
    expect(backupCodeLookupPrefix(code)).toBe(code.replaceAll('-', '').slice(0, 4))
  })
})
