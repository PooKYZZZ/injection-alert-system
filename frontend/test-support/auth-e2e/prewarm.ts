export const AUTH_E2E_PREWARM_REQUESTS = [
  { method: 'GET', path: '/dashboard' },
  { method: 'GET', path: '/mfa/enroll' },
  { method: 'GET', path: '/mfa/verify' },
  { method: 'GET', path: '/mfa/recover' },
  { method: 'GET', path: '/mfa/step-up' },
  { method: 'POST', path: '/api/auth/mfa/enroll' },
  { method: 'POST', path: '/api/auth/mfa/enroll/verify' },
  { method: 'POST', path: '/api/auth/mfa/enroll/finalize' },
  { method: 'POST', path: '/api/auth/mfa/verify' },
  { method: 'POST', path: '/api/auth/mfa/recovery/backup' },
  { method: 'POST', path: '/api/auth/mfa/recovery/email/request' },
  { method: 'POST', path: '/api/auth/mfa/recovery/email/verify' },
  { method: 'POST', path: '/api/auth/mfa/step-up' },
  { method: 'POST', path: '/api/auth/mfa/step-up/verify' },
] as const

type Fetcher = (
  input: string | URL | Request,
  init?: RequestInit
) => Promise<Response>

export async function prewarmAuthRoutes(
  origin: string,
  fetcher: Fetcher = fetch,
  sleep: (durationMs: number) => Promise<void> = (durationMs) =>
    new Promise((resolve) => setTimeout(resolve, durationMs))
): Promise<void> {
  const parsedOrigin = new URL(origin).origin
  if (parsedOrigin !== origin) {
    throw new Error('Authentication E2E application origin is invalid.')
  }

  for (const request of AUTH_E2E_PREWARM_REQUESTS) {
    const response = await fetcher(`${parsedOrigin}${request.path}`, {
      method: request.method,
      redirect: 'manual',
      ...(request.method === 'POST'
        ? { headers: { origin: parsedOrigin } }
        : {}),
    })
    if (response.status >= 500) {
      throw new Error('Authentication E2E route prewarming failed.')
    }
  }
  await sleep(500)
}
