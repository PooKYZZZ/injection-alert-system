import 'server-only'

import { createDecipheriv, createCipheriv, randomBytes } from 'node:crypto'

const ALGORITHM = 'aes-256-gcm'
const KEY_VERSION = 1
const NONCE_BYTES = 12

type EncryptedTotpSecret = {
  ciphertext: string
  nonce: string
  key_version: number
}

function encryptionKey(): Buffer {
  const raw = process.env.AUTH_MFA_ENCRYPTION_KEY?.trim()
  if (!raw) throw new Error('AUTH_MFA_ENCRYPTION_KEY is not configured.')
  const key = /^[0-9a-f]{64}$/i.test(raw)
    ? Buffer.from(raw, 'hex')
    : Buffer.from(raw, 'base64')
  if (key.length !== 32) throw new Error('AUTH_MFA_ENCRYPTION_KEY is invalid.')
  return key
}

function associatedData(accountId: string, factorId: string): Buffer {
  return Buffer.from(`${accountId}:${factorId}:totp`, 'utf8')
}

export function encryptTotpSecret(
  secret: string,
  accountId: string,
  factorId: string
): EncryptedTotpSecret {
  const nonce = randomBytes(NONCE_BYTES)
  const cipher = createCipheriv(ALGORITHM, encryptionKey(), nonce)
  cipher.setAAD(associatedData(accountId, factorId))
  const ciphertext = Buffer.concat([
    cipher.update(secret, 'utf8'),
    cipher.final(),
    cipher.getAuthTag(),
  ])
  return {
    ciphertext: ciphertext.toString('base64url'),
    nonce: nonce.toString('base64url'),
    key_version: KEY_VERSION,
  }
}

export function decryptTotpSecret(
  encrypted: EncryptedTotpSecret,
  accountId: string,
  factorId: string
): string {
  if (encrypted.key_version !== KEY_VERSION) {
    throw new Error('Unsupported TOTP key version.')
  }
  const nonce = Buffer.from(encrypted.nonce, 'base64url')
  const payload = Buffer.from(encrypted.ciphertext, 'base64url')
  if (nonce.length !== NONCE_BYTES || payload.length < 17) {
    throw new Error('Encrypted TOTP secret is invalid.')
  }
  const decipher = createDecipheriv(ALGORITHM, encryptionKey(), nonce)
  decipher.setAAD(associatedData(accountId, factorId))
  decipher.setAuthTag(payload.subarray(-16))
  const plaintext = Buffer.concat([
    decipher.update(payload.subarray(0, -16)),
    decipher.final(),
  ])
  return plaintext.toString('utf8')
}

export type { EncryptedTotpSecret }
