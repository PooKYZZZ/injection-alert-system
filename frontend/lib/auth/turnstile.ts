import 'server-only'

const VERIFY_URL = 'https://challenges.cloudflare.com/turnstile/v0/siteverify'

export function shouldRequireTurnstile(failureCount: number): boolean {
  return Number.isInteger(failureCount) && failureCount >= 5
}

type TurnstileResponse = {
  success?: boolean
  action?: string
  hostname?: string
}

export async function verifyTurnstileToken(
  token: unknown,
  expectedAction: string,
  expectedHostname?: string,
  fetchImpl: typeof fetch = fetch
): Promise<boolean> {
  const secret = process.env.AUTH_TURNSTILE_SECRET_KEY
  if (process.env.AUTH_TURNSTILE_ENABLED !== 'true' || !secret || typeof token !== 'string' || token.length < 1 || token.length > 4096) {
    return false
  }
  const body = new URLSearchParams({ secret, response: token })
  let response: Response
  try {
    response = await fetchImpl(VERIFY_URL, {
      method: 'POST',
      headers: { 'content-type': 'application/x-www-form-urlencoded' },
      body,
    })
  } catch {
    return false
  }
  if (!response.ok) return false
  let result: TurnstileResponse
  try {
    result = (await response.json()) as TurnstileResponse
  } catch {
    return false
  }
  return Boolean(
    result.success &&
      result.action === expectedAction &&
      (!expectedHostname || result.hostname === expectedHostname)
  )
}
