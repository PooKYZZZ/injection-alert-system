import type { NextAuthConfig } from 'next-auth'
import Credentials from 'next-auth/providers/credentials'

export const authConfig = {
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        password: { label: 'Password', type: 'password', placeholder: '' },
      },
      async authorize(credentials) {
        const demoPassword = process.env.SOC_DEMO_PASSWORD ?? process.env.DEMO_PASSWORD
        if (credentials?.password === demoPassword) {
          return { id: '1', name: 'SOC Analyst', email: 'soc@example.com' }
        }
        return null
      },
    }),
  ],
  pages: { signIn: '/login' },
} satisfies NextAuthConfig
