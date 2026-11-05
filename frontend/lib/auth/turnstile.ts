import 'server-only'

import { readLoginThrottlePolicy } from './login-throttle-policy'

const VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'
const VERIFY_TIMEOUT_MS = 5_000
const MAX_TOKEN_LENGTH = 2_048
const TEST_SITE_KEYS = new Set([
  '1x00000000000000000000AA',
  '2x00000000000000000000AB',
  '1x00000000000000000000BB',
  '2x00000000000000000000BB',
  '3x00000000000000000000FF',
])
const TEST_SECRET_KEYS = new Set([
  '1x0000000000000000000000000000000AA',
  '2x0000000000000000000000000000000AA',
  '3x0000000000000000000000000000000AA',
])
const HOSTNAME_PATTERN = /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*$/i

type TurnstileResponse = {
  success?: unknown
  action?: unknown
  hostname?: unknown
  metadata?: unknown
}

export type TurnstileConfiguration = {
  siteKey: string
  secretKey: string
  expectedHostname: string
}

export type TurnstileVerificationResult =
  | { valid: true }
  | { valid: false; reason: 'invalid' | 'unavailable' | 'misconfigured' }

export function isTurnstileEnabled(): boolean {
  return process.env.AUTH_TURNSTILE_ENABLED === 'true'
}

function isLoopbackHostname(value: string): boolean {
  return value === 'localhost' || value === '127.0.0.1' || value === '::1'
}

function isManagedLoopbackE2E(expectedHostname: string): boolean {
  if (process.env.CYBERTRACE_E2E_MANAGED !== 'true') return false
  try {
    const appOrigin = new URL(process.env.AUTH_APP_ORIGIN ?? '')
    const supabaseUrl = new URL(process.env.SUPABASE_URL ?? '')
    return (
      appOrigin.protocol === 'http:' &&
      isLoopbackHostname(appOrigin.hostname) &&
      isLoopbackHostname(supabaseUrl.hostname) &&
      expectedHostname === appOrigin.hostname
    )
  } catch {
    return false
  }
}

function isManagedTestKeyResponse(
  result: TurnstileResponse,
  configuration: TurnstileConfiguration
): boolean {
  const metadata = result.metadata
  return (
    TEST_SITE_KEYS.has(configuration.siteKey) &&
    TEST_SECRET_KEYS.has(configuration.secretKey) &&
    isManagedLoopbackE2E(configuration.expectedHostname) &&
    result.action === undefined &&
    result.hostname === 'example.com' &&
    typeof metadata === 'object' &&
    metadata !== null &&
    'result_with_testing_key' in metadata &&
    metadata.result_with_testing_key === true
  )
}

export function readTurnstileConfiguration(): TurnstileConfiguration | null {
  if (!isTurnstileEnabled()) return null
  const siteKey = process.env.NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY?.trim()
  const secretKey = process.env.AUTH_TURNSTILE_SECRET_KEY?.trim()
  const expectedHostname = process.env.AUTH_TURNSTILE_EXPECTED_HOSTNAME
    ?.trim()
    .toLowerCase()
  if (
    !siteKey ||
    !secretKey ||
    !expectedHostname ||
    !HOSTNAME_PATTERN.test(expectedHostname)
  ) {
    return null
  }

  const usesTestKey =
    TEST_SITE_KEYS.has(siteKey) || TEST_SECRET_KEYS.has(secretKey)
  if (
    process.env.NODE_ENV === 'production' &&
    usesTestKey &&
    !isManagedLoopbackE2E(expectedHostname)
  ) {
    return null
  }

  return { siteKey, secretKey, expectedHostname }
}

export function isTurnstileConfigured(): boolean {
  return readTurnstileConfiguration() !== null
}

export function shouldRequireTurnstile(failureCount: number): boolean {
  return (
    Number.isInteger(failureCount) &&
    failureCount >= readLoginThrottlePolicy().challengeThreshold
  )
}

export async function verifyTurnstileToken(
  token: unknown,
  fetchImpl: typeof fetch = fetch
): Promise<TurnstileVerificationResult> {
  const configuration = readTurnstileConfiguration()
  if (!configuration) return { valid: false, reason: 'misconfigured' }
  if (
    typeof token !== 'string' ||
    token.length < 1 ||
    token.length > MAX_TOKEN_LENGTH
  ) {
    return { valid: false, reason: 'invalid' }
  }

  const body = new URLSearchParams({
    secret: configuration.secretKey,
    response: token,
  })
  let response: Response
  try {
    response = await fetchImpl(VERIFY_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body,
      signal: AbortSignal.timeout(VERIFY_TIMEOUT_MS),
    })
  } catch {
    return { valid: false, reason: 'unavailable' }
  }
  if (!response.ok) return { valid: false, reason: 'unavailable' }

  let result: TurnstileResponse
  try {
    const payload: unknown = await response.json()
    if (typeof payload !== 'object' || payload === null) {
      return { valid: false, reason: 'unavailable' }
    }
    result = payload as TurnstileResponse
  } catch {
    return { valid: false, reason: 'unavailable' }
  }
  if (result.success !== true) return { valid: false, reason: 'invalid' }
  // Cloudflare's documented dummy keys return hostname=example.com and omit
  // action. Accept that shape only with their explicit testing-key marker in
  // the isolated loopback E2E environment; real credentials keep both checks.
  if (isManagedTestKeyResponse(result, configuration)) return { valid: true }
  if (
    result.action !== 'login' ||
    typeof result.hostname !== 'string' ||
    result.hostname.toLowerCase() !== configuration.expectedHostname
  ) {
    return { valid: false, reason: 'invalid' }
  }
  return { valid: true }
}
