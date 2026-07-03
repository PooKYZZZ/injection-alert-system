import { createHash } from 'node:crypto'

import { normalizeAccountIdentifier } from './account-registry'
import { SCRYPT_CONCURRENCY_LIMIT } from './password-hash'

type ThrottleReason = 'IDENTIFIER_THROTTLED' | 'GLOBAL_THROTTLED'

type ThrottleCheck =
  | { allowed: true; identifierHash: string }
  | {
      allowed: false
      identifierHash: string
      reasonCode: ThrottleReason
    }

type Counter = {
  failures: number
  windowStartedAt: number
  blockedUntil: number
}

export type LoginThrottleOptions = {
  identifierMaxFailures: number
  identifierWindowMs: number
  identifierCooldownMs: number
  globalMaxFailures: number
  globalWindowMs: number
  globalCooldownMs: number
}

function readPositiveInteger(name: string, fallback: number): number {
  const raw = process.env[name]
  if (!raw) {
    return fallback
  }

  const value = Number(raw)
  return Number.isInteger(value) && value > 0 ? value : fallback
}

function counterAt(now: number): Counter {
  return { failures: 0, windowStartedAt: now, blockedUntil: 0 }
}

function refreshCounter(
  counter: Counter | undefined,
  now: number,
  windowMs: number
): Counter {
  if (!counter) {
    return counterAt(now)
  }
  if (counter.blockedUntil > now) {
    return counter
  }
  if (
    counter.blockedUntil > 0 ||
    now - counter.windowStartedAt >= windowMs
  ) {
    return counterAt(now)
  }
  return counter
}

export function hashNormalizedIdentifier(identifier: string): string {
  return createHash('sha256')
    .update(normalizeAccountIdentifier(identifier))
    .digest('hex')
}

export class LoginThrottle {
  private readonly identifiers = new Map<string, Counter>()
  private globalCounter: Counter

  constructor(
    private readonly options: LoginThrottleOptions,
    private readonly now: () => number = Date.now
  ) {
    this.globalCounter = counterAt(this.now())
  }

  check(identifier: string): ThrottleCheck {
    const now = this.now()
    const identifierHash = hashNormalizedIdentifier(identifier)
    const identifierCounter = refreshCounter(
      this.identifiers.get(identifierHash),
      now,
      this.options.identifierWindowMs
    )
    this.identifiers.set(identifierHash, identifierCounter)

    if (identifierCounter.blockedUntil > now) {
      return {
        allowed: false,
        identifierHash,
        reasonCode: 'IDENTIFIER_THROTTLED',
      }
    }

    this.globalCounter = refreshCounter(
      this.globalCounter,
      now,
      this.options.globalWindowMs
    )
    if (this.globalCounter.blockedUntil > now) {
      return {
        allowed: false,
        identifierHash,
        reasonCode: 'GLOBAL_THROTTLED',
      }
    }

    return { allowed: true, identifierHash }
  }

  recordFailure(identifierHash: string): void {
    const now = this.now()
    const identifierCounter = refreshCounter(
      this.identifiers.get(identifierHash),
      now,
      this.options.identifierWindowMs
    )
    identifierCounter.failures += 1
    if (identifierCounter.failures >= this.options.identifierMaxFailures) {
      identifierCounter.blockedUntil =
        now + this.options.identifierCooldownMs
    }
    this.identifiers.set(identifierHash, identifierCounter)

    this.globalCounter = refreshCounter(
      this.globalCounter,
      now,
      this.options.globalWindowMs
    )
    this.globalCounter.failures += 1
    if (this.globalCounter.failures >= this.options.globalMaxFailures) {
      this.globalCounter.blockedUntil = now + this.options.globalCooldownMs
    }
  }

  recordSuccess(identifierHash: string): void {
    this.identifiers.delete(identifierHash)
  }
}

type GateResult<T> =
  | { ok: true; value: T }
  | { ok: false; reasonCode: 'SCRYPT_BUSY' }

export class ScryptConcurrencyGate {
  private active = 0

  constructor(private readonly limit: number) {}

  async run<T>(task: () => Promise<T>): Promise<GateResult<T>> {
    if (this.active >= this.limit) {
      return { ok: false, reasonCode: 'SCRYPT_BUSY' }
    }

    this.active += 1
    try {
      return { ok: true, value: await task() }
    } finally {
      this.active -= 1
    }
  }
}

export const loginThrottle = new LoginThrottle({
  identifierMaxFailures: readPositiveInteger(
    'AUTH_LOGIN_MAX_FAILURES_PER_IDENTIFIER',
    5
  ),
  identifierWindowMs:
    readPositiveInteger('AUTH_LOGIN_IDENTIFIER_WINDOW_SECONDS', 300) * 1_000,
  identifierCooldownMs:
    readPositiveInteger('AUTH_LOGIN_IDENTIFIER_COOLDOWN_SECONDS', 300) * 1_000,
  globalMaxFailures: readPositiveInteger('AUTH_LOGIN_GLOBAL_MAX_FAILURES', 30),
  globalWindowMs:
    readPositiveInteger('AUTH_LOGIN_GLOBAL_WINDOW_SECONDS', 60) * 1_000,
  globalCooldownMs:
    readPositiveInteger('AUTH_LOGIN_GLOBAL_COOLDOWN_SECONDS', 60) * 1_000,
})

export const scryptConcurrencyGate = new ScryptConcurrencyGate(
  readPositiveInteger('AUTH_SCRYPT_CONCURRENCY_LIMIT', SCRYPT_CONCURRENCY_LIMIT)
)
