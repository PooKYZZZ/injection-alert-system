import NextAuth from 'next-auth'
import { NextResponse } from 'next/server'
import type { NextMiddleware, NextRequest, NextFetchEvent } from 'next/server'
import { authConfig } from './auth.config'

const { auth } = NextAuth(authConfig)

const handler = auth((req) => {
  void req
}) as unknown as NextMiddleware

export default async (req: NextRequest, event: NextFetchEvent) => {
  const result = await handler(req, event)
  if (result instanceof Response) {
    result.headers.set('X-Content-Type-Options', 'nosniff')
    result.headers.set('X-Frame-Options', 'DENY')
    return result
  }
  const nextResponse = NextResponse.next()
  nextResponse.headers.set('X-Content-Type-Options', 'nosniff')
  nextResponse.headers.set('X-Frame-Options', 'DENY')
  return nextResponse
}

export const config = {
  matcher: [
    '/(dashboard|alerts|ml-health)/:path*',
  ],
}
