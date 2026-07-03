import { afterEach, beforeEach, describe, expect, it } from 'vitest'

import { PERMISSIONS, ROLES } from './roles'
import { requirePermission } from './route-guard'

const originalRegistry = process.env.AUTH_USERS_JSON

function setRegistry(
  accounts: Array<{
    id: string
    email: string
    name: string
    role: string
    authz_version: number
  }>
) {
  process.env.AUTH_USERS_JSON = JSON.stringify(accounts)
}

function session(role: string = ROLES.ANALYST, authzVersion = 1) {
  return {
    user: {
      id: 'analyst-1',
      email: 'analyst@example.test',
      role,
      authz_version: authzVersion,
    },
    expires: '2099-01-01T00:00:00.000Z',
  }
}

describe('requirePermission', () => {
  beforeEach(() => {
    setRegistry([
      {
        id: 'analyst-1',
        email: 'analyst@example.test',
        name: 'SOC Analyst',
        role: ROLES.ANALYST,
        authz_version: 1,
      },
    ])
  })

  afterEach(() => {
    if (originalRegistry === undefined) {
      delete process.env.AUTH_USERS_JSON
    } else {
      process.env.AUTH_USERS_JSON = originalRegistry
    }
  })

  it('returns 401 when no session exists', async () => {
    const result = requirePermission(null, PERMISSIONS.ALERTS_READ)

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.response.status).toBe(401)
      expect(await result.response.json()).toEqual({
        error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
      })
    }
  })

  it('returns 403 when the session role is missing or invalid', async () => {
    for (const role of [undefined, 'OWNER']) {
      const currentSession = session() as {
        user: Record<string, unknown>
        expires: string
      }
      currentSession.user.role = role

      const result = requirePermission(currentSession, PERMISSIONS.ALERTS_READ)

      expect(result.ok).toBe(false)
      if (!result.ok) {
        expect(result.response.status).toBe(403)
        expect(await result.response.json()).toEqual({
          error: { code: 'FORBIDDEN', message: 'Forbidden.' },
        })
      }
    }
  })

  it('allows a current session with the required permission', () => {
    expect(requirePermission(session(), PERMISSIONS.ALERTS_TRIAGE)).toEqual({
      ok: true,
    })
  })

  it('returns 403 when the valid role lacks the permission', async () => {
    setRegistry([
      {
        id: 'analyst-1',
        email: 'analyst@example.test',
        name: 'SOC Viewer',
        role: ROLES.VIEWER,
        authz_version: 1,
      },
    ])
    const result = requirePermission(
      session(ROLES.VIEWER),
      PERMISSIONS.ALERTS_TRIAGE
    )

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.response.status).toBe(403)
    }
  })

  it('returns 401 for a stale authz_version', async () => {
    const result = requirePermission(session(ROLES.ANALYST, 0), PERMISSIONS.ALERTS_READ)

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.response.status).toBe(401)
    }
  })

  it('returns 401 when the registry account was removed', async () => {
    setRegistry([])
    const result = requirePermission(session(), PERMISSIONS.ALERTS_READ)

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.response.status).toBe(401)
    }
  })

  it('reads the registry again and catches server-side mutation without refreshing the session', async () => {
    const originalSession = session()
    expect(requirePermission(originalSession, PERMISSIONS.ALERTS_READ)).toEqual({
      ok: true,
    })

    setRegistry([
      {
        id: 'analyst-1',
        email: 'analyst@example.test',
        name: 'SOC Analyst',
        role: ROLES.VIEWER,
        authz_version: 2,
      },
    ])

    const staleResult = requirePermission(originalSession, PERMISSIONS.ALERTS_READ)

    expect(staleResult.ok).toBe(false)
    if (!staleResult.ok) {
      expect(staleResult.response.status).toBe(401)
      expect(await staleResult.response.json()).toEqual({
        error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
      })
    }
  })

  it('returns 401 for a registry role mismatch', async () => {
    setRegistry([
      {
        id: 'analyst-1',
        email: 'analyst@example.test',
        name: 'SOC Analyst',
        role: ROLES.VIEWER,
        authz_version: 1,
      },
    ])

    const result = requirePermission(session(), PERMISSIONS.ALERTS_READ)

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.response.status).toBe(401)
    }
  })
})
