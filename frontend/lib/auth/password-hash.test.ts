import { describe, expect, it } from 'vitest'
import * as argon2 from 'argon2'

import {
  ARGON2_MEMORY_COST,
  ARGON2_PARALLELISM,
  ARGON2_TIME_COST,
  DUMMY_PASSWORD_HASH,
  MAX_PASSWORD_LENGTH,
  hasApprovedArgon2Parameters,
  hashPassword,
  verifyPasswordForAccount,
  verifyPasswordForUnknownAccount,
  verifyPasswordHash,
  validateNewPassword,
} from './password-hash'

describe('new password policy', () => {
  it('requires 6 characters, allows spaces, and never truncates', () => {
    expect(validateNewPassword('short')).toEqual({
      ok: false,
      code: 'PASSWORD_TOO_SHORT',
    })
    expect(validateNewPassword('abcdef')).toEqual({ ok: true })
    expect(validateNewPassword('a long pass phrase')).toEqual({ ok: true })
    expect(validateNewPassword('x'.repeat(257))).toEqual({
      ok: false,
      code: 'PASSWORD_TOO_LONG',
    })
  })
})

describe('password hashing', () => {
  it('uses the approved Argon2id parameters', () => {
    expect({
      memoryCost: ARGON2_MEMORY_COST,
      timeCost: ARGON2_TIME_COST,
      parallelism: ARGON2_PARALLELISM,
      maxPasswordLength: MAX_PASSWORD_LENGTH,
    }).toEqual({
      memoryCost: 19_456,
      timeCost: 2,
      parallelism: 1,
      maxPasswordLength: 256,
    })
  })

  it('generates an Argon2id PHC hash that verifies only the correct password', async () => {
    const hash = await hashPassword('correct horse battery staple')

    expect(hash).toMatch(/^\$argon2id\$/)
    await expect(
      verifyPasswordHash(hash, 'correct horse battery staple')
    ).resolves.toBe(true)
    await expect(verifyPasswordHash(hash, 'wrong password')).resolves.toBe(false)
    expect(hasApprovedArgon2Parameters(hash)).toBe(true)
  })

  it.each([
    '',
    'not-a-hash',
    '$argon2i$v=19$m=19456,t=2,p=1$c2FsdA$aGFzaA',
    '$argon2d$v=19$m=19456,t=2,p=1$c2FsdA$aGFzaA',
    '$argon2id$v=19$m=19456,t=2$c2FsdA$aGFzaA',
    '$argon2id$v=18$m=19456,t=2,p=1$c2FsdA$aGFzaA',
    'scrypt$v1$N=131072,r=8,p=1,keylen=64,maxmem=268435456$c2FsdA$aGFzaA',
    '$2b$12$abcdefghijklmnopqrstuuYwHqM8QQQqPXrJqrh8L2T4Q4aXEq1W',
    'plaintext-password',
  ])('fails safely for malformed or unsupported hash %s', async (hash) => {
    await expect(verifyPasswordHash(hash, 'password')).resolves.toBe(false)
  })

  it('rejects a valid but weak Argon2id PHC hash before verification', async () => {
    const weakHash = await argon2.hash('weak password', {
      type: argon2.argon2id,
      memoryCost: 4_096,
      timeCost: 1,
      parallelism: 1,
    })

    expect(weakHash).toMatch(/^\$argon2id\$/)
    expect(hasApprovedArgon2Parameters(weakHash)).toBe(false)
    await expect(
      verifyPasswordHash(weakHash, 'weak password')
    ).resolves.toBe(false)
  })

  it('uses a precomputed dummy hash with approved parameters', () => {
    expect(DUMMY_PASSWORD_HASH).toMatch(/^\$argon2id\$v=19\$/)
    expect(hasApprovedArgon2Parameters(DUMMY_PASSWORD_HASH)).toBe(true)
  })

  it('rejects empty and overlong passwords', async () => {
    const overlong = 'x'.repeat(MAX_PASSWORD_LENGTH + 1)
    const hash = await hashPassword('valid password')

    await expect(hashPassword('')).rejects.toThrow('Password input is invalid.')
    await expect(hashPassword(overlong)).rejects.toThrow(
      'Password input is invalid.'
    )
    await expect(verifyPasswordHash(hash, '')).resolves.toBe(false)
    await expect(verifyPasswordHash(hash, overlong)).resolves.toBe(false)
  })

  it('runs a real Argon2 verification for an unknown account', async () => {
    await expect(
      verifyPasswordForUnknownAccount('unknown account password')
    ).resolves.toBeUndefined()
  })

  it('returns false after dummy verification for an unknown account', async () => {
    await expect(
      verifyPasswordForAccount('unknown account password', null)
    ).resolves.toBe(false)
  })
})
