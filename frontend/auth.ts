import NextAuth from 'next-auth'
import { authConfig } from './auth.config'

export const { handlers, auth, signIn, signOut } = NextAuth({
      ...authConfig,
      session: { strategy: 'jwt' },
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
