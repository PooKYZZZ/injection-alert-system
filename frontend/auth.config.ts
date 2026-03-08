import type { NextAuthConfig } from 'next-auth'
import Credentials from 'next-auth/providers/credentials'

export const authConfig = {
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        username: { label: 'Username', type: 'text', placeholder: 'demo' },
        password: { label: 'Password', type: 'password', placeholder: 'demo' },
      },
      async authorize(credentials) {
        // PD1 Demo Mock Login
        if (credentials?.username === 'demo' && credentials?.password === 'demo') {
          return { id: '1', name: 'Demo User', email: 'demo@example.com' }
        }
        return null
      },
    }),
  ],
  pages: { signIn: '/login' },
} satisfies NextAuthConfig
