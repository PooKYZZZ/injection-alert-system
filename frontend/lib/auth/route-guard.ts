import { NextResponse } from 'next/server'

import { getAccountForSessionFreshness } from '../server/db/auth-accounts'
import { hasActiveMfaEnrollmentChallenge } from '../server/db/mfa-challenges'
import { writeLoginAudit } from './login-audit'
import {
  PERMISSIONS,
  isUserRole,
  roleHasPermission,
  type Permission,
} from './roles'

type GuardSession = {
  user?: {
    id?: unknown
    email?: unknown
    role?: unknown
    authz_version?: unknown
    auth_level?: unknown
    auth_method?: unknown
    auth_time?: unknown
    mfa_challenge_purpose?: unknown
    mfa_challenge_expires_at?: unknown
  }
} | null

type MfaChallengePermissionOptions = Readonly<{
  allowEnrollmentFinalization?: boolean
  allowRecoveryFinalization?: boolean
}>

type GuardResult =
  | { ok: true }
  | { ok: false; response: Response }

function denied(status: 401 | 403): GuardResult {
  const unauthorized = status === 401
  return {
    ok: false,
    response: NextResponse.json(
      {
        error: {
          code: unauthorized ? 'UNAUTHORIZED' : 'FORBIDDEN',
          message: unauthorized ? 'Unauthorized.' : 'Forbidden.',
        },
      },
      { status }
    ),
  }
}

async function requirePermissionAtLevels(
  session: GuardSession,
  permission: Permission,
  allowedMfaLevels: readonly ('password' | 'mfa' | 'recovery')[] = ['mfa'],
  allowEnrollmentFinalization = false,
  allowRecoveryFinalization = false
): Promise<GuardResult> {
  if (!session) {
    return denied(401)
  }

  const role = session.user?.role
  if (!isUserRole(role)) {
    return denied(403)
  }

  const id = session.user?.id
  const authzVersion = session.user?.authz_version
  if (
    typeof id !== 'string' ||
    !Number.isInteger(authzVersion) ||
    (authzVersion as number) < 1
  ) {
    return denied(401)
  }

  let currentAccount
  try {
    currentAccount = await getAccountForSessionFreshness(id)
  } catch {
    writeLoginAudit({
      event: 'auth.account_lookup_failed',
      level: 'warn',
      outcome: 'denied',
      userId: id,
      role,
      authzVersion: authzVersion as number,
      reasonCode: 'ACCOUNT_LOOKUP_FAILED',
    })
    return denied(401)
  }

  if (!currentAccount || currentAccount.id !== id.trim().toLowerCase()) {
    writeLoginAudit({
      event: 'auth.account_removed',
      level: 'warn',
      outcome: 'denied',
      userId: id,
      role,
      authzVersion: authzVersion as number,
      reasonCode: 'ACCOUNT_REMOVED',
    })
    return denied(401)
  }

  if (currentAccount.disabledAt !== null) {
    writeLoginAudit({
      event: 'auth.account_disabled',
      level: 'warn',
      outcome: 'denied',
      userId: id,
      role,
      authzVersion: authzVersion as number,
      reasonCode: 'ACCOUNT_DISABLED',
    })
    return denied(401)
  }

  if (
    currentAccount.mfaRequired &&
    !allowedMfaLevels.includes(
      session.user?.auth_level as 'password' | 'mfa' | 'recovery'
    )
  ) {
    writeLoginAudit({
      event: 'auth.mfa_required',
      level: 'warn',
      outcome: 'denied',
      userId: id,
      role,
      authzVersion: authzVersion as number,
      reasonCode: 'MFA_REQUIRED',
    })
    return denied(401)
  }

  const passwordChallengeIsActive =
    session.user?.auth_level === 'password' &&
    session.user?.auth_method === 'password' &&
    typeof session.user?.mfa_challenge_expires_at === 'string' &&
    Number.isFinite(Date.parse(session.user.mfa_challenge_expires_at)) &&
    Date.parse(session.user.mfa_challenge_expires_at) > Date.now()
  const canFinalizeEnrollment =
    allowEnrollmentFinalization &&
    permission === PERMISSIONS.MFA_ENROLLMENT &&
    passwordChallengeIsActive &&
    session.user?.mfa_challenge_purpose === 'mfa_enrollment'
  const canFinalizeRecovery =
    allowRecoveryFinalization &&
    permission === PERMISSIONS.MFA_ENROLLMENT &&
    passwordChallengeIsActive &&
    (session.user?.mfa_challenge_purpose === 'login_mfa' ||
      session.user?.mfa_challenge_purpose === 'mfa_enrollment')

  if (
    currentAccount.authzVersion !== authzVersion &&
    !canFinalizeEnrollment &&
    !canFinalizeRecovery
  ) {
    writeLoginAudit({
      event: 'auth.session_stale',
      level: 'warn',
      outcome: 'denied',
      userId: id,
      role,
      authzVersion: authzVersion as number,
      reasonCode: 'AUTHZ_VERSION_MISMATCH',
    })
    return denied(401)
  }

  if (currentAccount.role !== role) {
    writeLoginAudit({
      event: 'auth.role_mismatch',
      level: 'warn',
      outcome: 'denied',
      userId: id,
      role,
      authzVersion: authzVersion as number,
      reasonCode: 'ROLE_MISMATCH',
    })
    return denied(401)
  }

  if (!roleHasPermission(role, permission)) {
    writeLoginAudit({
      event: 'auth.rbac_forbidden',
      level: 'warn',
      outcome: 'denied',
      userId: id,
      role,
      authzVersion: authzVersion as number,
      reasonCode: 'PERMISSION_DENIED',
    })
    return denied(403)
  }

  return { ok: true }
}

export async function requirePermission(
  session: GuardSession,
  permission: Permission
): Promise<GuardResult> {
  return requirePermissionAtLevels(session, permission, ['mfa'])
}

export async function requireMfaEnrollmentPermission(
  session: GuardSession,
  permission: Permission,
  preAuthHandle?: string | null
): Promise<GuardResult> {
  const authorization = await requirePermissionAtLevels(
    session,
    permission,
    preAuthHandle ? ['password', 'mfa', 'recovery'] : ['mfa', 'recovery']
  )
  if (!authorization.ok) return authorization
  if (session?.user?.auth_level === 'password') {
    if (!preAuthHandle || typeof session.user.id !== 'string') {
      return denied(403)
    }
    try {
      if (!(await hasActiveMfaEnrollmentChallenge(session.user.id, preAuthHandle))) {
        return denied(403)
      }
    } catch {
      return denied(401)
    }
    return { ok: true }
  }
  if (session?.user?.auth_level !== 'mfa' && session?.user?.auth_level !== 'recovery') {
    return denied(403)
  }
  return { ok: true }
}

export async function requireMfaChallengePermission(
  session: GuardSession,
  permission: Permission,
  options: MfaChallengePermissionOptions = {}
): Promise<GuardResult> {
  const authorization = await requirePermissionAtLevels(
    session,
    permission,
    ['password', 'mfa', 'recovery'],
    options.allowEnrollmentFinalization === true,
    options.allowRecoveryFinalization === true
  )
  if (!authorization.ok) return authorization
  if (
    session?.user?.auth_level !== 'password' &&
    session?.user?.auth_level !== 'mfa' &&
    session?.user?.auth_level !== 'recovery'
  ) {
    return denied(403)
  }
  return { ok: true }
}

export async function requireMfaPermission(
  session: GuardSession,
  permission: Permission
): Promise<GuardResult> {
  const authorization = await requirePermission(session, permission)
  if (!authorization.ok) return authorization
  if (
    session?.user?.auth_level !== 'mfa' ||
    session.user.auth_method !== 'totp'
  ) {
    return denied(403)
  }
  return { ok: true }
}

export async function requireRecentTotpAdmin(
  session: GuardSession,
  permission: Permission,
  nowSeconds: () => number = () => Math.floor(Date.now() / 1_000)
): Promise<GuardResult> {
  const authorization = await requireMfaPermission(session, permission)
  if (!authorization.ok) return authorization
  if (session?.user?.role !== 'ADMIN') return denied(403)
  const authTime = session.user.auth_time
  const now = nowSeconds()
  if (
    typeof authTime !== 'number' ||
    !Number.isInteger(authTime) ||
    authTime > now + 30 ||
    now - authTime > 10 * 60
  ) {
    return denied(403)
  }
  return { ok: true }
}
