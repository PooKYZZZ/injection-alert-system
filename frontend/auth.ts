import NextAuth from 'next-auth'
import Credentials from 'next-auth/providers/credentials'
import { authConfig } from './auth.config'

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,
  // Override providers with the full Node-runtime implementation that includes authorize().
  // The spread above contributes `pages`; this key shadows the edge-safe providers array.
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        password: { label: 'Password', type: 'password', placeholder: '' },
      },
      async authorize(credentials) {
        const demoPassword =
          process.env.SOC_DEMO_PASSWORD ??
          process.env.DEMO_PASSWORD ??
          (process.env.NODE_ENV === 'development' ? 'demo1234' : undefined)
        if (
          typeof credentials?.password === 'string' &&
          credentials.password.length > 0 &&
          credentials.password === demoPassword
        ) {
          return { id: '1', name: 'SOC Analyst', email: 'soc@example.com' }
        }
        return null
      },
    }),
  ],
  session: {
    strategy: 'jwt',
    maxAge: 8 * 60 * 60, // 8 hours
  },
  callbacks: {
    jwt({ token, user }) {
      // On initial sign-in `user` is populated; on subsequent calls only `token` is.
      if (user?.id) token.id = user.id
      return token
    },
    session({ session, token }) {
      // token.id is typed as `unknown` by TypeScript because DefaultJWT carries a
      // Record<string, unknown> index signature that widens augmented properties in
      // this callback context. The typeof guard narrows it to string without a cast.
      if (typeof token.id === 'string') session.user.id = token.id
      return session
    },
  },
})
