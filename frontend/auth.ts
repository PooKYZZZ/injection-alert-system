import NextAuth, { CredentialsSignin } from 'next-auth'
import Credentials from 'next-auth/providers/credentials'
import { authConfig } from './auth.config'
import { writeLoginAudit } from './lib/auth/login-audit'
import {
  loginThrottle,
  passwordHashConcurrencyGate,
} from './lib/auth/login-throttle'
import { verifyPasswordForAccount } from './lib/auth/password-hash'
import { isUserRole, type UserRole } from './lib/auth/roles'
import {
  AUTH_CREDENTIAL_FIELDS,
  parseCredentialMode,
} from './lib/auth/credential-mode'
import { findAuthAccountByIdentifier } from './lib/server/db/auth-accounts'
import {
  beginLoginThrottleAttempt,
  completeLoginThrottleAttempt,
} from './lib/server/db/login-throttle'
import {
  beginLoginMfaChallenge,
  consumeMfaCompletionToken,
} from './lib/server/db/mfa-challenges'
import { setPreAuthCookie } from './lib/auth/preauth'
import { consumeRecoveryCompletionToken } from './lib/server/db/mfa-recovery'
import {
  isTurnstileConfigured,
  isTurnstileEnabled,
  shouldRequireTurnstile,
  verifyTurnstileToken,
} from './lib/auth/turnstile'
// In Next.js, environment variables from .env* are loaded by Next at runtime/build.
// Avoid importing "dotenv" in frontend/shared code since it is a Node-only module
// and will break when bundled for the browser. Rely on `process.env` instead.

const authSecret = process.env.AUTH_SECRET ?? process.env.NEXTAUTH_SECRET
if (!authSecret) {
  throw new Error('AUTH_SECRET or NEXTAUTH_SECRET must be set')
}

class LoginVerificationRequired extends CredentialsSignin {
  code = 'verification_required'
}

function verificationUnavailable(identifierHash: string): never {
  writeLoginAudit({
    event: 'auth.login_challenge_unavailable',
    level: 'error',
    outcome: 'failure',
    identifierHash,
    reasonCode: 'CONFIGURATION_INVALID',
  })
  throw new Error('Login verification is unavailable.')
}

function throwVerificationRequired(identifierHash: string): never {
  if (!isTurnstileConfigured()) return verificationUnavailable(identifierHash)
  writeLoginAudit({
    event: 'auth.login_challenge_required',
    level: 'warn',
    outcome: 'throttled',
    identifierHash,
    reasonCode: 'VERIFICATION_REQUIRED',
  })
  throw new LoginVerificationRequired()
}

async function verifyRequiredTurnstile(
  token: string | undefined,
  identifierHash: string
): Promise<void> {
  if (!isTurnstileConfigured()) return verificationUnavailable(identifierHash)
  if (!token) return throwVerificationRequired(identifierHash)

  const verification = await verifyTurnstileToken(token)
  if (verification.valid) return
  if (verification.reason === 'invalid') {
    writeLoginAudit({
      event: 'auth.login_challenge_rejected',
      level: 'warn',
      outcome: 'failure',
      identifierHash,
      reasonCode: 'TURNSTILE_REJECTED',
    })
    throw new LoginVerificationRequired()
  }
  writeLoginAudit({
    event: 'auth.login_challenge_unavailable',
    level: 'error',
    outcome: 'failure',
    identifierHash,
    reasonCode:
      verification.reason === 'misconfigured'
        ? 'CONFIGURATION_INVALID'
        : 'TURNSTILE_UNAVAILABLE',
  })
  throw new Error('Login verification is unavailable.')
}

async function finishAccountLoginAttempt(
  accountId: string,
  attemptId: string,
  outcome: 'success' | 'failure' | 'abandoned',
  identifierHash: string
) {
  try {
    const result = await completeLoginThrottleAttempt(
      accountId,
      attemptId,
      outcome
    )
    if (!result.completed) throw new Error('Reservation was already consumed.')
    return result
  } catch {
    writeLoginAudit({
      event: 'auth.login_throttle_unavailable',
      level: 'error',
      outcome: 'failure',
      identifierHash,
      reasonCode: 'LOGIN_THROTTLE_UNAVAILABLE',
    })
    throw new Error('Authentication account store unavailable')
  }
}

type VerifiedCompletion = {
  id: string
  name: string
  email: string
  role: UserRole
  authz_version: number
  auth_level: 'mfa' | 'recovery'
  auth_method: 'totp' | 'backup_code' | 'email_otp'
  verified_at: string
  completion_purpose: 'login_mfa' | 'mfa_enrollment' | 'recent_reauthentication' | 'mfa_recovery'
}

function claimsFromVerifiedCompletion(completion: VerifiedCompletion) {
  const verifiedAt = Date.parse(completion.verified_at)
  if (!Number.isFinite(verifiedAt)) {
    throw new Error('Verified completion timestamp is invalid.')
  }
  return {
    id: completion.id,
    name: completion.name,
    email: completion.email,
    role: completion.role,
    authz_version: completion.authz_version,
    auth_level: completion.auth_level,
    auth_method: completion.auth_method,
    auth_time: Math.floor(verifiedAt / 1_000),
    mfa_challenge_purpose: completion.completion_purpose,
  }
}

export const { handlers, auth, signIn, signOut } = NextAuth({
  ...authConfig,

  // Require explicit env-driven auth secret configuration.
  secret: authSecret,

  // Override providers with full Node runtime implementation
  providers: [
    Credentials({
      name: 'Credentials',
      credentials: AUTH_CREDENTIAL_FIELDS,
      async authorize(credentials) {
        const mode = parseCredentialMode(
          credentials as Record<string, unknown> | undefined
        )
        if (!mode) return null
        if (mode.kind === 'mfa_completion') {
          return claimsFromVerifiedCompletion(
            await consumeMfaCompletionToken(mode.token)
          )
        }
        if (mode.kind === 'recovery_completion') {
          return claimsFromVerifiedCompletion(
            await consumeRecoveryCompletionToken(mode.token)
          )
        }
        const { identifier, password, turnstileToken } = mode
        const localAttempt = loginThrottle.check(identifier)

        if (!localAttempt.allowed) {
          writeLoginAudit({
            event: 'auth.login_throttled',
            level: 'warn',
            outcome: 'throttled',
            identifierHash: localAttempt.identifierHash,
            reasonCode: localAttempt.reasonCode,
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
            identifierHash: localAttempt.identifierHash,
            reasonCode: 'ACCOUNT_LOOKUP_FAILED',
          })
          throw new Error('Authentication account store unavailable')
        }

        const turnstileEnabled = isTurnstileEnabled()
        let reservationId: string | null = null
        let failureCount = localAttempt.failureCount
        if (account) {
          let sharedAttempt
          try {
            sharedAttempt = await beginLoginThrottleAttempt(account.id, {
              turnstileEnabled,
              turnstileVerified: false,
            })
          } catch {
            writeLoginAudit({
              event: 'auth.login_throttle_unavailable',
              level: 'error',
              outcome: 'failure',
              identifierHash: localAttempt.identifierHash,
              reasonCode: 'LOGIN_THROTTLE_UNAVAILABLE',
            })
            throw new Error('Authentication account store unavailable')
          }

          if (
            !sharedAttempt.allowed &&
            sharedAttempt.reasonCode === 'VERIFICATION_REQUIRED' &&
            turnstileEnabled
          ) {
            await verifyRequiredTurnstile(
              turnstileToken,
              localAttempt.identifierHash
            )
            try {
              sharedAttempt = await beginLoginThrottleAttempt(account.id, {
                turnstileEnabled: true,
                turnstileVerified: true,
              })
            } catch {
              writeLoginAudit({
                event: 'auth.login_throttle_unavailable',
                level: 'error',
                outcome: 'failure',
                identifierHash: localAttempt.identifierHash,
                reasonCode: 'LOGIN_THROTTLE_UNAVAILABLE',
              })
              throw new Error('Authentication account store unavailable')
            }
          }

          if (!sharedAttempt.allowed) {
            writeLoginAudit({
              event: 'auth.login_throttled',
              level: 'warn',
              outcome: 'throttled',
              identifierHash: localAttempt.identifierHash,
              reasonCode: sharedAttempt.reasonCode,
            })
            return null
          }
          reservationId = sharedAttempt.attemptId
          failureCount = sharedAttempt.failureCount
        } else if (
          turnstileEnabled &&
          shouldRequireTurnstile(localAttempt.failureCount)
        ) {
          await verifyRequiredTurnstile(
            turnstileToken,
            localAttempt.identifierHash
          )
        }

        let verification
        try {
          verification = await passwordHashConcurrencyGate.run(() =>
            verifyPasswordForAccount(password, account?.passwordHash ?? null)
          )
        } catch {
          if (account && reservationId) {
            await finishAccountLoginAttempt(
              account.id,
              reservationId,
              'abandoned',
              localAttempt.identifierHash
            )
          }
          throw new Error('Authentication account store unavailable')
        }
        if (!verification.ok) {
          if (account && reservationId) {
            await finishAccountLoginAttempt(
              account.id,
              reservationId,
              'abandoned',
              localAttempt.identifierHash
            )
          }
          writeLoginAudit({
            event: 'auth.login_throttled',
            level: 'warn',
            outcome: 'throttled',
            identifierHash: localAttempt.identifierHash,
            reasonCode: verification.reasonCode,
          })
          return null
        }

        if (!account || !verification.value || account.disabledAt !== null) {
          if (account && reservationId) {
            const completion = await finishAccountLoginAttempt(
              account.id,
              reservationId,
              'failure',
              localAttempt.identifierHash
            )
            failureCount = completion.failureCount
          } else {
            failureCount = loginThrottle.recordFailure(
              localAttempt.identifierHash
            )
          }
          writeLoginAudit({
            event: 'auth.login_failed',
            level: 'warn',
            outcome: 'failure',
            identifierHash: localAttempt.identifierHash,
            reasonCode: 'INVALID_CREDENTIALS',
          })
          if (
            turnstileEnabled &&
            shouldRequireTurnstile(failureCount)
          ) {
            throwVerificationRequired(localAttempt.identifierHash)
          }
          return null
        }

        if (reservationId) {
          await finishAccountLoginAttempt(
            account.id,
            reservationId,
            'success',
            localAttempt.identifierHash
          )
        }
        loginThrottle.recordSuccess(localAttempt.identifierHash)

        let mfaChallengePurpose:
          | 'login_mfa'
          | 'mfa_enrollment'
          | 'recent_reauthentication'
          | undefined
        let mfaChallengeExpiresAt: string | undefined
        if (account.mfaRequired) {
          try {
            const challenge = await beginLoginMfaChallenge(account.id)
            await setPreAuthCookie(challenge.handle)
            mfaChallengePurpose = challenge.purpose
            mfaChallengeExpiresAt = challenge.expires_at
          } catch {
            writeLoginAudit({
              event: 'auth.account_lookup_failed',
              level: 'error',
              outcome: 'failure',
              identifierHash: localAttempt.identifierHash,
              reasonCode: 'ACCOUNT_LOOKUP_FAILED',
            })
            throw new Error('Authentication account store unavailable')
          }
        }
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
          auth_level: 'password',
          auth_method: 'password',
          auth_time: Math.floor(Date.now() / 1_000),
          mfa_challenge_purpose: mfaChallengePurpose,
          mfa_challenge_expires_at: mfaChallengeExpiresAt,
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
        token.auth_level = user.auth_level
        token.auth_method = user.auth_method
        token.auth_time = user.auth_time
        token.mfa_challenge_purpose = user.mfa_challenge_purpose
        token.mfa_challenge_expires_at = user.mfa_challenge_expires_at
        if (
          user.auth_level === 'password' &&
          typeof user.mfa_challenge_expires_at === 'string'
        ) {
          const challengeExpiry = Math.floor(
            Date.parse(user.mfa_challenge_expires_at) / 1_000
          )
          if (Number.isFinite(challengeExpiry)) {
            token.exp = Math.min(token.exp ?? challengeExpiry, challengeExpiry)
          }
        }
      }
      if (
        token.auth_level === 'password' &&
        typeof token.mfa_challenge_expires_at === 'string'
      ) {
        const challengeExpiry = Math.floor(
          Date.parse(token.mfa_challenge_expires_at) / 1_000
        )
        if (Number.isFinite(challengeExpiry)) {
          token.exp = Math.min(token.exp ?? challengeExpiry, challengeExpiry)
          if (challengeExpiry <= Math.floor(Date.now() / 1_000)) {
            token.exp = 0
          }
        }
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
        if (
          token.auth_level === 'password' ||
          token.auth_level === 'recovery' ||
          token.auth_level === 'mfa'
        ) {
          session.user.auth_level = token.auth_level
        }
        if (
          token.auth_method === 'password' ||
          token.auth_method === 'totp' ||
          token.auth_method === 'backup_code' ||
          token.auth_method === 'email_otp'
        ) {
          session.user.auth_method = token.auth_method
        }
        if (Number.isInteger(token.auth_time)) {
          session.user.auth_time = token.auth_time as number
        }
        if (typeof token.mfa_challenge_expires_at === 'string') {
          session.user.mfa_challenge_expires_at = token.mfa_challenge_expires_at
        }
        if (
          token.mfa_challenge_purpose === 'login_mfa' ||
          token.mfa_challenge_purpose === 'mfa_enrollment' ||
          token.mfa_challenge_purpose === 'recent_reauthentication' ||
          token.mfa_challenge_purpose === 'mfa_recovery'
        ) {
          session.user.mfa_challenge_purpose = token.mfa_challenge_purpose
        }
      }
      return session
    },
  },
})
