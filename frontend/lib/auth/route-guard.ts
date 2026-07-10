import { NextResponse } from 'next/server'

import { getAccountForSessionFreshness } from '../server/db/auth-accounts'
import { writeLoginAudit } from './login-audit'
import {
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
  }
} | null

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

export async function requirePermission(
  session: GuardSession,
  permission: Permission
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

  if (currentAccount.mfaRequired) {
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

  if (currentAccount.authzVersion !== authzVersion) {
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
