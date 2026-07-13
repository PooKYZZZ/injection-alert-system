import 'server-only'

import { cookies } from 'next/headers'

export const MFA_COMPLETION_COOKIE_NAME = process.env.NODE_ENV === 'development'
  ? 'cybertrace-mfa-completion'
  : '__Host-cybertrace-mfa-completion'
const MFA_COMPLETION_TTL_SECONDS = 2 * 60

function validToken(value: string | undefined): value is string {
  return Boolean(value && /^[A-Za-z0-9_-]{40,128}$/.test(value))
}

export async function setMfaCompletionCookie(token: string): Promise<void> {
  if (!validToken(token)) throw new Error('MFA completion token is invalid.')
  const cookieStore = await cookies()
  cookieStore.set(MFA_COMPLETION_COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV !== 'development',
    sameSite: 'lax',
    path: '/',
    maxAge: MFA_COMPLETION_TTL_SECONDS,
  })
}

export function readMfaCompletionCookie(request: Request): string | null {
  const raw = request.headers.get('cookie') ?? ''
  const match = raw.match(
    new RegExp(`(?:^|;\\s*)${MFA_COMPLETION_COOKIE_NAME}=([^;]+)`)
  )
  return validToken(match?.[1]) ? match![1] : null
}

export async function clearMfaCompletionCookie(): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.set(MFA_COMPLETION_COOKIE_NAME, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV !== 'development',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  })
}
