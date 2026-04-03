import NextAuth from 'next-auth'
import Credentials from 'next-auth/providers/credentials'
import { authConfig } from './auth.config'
// In Next.js, environment variables from .env* are loaded by Next at runtime/build.
// Avoid importing "dotenv" in frontend/shared code since it is a Node-only module
// and will break when bundled for the browser. Rely on `process.env` instead.

// Ensure the secret is defined in the auth configuration (do not log secrets)
const authOptions = {
  secret: process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET ?? 'default-secret-key',
};

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,

  // ✅ REQUIRED: Fixes "MissingSecret" error
  secret: authOptions.secret,

  // Override providers with full Node runtime implementation
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
          (process.env.NODE_ENV === 'development' ? 'demo1234' : undefined);

        if (
          typeof credentials?.password === 'string' &&
          credentials.password.length > 0 &&
          credentials.password === demoPassword
        ) {
          return {
            id: '1',
            name: 'SOC Analyst',
            email: 'soc@example.com',
          };
        }

        return null;
      },
    }),
  ],

  session: {
    strategy: 'jwt',
    maxAge: 8 * 60 * 60, // 8 hours
  },

  callbacks: {
    jwt({ token, user }) {
      if (user?.id) token.id = user.id;
      return token;
    },
    session({ session, token }) {
      if (typeof token.id === 'string') {
        session.user.id = token.id;
      }
      return session;
    },
  },
})