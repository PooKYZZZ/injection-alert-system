import 'server-only'

import { createHash, randomBytes } from 'node:crypto'
import { cookies } from 'next/headers'

export const PREAUTH_COOKIE_NAME = process.env.NODE_ENV === 'development'
  ? 'cybertrace-preauth'
  : '__Host-cybertrace-preauth'
export const PREAUTH_TTL_SECONDS = 10 * 60

export function generatePreAuthHandle(): string {
  return randomBytes(32).toString('base64url')
}

export function digestPreAuthHandle(handle: string): string {
  if (!/^[A-Za-z0-9_-]{40,128}$/.test(handle)) {
    throw new Error('Pre-auth handle is invalid.')
  }
  return createHash('sha256').update(handle, 'utf8').digest('hex')
}

export async function setPreAuthCookie(handle: string): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.set(PREAUTH_COOKIE_NAME, handle, {
    httpOnly: true,
    secure: process.env.NODE_ENV !== 'development',
    sameSite: 'lax',
    path: '/',
    maxAge: PREAUTH_TTL_SECONDS,
  })
}

export function readPreAuthHandle(request: Request): string | null {
  const raw = request.headers.get('cookie') ?? ''
  const match = raw.match(
    new RegExp(`(?:^|;\\s*)${PREAUTH_COOKIE_NAME}=([^;]+)`)
  )
  const value = match?.[1]
  return value && /^[A-Za-z0-9_-]{40,128}$/.test(value) ? value : null
}

export async function readPreAuthHandleFromCookies(): Promise<string | null> {
  const value = (await cookies()).get(PREAUTH_COOKIE_NAME)?.value
  return value && /^[A-Za-z0-9_-]{40,128}$/.test(value) ? value : null
}

export async function clearPreAuthCookie(): Promise<void> {
  const cookieStore = await cookies()
  cookieStore.set(PREAUTH_COOKIE_NAME, '', {
    httpOnly: true,
    secure: process.env.NODE_ENV !== 'development',
    sameSite: 'lax',
    path: '/',
    maxAge: 0,
  })
}
