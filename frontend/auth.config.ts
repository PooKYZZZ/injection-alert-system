import type { NextAuthConfig } from 'next-auth'
import Credentials from 'next-auth/providers/credentials'
import { AUTH_CREDENTIAL_FIELDS } from './lib/auth/credential-mode'
import { isUserRole } from './lib/auth/roles'

// Edge-safe config: no authorize() callback — Node.js-only logic lives in auth.ts.
export const authConfig = {
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: AUTH_CREDENTIAL_FIELDS,
    }),
  ],
  pages: { signIn: '/login' },
  callbacks: {
    // The edge-safe middleware only needs the already-signed JWT role claim
    // for an early route response. Database freshness remains authoritative
    // in the server page and BFF guards.
    session({ session, token }) {
      if (isUserRole(token.role)) {
        session.user.role = token.role
      }
      return session
    },
  },
} satisfies NextAuthConfig
