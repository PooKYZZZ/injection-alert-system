import { createCipheriv, createDecipheriv, randomBytes } from 'node:crypto'

const ALGORITHM = 'aes-256-gcm'
const AAD_PREFIX = 'cybertrace:notification-payload:v1'
const AUTH_TAG_BYTES = 16
const KEY_VERSION = 1
const NONCE_BYTES = 12
const MAX_CONTEXT_LENGTH = 320
const MAX_PAYLOAD_FIELDS = 16
const MAX_PAYLOAD_VALUE_LENGTH = 4_096

export type NotificationPayloadContext = {
  kind: string
  recipient: string
  idempotencyKey: string
}

export type ProtectedNotificationPayload = {
  ciphertext: string
  nonce: string
  key_version: number
}

function unavailable(): Error {
  return new Error('Notification payload is unavailable.')
}

function encryptionKey(): Buffer {
  const raw = process.env.NOTIFICATION_PAYLOAD_ENCRYPTION_KEY?.trim()
  if (!raw) throw unavailable()
  const isHex = /^[0-9a-f]{64}$/i.test(raw)
  if (!isHex && !/^[A-Za-z0-9+/]+={0,2}$/.test(raw)) throw unavailable()
  const key = Buffer.from(raw, isHex ? 'hex' : 'base64')
  if (!isHex && key.toString('base64') !== raw) throw unavailable()
  if (key.length !== 32) throw unavailable()
  return key
}

function validateContext(context: NotificationPayloadContext): void {
  for (const value of [
    context.kind,
    context.recipient,
    context.idempotencyKey,
  ]) {
    if (
      typeof value !== 'string' ||
      value.length < 1 ||
      value.length > MAX_CONTEXT_LENGTH ||
      value.includes('\0')
    ) {
      throw unavailable()
    }
  }
}

function additionalData(context: NotificationPayloadContext): Buffer {
  validateContext(context)
  return Buffer.from(
    [
      AAD_PREFIX,
      context.kind,
      context.recipient,
      context.idempotencyKey,
    ].join('\0'),
    'utf8'
  )
}

function validatePayload(payload: unknown): Record<string, string> {
  if (!payload || typeof payload !== 'object' || Array.isArray(payload)) {
    throw unavailable()
  }
  const entries = Object.entries(payload)
  if (entries.length < 1 || entries.length > MAX_PAYLOAD_FIELDS) {
    throw unavailable()
  }
  for (const [key, value] of entries) {
    if (
      key.length < 1 ||
      key.length > 128 ||
      typeof value !== 'string' ||
      value.length < 1 ||
      value.length > MAX_PAYLOAD_VALUE_LENGTH
    ) {
      throw unavailable()
    }
  }
  return Object.fromEntries(entries) as Record<string, string>
}

function decodeBase64Url(value: unknown): Buffer {
  if (typeof value !== 'string' || !/^[A-Za-z0-9_-]+$/.test(value)) {
    throw unavailable()
  }
  const decoded = Buffer.from(value, 'base64url')
  if (decoded.toString('base64url') !== value) throw unavailable()
  return decoded
}

export function protectNotificationPayload(
  context: NotificationPayloadContext,
  payload: Record<string, string>
): ProtectedNotificationPayload {
  try {
    const nonce = randomBytes(NONCE_BYTES)
    const cipher = createCipheriv(ALGORITHM, encryptionKey(), nonce)
    cipher.setAAD(additionalData(context))
    const ciphertext = Buffer.concat([
      cipher.update(JSON.stringify(validatePayload(payload)), 'utf8'),
      cipher.final(),
      cipher.getAuthTag(),
    ])
    return {
      ciphertext: ciphertext.toString('base64url'),
      nonce: nonce.toString('base64url'),
      key_version: KEY_VERSION,
    }
  } catch {
    throw unavailable()
  }
}

export function unprotectNotificationPayload(
  context: NotificationPayloadContext,
  envelope: ProtectedNotificationPayload
): Record<string, string> {
  try {
    if (
      !envelope ||
      envelope.key_version !== KEY_VERSION ||
      Object.keys(envelope).sort().join(',') !==
        'ciphertext,key_version,nonce'
    ) {
      throw unavailable()
    }
    const nonce = decodeBase64Url(envelope.nonce)
    const payload = decodeBase64Url(envelope.ciphertext)
    if (nonce.length !== NONCE_BYTES || payload.length <= AUTH_TAG_BYTES) {
      throw unavailable()
    }
    const tagOffset = payload.length - AUTH_TAG_BYTES
    const decipher = createDecipheriv(ALGORITHM, encryptionKey(), nonce)
    decipher.setAAD(additionalData(context))
    decipher.setAuthTag(payload.subarray(tagOffset))
    const plaintext = Buffer.concat([
      decipher.update(payload.subarray(0, tagOffset)),
      decipher.final(),
    ]).toString('utf8')
    return validatePayload(JSON.parse(plaintext))
  } catch {
    throw unavailable()
  }
}
