import { NextResponse } from 'next/server'

import {
  isUserRole,
  roleHasPermission,
  type Permission,
  type UserRole,
} from './roles'

type GuardSession = {
  user?: {
    id?: unknown
    email?: unknown
    role?: unknown
    authz_version?: unknown
  }
} | null

type RegistryAccount = {
  id: string
  role: UserRole
  authzVersion: number
}

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

function readCurrentAccounts(): RegistryAccount[] | null {
  const rawRegistry = process.env.AUTH_USERS_JSON
  if (!rawRegistry) {
    return null
  }

  try {
    const parsed: unknown = JSON.parse(rawRegistry)
    if (!Array.isArray(parsed)) {
      return null
    }

    const accounts: RegistryAccount[] = []
    for (const value of parsed) {
      if (
        typeof value !== 'object' ||
        value === null ||
        !('id' in value) ||
        typeof value.id !== 'string' ||
        !isUserRole('role' in value ? value.role : undefined) ||
        !('authz_version' in value) ||
        !Number.isInteger(value.authz_version) ||
        (value.authz_version as number) < 1
      ) {
        return null
      }

      accounts.push({
        id: value.id.trim().toLowerCase(),
        role: value.role,
        authzVersion: value.authz_version as number,
      })
    }
    return accounts
  } catch {
    return null
  }
}

export function requirePermission(
  session: GuardSession,
  permission: Permission
): GuardResult {
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

  const currentAccounts = readCurrentAccounts()
  const currentAccount = currentAccounts?.find(
    (account) => account.id === id.trim().toLowerCase()
  )
  if (
    !currentAccount ||
    currentAccount.authzVersion !== authzVersion ||
    currentAccount.role !== role
  ) {
    return denied(401)
  }

  if (!roleHasPermission(role, permission)) {
    return denied(403)
  }

  return { ok: true }
}
