import 'server-only'

import { cookies } from 'next/headers'

export const RECOVERY_COOKIE_NAME = '__Host-cybertrace-recovery'

export async function setRecoveryCompletionCookie(token: string): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.set(RECOVERY_COOKIE_NAME, token, {
    httpOnly: true,
    secure: process.env.NODE_ENV !== 'development',
    sameSite: 'lax',
    path: '/',
    maxAge: 5 * 60,
  })
}

export function readRecoveryCompletionCookie(request: Request): string | null {
  const raw = request.headers.get('cookie') ?? ''
  const match = raw.match(/(?:^|;\s*)__Host-cybertrace-recovery=([^;]+)/)
  return match?.[1] ?? null
}

export async function clearRecoveryCompletionCookie(): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.set(RECOVERY_COOKIE_NAME, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV !== 'development',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  })
}
