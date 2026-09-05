export const ROLES = {
  OWNER: 'OWNER',
  ADMIN: 'ADMIN',
  ANALYST: 'ANALYST',
  VIEWER: 'VIEWER',
} as const

export type UserRole = (typeof ROLES)[keyof typeof ROLES]

/** Lowest to highest privilege. Keep authorization decisions permission-based. */
export const ROLE_HIERARCHY = [
  ROLES.VIEWER,
  ROLES.ANALYST,
  ROLES.ADMIN,
  ROLES.OWNER,
] as const

export const ROLE_VALUES = [
  ROLES.OWNER,
  ROLES.ADMIN,
  ROLES.ANALYST,
  ROLES.VIEWER,
] as const

export const PERMISSIONS = {
  ALERTS_READ: 'alerts:read',
  ALERTS_TRIAGE: 'alerts:triage',
  ALERTS_ACTION_UPDATE: 'alerts:action:update',
  STATS_READ: 'stats:read',
  ML_HEALTH_READ: 'ml-health:read',
  ML_MODEL_READ: 'ml-model:read',
  ML_MODEL_RUN: 'ml-model:run',
  ML_MODEL_APPROVE: 'ml-model:approve',
  ML_MODEL_DEPLOY: 'ml-model:deploy',
  ACCOUNTS_READ: 'accounts:read',
  ACCOUNTS_MANAGE: 'accounts:manage',
  MFA_ENROLLMENT: 'mfa:enrollment',
} as const

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS]

export const ROLE_PERMISSIONS: Readonly<Record<UserRole, ReadonlySet<Permission>>> = {
  [ROLES.VIEWER]: new Set([
    PERMISSIONS.ALERTS_READ,
    PERMISSIONS.STATS_READ,
  ]),
  [ROLES.ANALYST]: new Set([
    PERMISSIONS.ALERTS_READ,
    PERMISSIONS.ALERTS_TRIAGE,
    PERMISSIONS.STATS_READ,
    PERMISSIONS.MFA_ENROLLMENT,
  ]),
  [ROLES.ADMIN]: new Set([
    PERMISSIONS.ALERTS_READ,
    PERMISSIONS.ALERTS_TRIAGE,
    PERMISSIONS.ALERTS_ACTION_UPDATE,
    PERMISSIONS.STATS_READ,
    PERMISSIONS.ACCOUNTS_READ,
    PERMISSIONS.ACCOUNTS_MANAGE,
    PERMISSIONS.MFA_ENROLLMENT,
  ]),
  [ROLES.OWNER]: new Set(Object.values(PERMISSIONS)),
}

export function isUserRole(value: unknown): value is UserRole {
  return typeof value === 'string' && ROLE_VALUES.includes(value as UserRole)
}

export function roleHasPermission(
  role: unknown,
  permission: Permission
): boolean {
  return isUserRole(role) && ROLE_PERMISSIONS[role].has(permission)
}

export function roleLabel(role: unknown): string {
  if (role === ROLES.OWNER) return 'Owner'
  if (role === ROLES.ADMIN) return 'Admin'
  if (role === ROLES.ANALYST) return 'Analyst'
  return 'Viewer'
}

export function roleRequiresMfa(role: unknown): boolean {
  return isUserRole(role) && role !== ROLES.VIEWER
}

export function roleAtLeast(role: unknown, minimumRole: UserRole): boolean {
  if (!isUserRole(role)) return false
  return ROLE_HIERARCHY.indexOf(role) >= ROLE_HIERARCHY.indexOf(minimumRole)
}

export function rolesAssignableBy(actorRole: unknown): readonly UserRole[] {
  if (actorRole === ROLES.OWNER) return ROLE_HIERARCHY
  if (actorRole === ROLES.ADMIN) {
    return [ROLES.VIEWER, ROLES.ANALYST, ROLES.ADMIN]
  }
  return []
}

export function canManageAccount(
  actorRole: unknown,
  targetRole: unknown
): boolean {
  if (!roleHasPermission(actorRole, PERMISSIONS.ACCOUNTS_MANAGE)) return false
  if (targetRole === ROLES.OWNER && actorRole !== ROLES.OWNER) return false
  return isUserRole(targetRole)
}
