import { describe, expect, it } from 'vitest'

import {
  PERMISSIONS,
  ROLES,
  ROLE_HIERARCHY,
  canManageAccount,
  roleAtLeast,
  roleHasPermission,
  rolesAssignableBy,
} from './roles'

describe('role permission policy', () => {
  it('keeps role and permission constants stable', () => {
    expect(ROLES).toEqual({
      OWNER: 'OWNER',
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
      ML_MODEL_READ: 'ml-model:read',
      ML_MODEL_RUN: 'ml-model:run',
      ML_MODEL_APPROVE: 'ml-model:approve',
      ML_MODEL_DEPLOY: 'ml-model:deploy',
      ACCOUNTS_READ: 'accounts:read',
      ACCOUNTS_MANAGE: 'accounts:manage',
      MFA_ENROLLMENT: 'mfa:enrollment',
    })
  })

  it('allows VIEWER read permissions only', () => {
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ALERTS_READ)).toBe(true)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.STATS_READ)).toBe(true)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ML_HEALTH_READ)).toBe(false)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ML_MODEL_READ)).toBe(false)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ML_MODEL_RUN)).toBe(false)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ALERTS_TRIAGE)).toBe(false)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ALERTS_ACTION_UPDATE)).toBe(false)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.ACCOUNTS_READ)).toBe(false)
  })

  it('allows ANALYST read and triage permissions', () => {
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ALERTS_READ)).toBe(true)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.STATS_READ)).toBe(true)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ML_HEALTH_READ)).toBe(false)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ML_MODEL_READ)).toBe(false)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ML_MODEL_RUN)).toBe(false)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ML_MODEL_APPROVE)).toBe(false)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ALERTS_TRIAGE)).toBe(true)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ALERTS_ACTION_UPDATE)).toBe(false)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.ACCOUNTS_MANAGE)).toBe(false)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.MFA_ENROLLMENT)).toBe(true)
  })

  it('keeps ML permissions exclusive to OWNER', () => {
    for (const role of [ROLES.ADMIN, ROLES.ANALYST, ROLES.VIEWER]) {
      for (const permission of [
        PERMISSIONS.ML_HEALTH_READ,
        PERMISSIONS.ML_MODEL_READ,
        PERMISSIONS.ML_MODEL_RUN,
        PERMISSIONS.ML_MODEL_APPROVE,
        PERMISSIONS.ML_MODEL_DEPLOY,
      ]) {
        expect(roleHasPermission(role, permission)).toBe(false)
      }
    }
    for (const permission of Object.values(PERMISSIONS)) {
      expect(roleHasPermission(ROLES.OWNER, permission)).toBe(true)
    }
  })

  it('denies unknown and missing roles', () => {
    expect(roleHasPermission('NOT_A_ROLE', PERMISSIONS.ALERTS_READ)).toBe(false)
    expect(roleHasPermission(undefined, PERMISSIONS.ALERTS_READ)).toBe(false)
  })

  it('exposes hierarchy and prevents administrators from managing owners', () => {
    expect(ROLE_HIERARCHY).toEqual([ROLES.VIEWER, ROLES.ANALYST, ROLES.ADMIN, ROLES.OWNER])
    expect(roleAtLeast(ROLES.OWNER, ROLES.ADMIN)).toBe(true)
    expect(roleAtLeast(ROLES.ADMIN, ROLES.OWNER)).toBe(false)
    expect(rolesAssignableBy(ROLES.ADMIN)).toEqual([ROLES.VIEWER, ROLES.ANALYST, ROLES.ADMIN])
    expect(rolesAssignableBy(ROLES.OWNER)).toEqual(ROLE_HIERARCHY)
    expect(canManageAccount(ROLES.ADMIN, ROLES.ADMIN)).toBe(true)
    expect(canManageAccount(ROLES.ADMIN, ROLES.OWNER)).toBe(false)
    expect(canManageAccount(ROLES.OWNER, ROLES.OWNER)).toBe(true)
  })
})
