import NextAuth, { type NextAuthRequest } from 'next-auth'
import { NextResponse } from 'next/server'
import type { NextFetchEvent, NextRequest } from 'next/server'
import { authConfig } from './auth.config'

const { auth } = NextAuth(authConfig)

const handler = auth((req: NextAuthRequest, event: NextFetchEvent) => {
  void req.auth
  void event
})

export default async function middleware(
  req: NextRequest,
  event: NextFetchEvent
): Promise<Response> {
  const result = await handler(req, event)
  if (result instanceof Response) {
    result.headers.set('X-Content-Type-Options', 'nosniff')
    result.headers.set('X-Frame-Options', 'DENY')
    result.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
    result.headers.set(
      'Permissions-Policy',
      'camera=(), microphone=(), geolocation=(), payment=()'
    )
    return result
  }
  const nextResponse = NextResponse.next()
  nextResponse.headers.set('X-Content-Type-Options', 'nosniff')
  nextResponse.headers.set('X-Frame-Options', 'DENY')
  nextResponse.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  nextResponse.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=(), payment=()'
  )
  return nextResponse
}

export const config = {
  matcher: [
    '/(dashboard|alerts|ml-health|user-management)/:path*',
  ],
}
