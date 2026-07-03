export const ROLES = {
  ADMIN: 'ADMIN',
  ANALYST: 'ANALYST',
  VIEWER: 'VIEWER',
} as const

export type UserRole = (typeof ROLES)[keyof typeof ROLES]

export const PERMISSIONS = {
  ALERTS_READ: 'alerts:read',
  ALERTS_TRIAGE: 'alerts:triage',
  ALERTS_ACTION_UPDATE: 'alerts:action:update',
  STATS_READ: 'stats:read',
  ML_HEALTH_READ: 'ml-health:read',
} as const

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS]

const ROLE_PERMISSIONS: Readonly<Record<UserRole, ReadonlySet<Permission>>> = {
  [ROLES.VIEWER]: new Set([
    PERMISSIONS.ALERTS_READ,
    PERMISSIONS.STATS_READ,
    PERMISSIONS.ML_HEALTH_READ,
  ]),
  [ROLES.ANALYST]: new Set([
    PERMISSIONS.ALERTS_READ,
    PERMISSIONS.ALERTS_TRIAGE,
    PERMISSIONS.STATS_READ,
    PERMISSIONS.ML_HEALTH_READ,
  ]),
  [ROLES.ADMIN]: new Set(Object.values(PERMISSIONS)),
}

export function isUserRole(value: unknown): value is UserRole {
  return typeof value === 'string' && Object.values(ROLES).includes(value as UserRole)
}

export function roleHasPermission(
  role: unknown,
  permission: Permission
): boolean {
  return isUserRole(role) && ROLE_PERMISSIONS[role].has(permission)
}
