import { describe, expect, it } from 'vitest'

import {
  ARGON2_MEMORY_COST,
  ARGON2_PARALLELISM,
  ARGON2_TIME_COST,
  MAX_PASSWORD_LENGTH,
  hashPassword,
  verifyPasswordForAccount,
  verifyPasswordForUnknownAccount,
  verifyPasswordHash,
} from './password-hash'

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
  })

  it.each([
    '',
    'not-a-hash',
    '$argon2i$v=19$m=19456,t=2,p=1$c2FsdA$aGFzaA',
    'scrypt$v1$N=131072,r=8,p=1,keylen=64,maxmem=268435456$c2FsdA$aGFzaA',
  ])('fails safely for malformed or unsupported hash %s', async (hash) => {
    await expect(verifyPasswordHash(hash, 'password')).resolves.toBe(false)
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
