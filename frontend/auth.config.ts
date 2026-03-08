import type { NextAuthConfig } from 'next-auth'
import Credentials from 'next-auth/providers/credentials'

export const authConfig = {
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        username: { label: 'Username', type: 'text', placeholder: 'your-username' },
        password: { label: 'Password', type: 'password', placeholder: '' },
      },
      async authorize(credentials) {
        // PD1 Demo Mock Login
        const demoUsername = process.env.DEMO_USERNAME
        const demoPassword = process.env.DEMO_PASSWORD

        if (
          demoUsername &&
          demoPassword &&
          credentials?.username === demoUsername &&
          credentials?.password === demoPassword
        ) {
          return { id: '1', name: 'Demo User', email: 'demo@example.com' }
        }
        return null
      },
    }),
  ],
  pages: { signIn: '/login' },
} satisfies NextAuthConfig
