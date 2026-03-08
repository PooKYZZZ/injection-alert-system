import NextAuth from 'next-auth'
import { authConfig } from './auth.config'

export const { auth: middleware } = NextAuth(authConfig)

export const config = {
  // Protect all page routes.
  // Excludes:
  //   /login          — sign-in page (avoid redirect loop)
  //   /api/**         — BFF route handlers return JSON 401s themselves
  //   /_next/**       — Next.js internals
  //   /favicon.ico    — static asset
  matcher: ['/((?!login|api|_next/static|_next/image|favicon\\.ico).*)'],
}
