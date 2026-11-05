import { createHmac } from 'node:crypto'

import { readLoginThrottlePolicy } from './login-throttle-policy'
import { PASSWORD_HASH_CONCURRENCY_LIMIT } from './password-hash'

type ThrottleReason = 'IDENTIFIER_THROTTLED'

type ThrottleCheck =
  | { allowed: true; identifierHash: string; failureCount: number }
  | {
      allowed: false
      identifierHash: string
      failureCount: number
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
  maxIdentifierEntries?: number
}

function readPositiveInteger(name: string, fallback: number): number {
  const raw = process.env[name]
  if (!raw) return fallback

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
  if (!counter) return counterAt(now)
  if (counter.blockedUntil > now) return counter
  if (
    counter.blockedUntil > 0 ||
    now - counter.windowStartedAt >= windowMs
  ) {
    return counterAt(now)
  }
  return counter
}

export function hashNormalizedIdentifier(
  identifier: string,
  key = process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET
): string {
  if (!key) throw new Error('Authentication secret is unavailable.')
  return createHmac('sha256', key)
    .update(identifier.trim().toLowerCase())
    .digest('hex')
}

export class LoginThrottle {
  private readonly identifiers = new Map<string, Counter>()

  constructor(
    private readonly options: LoginThrottleOptions,
    private readonly now: () => number = Date.now
  ) {}

  get trackedIdentifierCount(): number {
    return this.identifiers.size
  }

  private prune(now: number): void {
    for (const [identifierHash, counter] of this.identifiers) {
      if (
        counter.blockedUntil <= now &&
        (counter.blockedUntil > 0 ||
          now - counter.windowStartedAt >= this.options.identifierWindowMs)
      ) {
        this.identifiers.delete(identifierHash)
      }
    }
  }

  private remember(identifierHash: string, counter: Counter): void {
    if (!this.identifiers.has(identifierHash)) {
      const maxEntries = this.options.maxIdentifierEntries ?? 1_024
      while (this.identifiers.size >= maxEntries) {
        const oldest = this.identifiers.keys().next().value
        if (typeof oldest !== 'string') break
        this.identifiers.delete(oldest)
      }
    }
    this.identifiers.set(identifierHash, counter)
  }

  check(identifier: string): ThrottleCheck {
    const now = this.now()
    this.prune(now)
    const identifierHash = hashNormalizedIdentifier(identifier)
    const identifierCounter = refreshCounter(
      this.identifiers.get(identifierHash),
      now,
      this.options.identifierWindowMs
    )
    this.remember(identifierHash, identifierCounter)

    if (identifierCounter.blockedUntil > now) {
      return {
        allowed: false,
        identifierHash,
        failureCount: identifierCounter.failures,
        reasonCode: 'IDENTIFIER_THROTTLED',
      }
    }

    return {
      allowed: true,
      identifierHash,
      failureCount: identifierCounter.failures,
    }
  }

  recordFailure(identifierHash: string): number {
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
    this.remember(identifierHash, identifierCounter)
    return identifierCounter.failures
  }

  recordSuccess(identifierHash: string): void {
    this.identifiers.delete(identifierHash)
  }
}

type GateResult<T> =
  | { ok: true; value: T }
  | { ok: false; reasonCode: 'PASSWORD_HASH_BUSY' }

export class PasswordHashConcurrencyGate {
  private active = 0

  constructor(private readonly limit: number) {}

  async run<T>(task: () => Promise<T>): Promise<GateResult<T>> {
    if (this.active >= this.limit) {
      return { ok: false, reasonCode: 'PASSWORD_HASH_BUSY' }
    }

    this.active += 1
    try {
      return { ok: true, value: await task() }
    } finally {
      this.active -= 1
    }
  }
}

const throttlePolicy = readLoginThrottlePolicy()

export const loginThrottle = new LoginThrottle({
  identifierMaxFailures: throttlePolicy.maxFailures,
  identifierWindowMs: throttlePolicy.windowSeconds * 1_000,
  identifierCooldownMs: throttlePolicy.cooldownSeconds * 1_000,
  maxIdentifierEntries: readPositiveInteger(
    'AUTH_LOGIN_MAX_IDENTIFIER_ENTRIES',
    1_024
  ),
})

export const passwordHashConcurrencyGate = new PasswordHashConcurrencyGate(
  readPositiveInteger(
    'AUTH_PASSWORD_HASH_CONCURRENCY_LIMIT',
    PASSWORD_HASH_CONCURRENCY_LIMIT
  )
)
