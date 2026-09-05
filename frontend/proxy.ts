import NextAuth, { type NextAuthRequest } from 'next-auth'
import { NextResponse } from 'next/server'
import type { NextFetchEvent, NextRequest } from 'next/server'
import { authConfig } from './auth.config'
import {
  isUserRole,
  PERMISSIONS,
  roleHasPermission,
  type Permission,
} from './lib/auth/roles'

function protectedRoutePermission(pathname: string): Permission | null {
  if (pathname === '/ml-health' || pathname.startsWith('/ml-health/')) {
    return PERMISSIONS.ML_HEALTH_READ
  }
  if (pathname === '/ml-model' || pathname.startsWith('/ml-model/')) {
    return PERMISSIONS.ML_MODEL_READ
  }
  return null
}

function routeAccessDenied(status: 401 | 403): Response {
  if (status === 401) {
    return NextResponse.json(
      { error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' } },
      { status }
    )
  }
  return new NextResponse(
    '<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Access denied</title></head><body><main><p>403</p><h1>Access denied</h1><p>Your account is not authorized to access this section.</p></main></body></html>',
    {
      status,
      headers: {
        'content-type': 'text/html; charset=utf-8',
        'cache-control': 'no-store',
      },
    }
  )
}

function withSecurityHeaders(response: Response): Response {
  response.headers.set('X-Content-Type-Options', 'nosniff')
  response.headers.set('X-Frame-Options', 'DENY')
  response.headers.set('Referrer-Policy', 'strict-origin-when-cross-origin')
  response.headers.set(
    'Permissions-Policy',
    'camera=(), microphone=(), geolocation=(), payment=()'
  )
  return response
}

const { auth } = NextAuth(authConfig)

const handler = auth((req: NextAuthRequest, event: NextFetchEvent) => {
  const permission = protectedRoutePermission(req.nextUrl.pathname)
  if (permission) {
    const role = req.auth?.user?.role
    if (!isUserRole(role)) {
      return routeAccessDenied(401)
    }
    if (!roleHasPermission(role, permission)) {
      return routeAccessDenied(403)
    }
  }
  void event
})

export default async function middleware(
  req: NextRequest,
  event: NextFetchEvent
): Promise<Response> {
  const result = await handler(req, event)
  return withSecurityHeaders(
    result instanceof Response ? result : NextResponse.next()
  )
}

export const config = {
  matcher: [
    '/(dashboard|alerts|ml-health|ml-model|user-management)/:path*',
  ],
}
