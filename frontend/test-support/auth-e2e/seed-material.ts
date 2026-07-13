import {
  createCipheriv,
  randomBytes,
  randomInt,
} from 'node:crypto'

import type { EncryptedTotpSecret } from '@/lib/auth/mfa-crypto'

const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
const BACKUP_ALPHABET = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ'
const AES_GCM_NONCE_BYTES = 12

export function encodeBase32(value: Buffer): string {
  if (value.length === 0) throw new Error('Base32 input is empty.')

  let output = ''
  let buffer = 0
  let bits = 0
  for (const byte of value) {
    buffer = (buffer << 8) | byte
    bits += 8
    while (bits >= 5) {
      bits -= 5
      output += BASE32_ALPHABET[(buffer >> bits) & 31]
    }
  }
  if (bits > 0) {
    output += BASE32_ALPHABET[(buffer << (5 - bits)) & 31]
  }
  return output
}

export function generateTotpSecret(
  randomSource: (size: number) => Buffer = randomBytes
): string {
  return encodeBase32(randomSource(20))
}

function decodeEncryptionKey(encodedKey: string): Buffer {
  const key = /^[0-9a-f]{64}$/i.test(encodedKey)
    ? Buffer.from(encodedKey, 'hex')
    : Buffer.from(encodedKey, 'base64')
  if (key.length !== 32) {
    throw new Error('Authentication E2E MFA key is invalid.')
  }
  return key
}

export function encryptTotpSecretForSeed(
  secret: string,
  accountId: string,
  factorId: string,
  encodedKey: string
): EncryptedTotpSecret {
  const nonce = randomBytes(AES_GCM_NONCE_BYTES)
  const cipher = createCipheriv(
    'aes-256-gcm',
    decodeEncryptionKey(encodedKey),
    nonce
  )
  cipher.setAAD(Buffer.from(`${accountId}:${factorId}:totp`, 'utf8'))
  const ciphertext = Buffer.concat([
    cipher.update(secret, 'utf8'),
    cipher.final(),
    cipher.getAuthTag(),
  ])
  return {
    ciphertext: ciphertext.toString('base64url'),
    nonce: nonce.toString('base64url'),
    key_version: 1,
  }
}

export function generateTestPassword(): string {
  return `${randomBytes(24).toString('base64url')}Aa1!`
}

export function generateBackupCode(): string {
  const characters = Array.from(
    { length: 12 },
    () => BACKUP_ALPHABET[randomInt(BACKUP_ALPHABET.length)]
  )
  return [
    characters.slice(0, 4).join(''),
    characters.slice(4, 8).join(''),
    characters.slice(8).join(''),
  ].join('-')
}

export function backupCodeLookupPrefix(code: string): string {
  return code.replaceAll('-', '').slice(0, 4)
}
