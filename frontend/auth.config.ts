import type { NextAuthConfig } from 'next-auth'
import Credentials from 'next-auth/providers/credentials'

// Edge-safe config: no authorize() callback — Node.js-only logic lives in auth.ts.
export const authConfig = {
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        password: { label: 'Password', type: 'password', placeholder: '' },
      },
    }),
  ],
  pages: { signIn: '/login' },
} satisfies NextAuthConfig
