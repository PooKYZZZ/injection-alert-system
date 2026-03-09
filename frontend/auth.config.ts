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
        const demoPassword = process.env.SOC_DEMO_PASSWORD
        // Always fail closed: require the env var to be explicitly set.
        // Deployments without SOC_DEMO_PASSWORD are locked out rather than
        // falling back to a well-known default.
        if (!demoPassword || credentials?.password !== demoPassword) return null
        return { id: '1', name: 'SOC Analyst', email: 'soc@example.com' }
      },
    }),
  ],
  pages: { signIn: '/login' },
} satisfies NextAuthConfig
