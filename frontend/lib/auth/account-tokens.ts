import 'server-only'

import { createHash, randomBytes } from 'node:crypto'

export function generateOpaqueToken(): string {
  return randomBytes(32).toString('base64url')
}

export function digestOpaqueToken(token: string): string {
  if (!token || token.length > 512) {
    throw new Error('Account action token is invalid.')
  }
  return createHash('sha256').update(token, 'utf8').digest('hex')
}

export function buildTrustedActionUrl(
  configuredOrigin: string,
  pathname: string,
  token: string
): string {
  const origin = new URL(configuredOrigin)
  const local = origin.hostname === 'localhost' || origin.hostname === '127.0.0.1'
  if (
    origin.origin !== configuredOrigin.replace(/\/$/, '') ||
    (origin.protocol !== 'https:' && !(local && origin.protocol === 'http:')) ||
    !pathname.startsWith('/')
  ) {
    throw new Error('AUTH_APP_ORIGIN is invalid.')
  }
  const url = new URL(pathname, `${origin.origin}/`)
  url.searchParams.set('token', token)
  return url.toString()
}
