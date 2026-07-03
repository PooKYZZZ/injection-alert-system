import * as crypto from 'node:crypto'

import { describe, expect, it, vi } from 'vitest'

vi.mock('node:crypto', async (importOriginal) => {
  const actual = await importOriginal<typeof import('node:crypto')>()
  return {
    ...actual,
    scrypt: vi.fn(actual.scrypt),
  }
})

import {
  DUMMY_PASSWORD_HASH,
  MAX_PASSWORD_LENGTH,
  SCRYPT_CONCURRENCY_LIMIT,
  SCRYPT_KEYLEN,
  SCRYPT_MAXMEM,
  SCRYPT_N,
  SCRYPT_P,
  SCRYPT_R,
  SCRYPT_SALT_BYTES,
  hashPassword,
  verifyPasswordForAccount,
  verifyPasswordHash,
} from './password-hash'

describe('password hashing', () => {
  it('uses the required scrypt constants', () => {
    expect({
      N: SCRYPT_N,
      r: SCRYPT_R,
      p: SCRYPT_P,
      keylen: SCRYPT_KEYLEN,
      saltBytes: SCRYPT_SALT_BYTES,
      maxmem: SCRYPT_MAXMEM,
      concurrencyLimit: SCRYPT_CONCURRENCY_LIMIT,
    }).toEqual({
      N: 131_072,
      r: 8,
      p: 1,
      keylen: 64,
      saltBytes: 32,
      maxmem: 268_435_456,
      concurrencyLimit: 2,
    })
  })

  it('generates a hash that verifies only the correct password', async () => {
    const encoded = await hashPassword('correct horse battery staple')

    await expect(
      verifyPasswordHash('correct horse battery staple', encoded)
    ).resolves.toBe(true)
    await expect(verifyPasswordHash('wrong password', encoded)).resolves.toBe(
      false
    )
  })

  it.each([
    'not-a-hash',
    'scrypt$v2$N=131072,r=8,p=1,keylen=64,maxmem=268435456$c2FsdA$aGFzaA',
    'scrypt$v1$N=131072,r=8,p=1,keylen=64$c2FsdA$aGFzaA',
    'scrypt$v1$N=x,r=8,p=1,keylen=64,maxmem=268435456$c2FsdA$aGFzaA',
    'scrypt$v1$N=-1,r=8,p=1,keylen=64,maxmem=268435456$c2FsdA$aGFzaA',
    'scrypt$v1$N=0,r=8,p=1,keylen=64,maxmem=268435456$c2FsdA$aGFzaA',
    'scrypt$v1$N=65536,r=8,p=2,keylen=64,maxmem=268435456$c2FsdA$aGFzaA',
    'scrypt$v1$N=131072,r=8,p=1,keylen=32,maxmem=268435456$c2FsdA$aGFzaA',
    'scrypt$v1$N=131072,r=8,p=1,keylen=64,maxmem=134217728$c2FsdA$aGFzaA',
    'scrypt$v1$N=131072,r=8,p=1,keylen=64,maxmem=268435456$c2FsdA$c2hvcnQ',
  ])('fails safely for malformed or unsupported hash %s', async (encoded) => {
    await expect(verifyPasswordHash('password', encoded)).resolves.toBe(false)
  })

  it('uses the exact real-hash profile for the dummy hash', () => {
    expect(DUMMY_PASSWORD_HASH).toMatch(
      /^scrypt\$v1\$N=131072,r=8,p=1,keylen=64,maxmem=268435456\$/
    )
    const dummySalt = DUMMY_PASSWORD_HASH.split('$')[3]
    expect(Buffer.from(dummySalt, 'base64url')).toHaveLength(SCRYPT_SALT_BYTES)
  })

  it('runs scrypt for an unknown account before returning generic failure', async () => {
    const scryptSpy = vi.mocked(crypto.scrypt)
    scryptSpy.mockClear()

    await expect(
      verifyPasswordForAccount('unknown account password', null)
    ).resolves.toBe(false)

    expect(scryptSpy).toHaveBeenCalledTimes(1)
  })

  it('rejects overlong passwords without leaking the plaintext', async () => {
    const password = `sensitive-${'x'.repeat(MAX_PASSWORD_LENGTH)}`
    const encoded = await hashPassword('valid password')

    await expect(verifyPasswordHash(password, encoded)).resolves.toBe(false)
    await expect(hashPassword(password)).rejects.not.toThrow(password)
  })
})
