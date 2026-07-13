import { describe, expect, it } from 'vitest'

import {
  PERMISSIONS,
  ROLES,
  roleHasPermission,
} from './roles'

describe('role permission policy', () => {
  it('keeps role and permission constants stable', () => {
    expect(ROLES).toEqual({
      ADMIN: 'ADMIN',
      ANALYST: 'ANALYST',
      VIEWER: 'VIEWER',
    })
    expect(PERMISSIONS).toEqual({
      ALERTS_READ: 'alerts:read',
      ALERTS_TRIAGE: 'alerts:triage',
      ALERTS_ACTION_UPDATE: 'alerts:action:update',
      STATS_READ: 'stats:read',
      ML_HEALTH_READ: 'ml-health:read',
      ACCOUNTS_READ: 'accounts:read',
      ACCOUNTS_MANAGE: 'accounts:manage',
      MFA_ENROLLMENT: 'mfa:enrollment',
    })
  })

  it('allows VIEWER read permissions only', () => {
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ALERTS_READ)).toBe(true)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.STATS_READ)).toBe(true)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ML_HEALTH_READ)).toBe(true)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ALERTS_TRIAGE)).toBe(false)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ALERTS_ACTION_UPDATE)).toBe(false)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ACCOUNTS_READ)).toBe(false)
  })

  it('allows ANALYST read and triage permissions', () => {
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ALERTS_READ)).toBe(true)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.STATS_READ)).toBe(true)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ML_HEALTH_READ)).toBe(true)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ALERTS_TRIAGE)).toBe(true)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ALERTS_ACTION_UPDATE)).toBe(false)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ACCOUNTS_MANAGE)).toBe(false)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.MFA_ENROLLMENT)).toBe(true)
  })

  it('allows ADMIN every defined permission', () => {
    for (const permission of Object.values(PERMISSIONS)) {
      expect(roleHasPermission(ROLES.ADMIN, permission)).toBe(true)
    }
  })

  it('denies unknown and missing roles', () => {
    expect(roleHasPermission('OWNER', PERMISSIONS.ALERTS_READ)).toBe(false)
    expect(roleHasPermission(undefined, PERMISSIONS.ALERTS_READ)).toBe(false)
  })
})
