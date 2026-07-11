import { createHmac } from 'node:crypto'

const BASE32_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
export const TOTP_PERIOD_MS = 30_000

type WaitOptions = {
  now?: () => number
  sleep?: (durationMs: number) => Promise<void>
  settleMs?: number
  maxWaitMs?: number
}

function decodeBase32(value: string): Buffer {
  const normalized = value.replace(/=+$/, '').toUpperCase()
  if (!normalized || /[^A-Z2-7]/.test(normalized)) {
    throw new Error('TOTP secret is invalid.')
  }

  let buffer = 0
  let bits = 0
  const bytes: number[] = []
  for (const character of normalized) {
    buffer = (buffer << 5) | BASE32_ALPHABET.indexOf(character)
    bits += 5
    if (bits >= 8) {
      bits -= 8
      bytes.push((buffer >> bits) & 0xff)
    }
  }
  if (bytes.length === 0) throw new Error('TOTP secret is invalid.')
  return Buffer.from(bytes)
}

export function totpTimeStep(nowMs = Date.now()): number {
  if (!Number.isFinite(nowMs) || nowMs < 0) {
    throw new Error('TOTP time is invalid.')
  }
  return Math.floor(nowMs / TOTP_PERIOD_MS)
}

export function totpCodeAtStep(
  secret: string,
  step: number,
  digits: 6 | 8 = 6
): string {
  if (!Number.isSafeInteger(step) || step < 0) {
    throw new Error('TOTP time step is invalid.')
  }

  const counter = Buffer.alloc(8)
  counter.writeBigUInt64BE(BigInt(step))
  const digest = createHmac('sha1', decodeBase32(secret))
    .update(counter)
    .digest()
  const offset = digest[digest.length - 1] & 0x0f
  const binary =
    ((digest[offset] & 0x7f) << 24) |
    (digest[offset + 1] << 16) |
    (digest[offset + 2] << 8) |
    digest[offset + 3]
  return String(binary % 10 ** digits).padStart(digits, '0')
}

export function totpCodeAtTime(
  secret: string,
  nowMs = Date.now()
): { code: string; step: number } {
  const step = totpTimeStep(nowMs)
  return { code: totpCodeAtStep(secret, step), step }
}

export function parseTotpSecret(provisioningUri: string): string {
  let parsed: URL
  try {
    parsed = new URL(provisioningUri)
  } catch {
    throw new Error('TOTP provisioning URI is invalid.')
  }
  const secret = parsed.searchParams.get('secret')?.toUpperCase() ?? ''
  if (
    parsed.protocol !== 'otpauth:' ||
    parsed.hostname !== 'totp' ||
    !/^[A-Z2-7]+$/.test(secret)
  ) {
    throw new Error('TOTP provisioning URI is invalid.')
  }
  decodeBase32(secret)
  return secret
}

export async function waitForTotpStepAfter(
  previousStep: number,
  options: WaitOptions = {}
): Promise<number> {
  if (!Number.isSafeInteger(previousStep) || previousStep < 0) {
    throw new Error('Previous TOTP time step is invalid.')
  }

  const now = options.now ?? Date.now
  const sleep =
    options.sleep ??
    ((durationMs: number) =>
      new Promise<void>((resolve) => setTimeout(resolve, durationMs)))
  const settleMs = options.settleMs ?? 50
  const maxWaitMs = options.maxWaitMs ?? TOTP_PERIOD_MS + 1_000
  const currentTime = now()
  const currentStep = totpTimeStep(currentTime)
  if (currentStep > previousStep) return currentStep

  const waitMs =
    (previousStep + 1) * TOTP_PERIOD_MS - currentTime + settleMs
  if (waitMs < 0 || waitMs > maxWaitMs) {
    throw new Error('A newer TOTP time step is not safely reachable.')
  }

  await sleep(waitMs)
  const nextStep = totpTimeStep(now())
  if (nextStep <= previousStep) {
    throw new Error('A newer TOTP time step is not safely reachable.')
  }
  return nextStep
}
