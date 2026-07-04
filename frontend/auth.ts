import NextAuth from 'next-auth'
import Credentials from 'next-auth/providers/credentials'
import { authConfig } from './auth.config'
import { writeLoginAudit } from './lib/auth/login-audit'
import {
  loginThrottle,
  passwordHashConcurrencyGate,
} from './lib/auth/login-throttle'
import { verifyPasswordForAccount } from './lib/auth/password-hash'
import { isUserRole } from './lib/auth/roles'
import { findAuthAccountByIdentifier } from './lib/server/db/auth-accounts'
// In Next.js, environment variables from .env* are loaded by Next at runtime/build.
// Avoid importing "dotenv" in frontend/shared code since it is a Node-only module
// and will break when bundled for the browser. Rely on `process.env` instead.

const authSecret = process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET
if (!authSecret) {
  throw new Error('AUTH_SECRET or NEXTAUTH_SECRET must be set')
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,

  // Require explicit env-driven auth secret configuration.
  secret: authSecret,

  // Override providers with full Node runtime implementation
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: {
        identifier: {
          label: 'Email or username',
          type: 'text',
          placeholder: '',
        },
        password: { label: 'Password', type: 'password', placeholder: '' },
      },
      async authorize(credentials) {
        const identifier =
          typeof credentials?.identifier === 'string'
            ? credentials.identifier
            : ''
        const password =
          typeof credentials?.password === 'string' ? credentials.password : ''
        const attempt = loginThrottle.check(identifier)

        if (!attempt.allowed) {
          writeLoginAudit({
            event: 'auth.login_throttled',
            level: 'warn',
            outcome: 'throttled',
            identifierHash: attempt.identifierHash,
            reasonCode: attempt.reasonCode,
          })
          return null
        }

        let account
        try {
          account = await findAuthAccountByIdentifier(identifier)
        } catch {
          writeLoginAudit({
            event: 'auth.account_lookup_failed',
            level: 'error',
            outcome: 'failure',
            identifierHash: attempt.identifierHash,
            reasonCode: 'ACCOUNT_LOOKUP_FAILED',
          })
          return null
        }

        const verification = await passwordHashConcurrencyGate.run(() =>
          verifyPasswordForAccount(password, account?.passwordHash ?? null)
        )
        if (!verification.ok) {
          writeLoginAudit({
            event: 'auth.login_throttled',
            level: 'warn',
            outcome: 'throttled',
            identifierHash: attempt.identifierHash,
            reasonCode: verification.reasonCode,
          })
          return null
        }

        if (
          !account ||
          !verification.value ||
          account.disabledAt !== null ||
          account.mfaRequired
        ) {
          loginThrottle.recordFailure(attempt.identifierHash)
          writeLoginAudit({
            event: 'auth.login_failed',
            level: 'warn',
            outcome: 'failure',
            identifierHash: attempt.identifierHash,
            reasonCode: 'INVALID_CREDENTIALS',
          })
          return null
        }

        loginThrottle.recordSuccess(attempt.identifierHash)
        writeLoginAudit({
          event: 'auth.login_succeeded',
          level: 'info',
          outcome: 'success',
          userId: account.id,
          role: account.role,
          authzVersion: account.authzVersion,
        })
        return {
          id: account.id,
          name: account.name,
          email: account.email,
          role: account.role,
          authz_version: account.authzVersion,
        }
      },
    }),
  ],

  session: {
    strategy: 'jwt',
    maxAge: 8 * 60 * 60, // 8 hours
  },
  jwt: {
    maxAge: 8 * 60 * 60,
  },

  callbacks: {
    jwt({ token, user }) {
      if (user?.id) {
        token.id = user.id
        token.role = user.role
        token.authz_version = user.authz_version
      }
      return token
    },
    session({ session, token }) {
      if (
        typeof token.id === 'string' &&
        isUserRole(token.role) &&
        Number.isInteger(token.authz_version) &&
        (token.authz_version as number) >= 1
      ) {
        session.user.id = token.id
        session.user.role = token.role
        session.user.authz_version = token.authz_version as number
      }
      return session
    },
  },
})
