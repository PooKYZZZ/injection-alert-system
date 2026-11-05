export type LoginThrottlePolicy = {
  challengeThreshold: number
  maxFailures: number
  windowSeconds: number
  cooldownSeconds: number
}

function configuredInteger(
  name: string,
  fallback: number,
  minimum: number,
  maximum: number
): number {
  const raw = process.env[name]
  if (raw === undefined || raw === '') return fallback
  const value = Number(raw)
  if (
    !Number.isInteger(value) ||
    value < minimum ||
    value > maximum
  ) {
    throw new Error('Invalid login throttle configuration.')
  }
  return value
}

export function readLoginThrottlePolicy(): LoginThrottlePolicy {
  const maxFailures = configuredInteger(
    'AUTH_LOGIN_MAX_FAILURES_PER_IDENTIFIER',
    5,
    2,
    20
  )
  const challengeThreshold = configuredInteger(
    'AUTH_LOGIN_TURNSTILE_AFTER_FAILURES',
    Math.min(3, maxFailures - 1),
    1,
    maxFailures - 1
  )

  return {
    challengeThreshold,
    maxFailures,
    windowSeconds: configuredInteger(
      'AUTH_LOGIN_IDENTIFIER_WINDOW_SECONDS',
      300,
      1,
      3_600
    ),
    cooldownSeconds: configuredInteger(
      'AUTH_LOGIN_IDENTIFIER_COOLDOWN_SECONDS',
      300,
      1,
      3_600
    ),
  }
}
