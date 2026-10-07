import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import {
  PERMISSIONS,
  ROLES,
  ROLE_HIERARCHY,
  ROLE_PERMISSIONS,
  ROLE_VALUES,
  type UserRole,
  canManageAccount,
  roleAtLeast,
  roleHasPermission,
  rolesAssignableBy,
} from './roles'

describe('role permission policy', () => {
  const parityMatrix = JSON.parse(
    readFileSync(
      resolve(__dirname, '../../../tests/contracts/role-permission-matrix.json'),
      'utf8'
    )
  ) as Record<UserRole, string[]>

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
      TRAINING_FEEDBACK_MANAGE: 'training-feedback:manage',
      STATS_READ: 'stats:read',
      ML_HEALTH_READ: 'ml-health:read',
      ML_MODEL_READ: 'ml-model:read',
      ML_MODEL_RUN: 'ml-model:run',
      ML_MODEL_APPROVE: 'ml-model:approve',
      ML_MODEL_DEPLOY: 'ml-model:deploy',
      ACCOUNTS_READ: 'accounts:read',
      ACCOUNTS_MANAGE: 'accounts:manage',
      MFA_ENROLLMENT: 'mfa:enrollment',
      TRAFFIC_EXPORT: 'traffic:export',
    })
  })

  it('matches the shared backend/frontend permission matrix', () => {
    for (const role of ROLE_VALUES) {
      expect([...ROLE_PERMISSIONS[role]].sort()).toEqual(
        [...parityMatrix[role]].sort()
      )
    }
    expect(Object.values(PERMISSIONS).sort()).toEqual(
      [...new Set(Object.values(parityMatrix).flat())].sort()
    )
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
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.TRAINING_FEEDBACK_MANAGE)).toBe(false)
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

  it('keeps Training Feedback management exclusive to OWNER', () => {
    for (const role of [ROLES.ADMIN, ROLES.ANALYST, ROLES.VIEWER]) {
      expect(roleHasPermission(role, PERMISSIONS.TRAINING_FEEDBACK_MANAGE)).toBe(false)
    }
    expect(roleHasPermission(ROLES.OWNER, PERMISSIONS.TRAINING_FEEDBACK_MANAGE)).toBe(true)
  })

  it('allows only Owner, Admin, and Analyst to export Traffic History', () => {
    expect(roleHasPermission(ROLES.OWNER, PERMISSIONS.TRAFFIC_EXPORT)).toBe(true)
    expect(roleHasPermission(ROLES.ADMIN, PERMISSIONS.TRAFFIC_EXPORT)).toBe(true)
    expect(roleHasPermission(ROLES.ANALYST, PERMISSIONS.TRAFFIC_EXPORT)).toBe(true)
    expect(roleHasPermission(ROLES.VIEWER, PERMISSIONS.TRAFFIC_EXPORT)).toBe(false)
  })

  it('denies unknown and missing roles', () => {
    expect(roleHasPermission('NOT_A_ROLE', PERMISSIONS.ALERTS_READ)).toBe(false)
    expect(roleHasPermission('NOT_A_ROLE', PERMISSIONS.TRAINING_FEEDBACK_MANAGE)).toBe(false)
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
