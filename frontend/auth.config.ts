import type { NextAuthConfig } from 'next-auth'
import Credentials from 'next-auth/providers/credentials'
import { AUTH_CREDENTIAL_FIELDS } from './lib/auth/credential-mode'

// Edge-safe config: no authorize() callback — Node.js-only logic lives in auth.ts.
export const authConfig = {
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: AUTH_CREDENTIAL_FIELDS,
    }),
  ],
  pages: { signIn: '/login' },
} satisfies NextAuthConfig
