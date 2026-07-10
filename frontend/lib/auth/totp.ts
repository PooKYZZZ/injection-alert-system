import 'server-only'

import { createHmac, randomBytes, timingSafeEqual } from 'node:crypto'

const BASE32 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
const PERIOD_SECONDS = 30

function decodeBase32(value: string): Buffer {
  const normalized = value.replace(/=+$/, '').toUpperCase()
  if (!normalized || /[^A-Z2-7]/.test(normalized)) throw new Error('Invalid TOTP secret.')
  let buffer = 0
  let bits = 0
  const bytes: number[] = []
  for (const character of normalized) {
    buffer = (buffer << 5) | BASE32.indexOf(character)
    bits += 5
    if (bits >= 8) {
      bits -= 8
      bytes.push((buffer >> bits) & 0xff)
    }
  }
  return Buffer.from(bytes)
}

function codeAtStep(secret: string, step: number): string {
  const key = decodeBase32(secret)
  const counter = Buffer.alloc(8)
  counter.writeBigUInt64BE(BigInt(step))
  const digest = createHmac('sha1', key).update(counter).digest()
  const offset = digest[digest.length - 1] & 0x0f
  const binary =
    ((digest[offset] & 0x7f) << 24) |
    (digest[offset + 1] << 16) |
    (digest[offset + 2] << 8) |
    digest[offset + 3]
  return String(binary % 1_000_000).padStart(6, '0')
}

export function generateTotpSecret(): string {
  let value = ''
  const buffer = randomBytes(20)
  let bits = 0
  let current = 0
  for (const byte of buffer) {
    current = (current << 8) | byte
    bits += 8
    while (bits >= 5) {
      bits -= 5
      value += BASE32[(current >> bits) & 31]
    }
  }
  if (bits > 0) value += BASE32[(current << (5 - bits)) & 31]
  buffer.fill(0)
  return value
}

export function verifyTotpCode(
  secret: string,
  submittedCode: string,
  nowMs = Date.now()
): { valid: boolean; timeStep?: number } {
  if (!/^\d{6}$/.test(submittedCode)) return { valid: false }
  const currentStep = Math.floor(nowMs / 1_000 / PERIOD_SECONDS)
  for (const offset of [-1, 0, 1]) {
    const step = currentStep + offset
    if (step < 0) continue
    const expected = Buffer.from(codeAtStep(secret, step), 'utf8')
    const actual = Buffer.from(submittedCode, 'utf8')
    if (timingSafeEqual(expected, actual)) return { valid: true, timeStep: step }
  }
  return { valid: false }
}

export function buildTotpProvisioningUri(
  accountLabel: string,
  secret: string
): string {
  const label = encodeURIComponent(`CyberTrace:${accountLabel}`)
  const issuer = encodeURIComponent('CyberTrace')
  return `otpauth://totp/${label}?secret=${encodeURIComponent(secret)}&issuer=${issuer}&algorithm=SHA1&digits=6&period=${PERIOD_SECONDS}`
}

export { PERIOD_SECONDS }
