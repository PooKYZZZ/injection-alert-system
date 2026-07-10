import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { PERMISSIONS, ROLES } from './roles'
import {
  requireMfaEnrollmentPermission,
  requireMfaPermission,
  requirePermission,
  requireRecentTotpAdmin,
} from './route-guard'

const guardHarness = vi.hoisted(() => ({
  getAccount: vi.fn(),
}))

vi.mock('../server/db/auth-accounts', () => ({
  getAccountForSessionFreshness: guardHarness.getAccount,
}))

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'

function currentAccount(
  overrides: Partial<{
    id: string
    role: 'ADMIN' | 'ANALYST' | 'VIEWER'
    authzVersion: number
    mfaRequired: boolean
    disabledAt: string | null
  }> = {}
) {
  return {
    id: accountId,
    role: ROLES.ANALYST,
    authzVersion: 1,
    mfaRequired: false,
    disabledAt: null,
    ...overrides,
  }
}

function session(
  role: string = ROLES.ANALYST,
  authzVersion = 1,
  authClaims: Record<string, unknown> = {}
) {
  return {
    user: {
      id: accountId,
      email: 'analyst@example.test',
      role,
      authz_version: authzVersion,
      ...authClaims,
    },
    expires: '2099-01-01T00:00:00.000Z',
  }
}

async function expectGenericUnauthorized(
  result: Awaited<ReturnType<typeof requirePermission>>
): Promise<void> {
  expect(result.ok).toBe(false)
  if (!result.ok) {
    expect(result.response.status).toBe(401)
    expect(await result.response.json()).toEqual({
      error: { code: 'UNAUTHORIZED', message: 'Unauthorized.' },
    })
  }
}

describe('requirePermission', () => {
  beforeEach(() => {
    guardHarness.getAccount.mockReset()
    guardHarness.getAccount.mockResolvedValue(currentAccount())
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('returns 401 when no session exists without querying the database', async () => {
    await expectGenericUnauthorized(
      await requirePermission(null, PERMISSIONS.ALERTS_READ)
    )
    expect(guardHarness.getAccount).not.toHaveBeenCalled()
  })

  it('returns 403 when the session role is missing or invalid', async () => {
    for (const role of [undefined, 'OWNER']) {
      const currentSession = session() as {
        user: Record<string, unknown>
        expires: string
      }
      currentSession.user.role = role

      const result = await requirePermission(
        currentSession,
        PERMISSIONS.ALERTS_READ
      )

      expect(result.ok).toBe(false)
      if (!result.ok) {
        expect(result.response.status).toBe(403)
        expect(await result.response.json()).toEqual({
          error: { code: 'FORBIDDEN', message: 'Forbidden.' },
        })
      }
    }
  })

  it('allows a matching DB account with the required permission', async () => {
    await expect(
      requirePermission(session(), PERMISSIONS.ALERTS_TRIAGE)
    ).resolves.toEqual({ ok: true })
    expect(guardHarness.getAccount).toHaveBeenCalledWith(accountId)
  })

  it('returns 403 when the current role lacks the permission', async () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)
    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ role: ROLES.VIEWER })
    )

    const result = await requirePermission(
      session(ROLES.VIEWER),
      PERMISSIONS.ALERTS_TRIAGE
    )

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.response.status).toBe(403)
    }
    expect(JSON.parse(String(log.mock.calls[0][0]))).toMatchObject({
      event: 'auth.rbac_forbidden',
      outcome: 'denied',
      reason_code: 'PERMISSION_DENIED',
    })
  })

  it('denies a stale authz_version', async () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)

    const result = await requirePermission(
      session(ROLES.ANALYST, 2),
      PERMISSIONS.ALERTS_READ
    )

    await expectGenericUnauthorized(result)
    expect(JSON.parse(String(log.mock.calls[0][0]))).toMatchObject({
      event: 'auth.session_stale',
      outcome: 'denied',
      reason_code: 'AUTHZ_VERSION_MISMATCH',
    })
  })

  it('denies a deleted DB account', async () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)
    guardHarness.getAccount.mockResolvedValue(undefined)

    const result = await requirePermission(
      session(),
      PERMISSIONS.ALERTS_READ
    )

    await expectGenericUnauthorized(result)
    expect(JSON.parse(String(log.mock.calls[0][0]))).toMatchObject({
      event: 'auth.account_removed',
      outcome: 'denied',
      reason_code: 'ACCOUNT_REMOVED',
    })
  })

  it('denies an account disabled after its JWT was issued', async () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)
    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ disabledAt: '2026-07-04T00:00:00Z' })
    )

    const result = await requirePermission(
      session(),
      PERMISSIONS.ALERTS_READ
    )

    await expectGenericUnauthorized(result)
    expect(JSON.parse(String(log.mock.calls[0][0]))).toMatchObject({
      event: 'auth.account_disabled',
      outcome: 'denied',
      reason_code: 'ACCOUNT_DISABLED',
    })
  })

  it('denies an account that starts requiring MFA after login', async () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)
    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ mfaRequired: true })
    )

    const result = await requirePermission(
      session(),
      PERMISSIONS.ALERTS_READ
    )

    await expectGenericUnauthorized(result)
    expect(JSON.parse(String(log.mock.calls[0][0]))).toMatchObject({
      event: 'auth.mfa_required',
      outcome: 'denied',
      reason_code: 'MFA_REQUIRED',
    })
  })

  it('denies a role downgrade after the JWT was issued', async () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)
    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ role: ROLES.VIEWER })
    )

    const result = await requirePermission(
      session(),
      PERMISSIONS.ALERTS_READ
    )

    await expectGenericUnauthorized(result)
    expect(JSON.parse(String(log.mock.calls[0][0]))).toMatchObject({
      event: 'auth.role_mismatch',
      outcome: 'denied',
      reason_code: 'ROLE_MISMATCH',
    })
  })

  it('denies an account id mismatch', async () => {
    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ id: 'e1684968-b911-482d-9781-78c82dd7edeb' })
    )

    await expectGenericUnauthorized(
      await requirePermission(session(), PERMISSIONS.ALERTS_READ)
    )
  })

  it('fails closed when the DB freshness query fails', async () => {
    const log = vi.spyOn(console, 'info').mockImplementation(() => undefined)
    guardHarness.getAccount.mockRejectedValue(
      new Error('raw Supabase connection details')
    )

    const result = await requirePermission(
      session(),
      PERMISSIONS.ALERTS_READ
    )

    await expectGenericUnauthorized(result)
    expect(JSON.parse(String(log.mock.calls[0][0]))).toMatchObject({
      event: 'auth.account_lookup_failed',
      outcome: 'denied',
      reason_code: 'ACCOUNT_LOOKUP_FAILED',
    })
    expect(String(log.mock.calls[0][0])).not.toContain('Supabase')
  })

  it('does not let audit logging failure change a denied response', async () => {
    vi.spyOn(console, 'info').mockImplementation(() => {
      throw new Error('logger unavailable')
    })
    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ role: ROLES.VIEWER })
    )

    const result = await requirePermission(
      session(ROLES.VIEWER),
      PERMISSIONS.ALERTS_TRIAGE
    )

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.response.status).toBe(403)
    }
  })

  it('allows an MFA session for an account whose policy requires MFA', async () => {
    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ role: ROLES.ADMIN, mfaRequired: true })
    )

    await expect(
      requireMfaPermission(
        session(ROLES.ADMIN, 1, {
          auth_level: 'mfa',
          auth_method: 'totp',
          auth_time: 1_000,
        }),
        PERMISSIONS.ACCOUNTS_READ
      )
    ).resolves.toEqual({ ok: true })
  })

  it('allows recovery-level sessions only for mandatory TOTP enrollment', async () => {
    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ role: ROLES.ADMIN, mfaRequired: true })
    )
    await expect(
      requireMfaEnrollmentPermission(
        session(ROLES.ADMIN, 1, { auth_level: 'recovery', auth_method: 'backup_code' }),
        PERMISSIONS.ACCOUNTS_READ
      )
    ).resolves.toEqual({ ok: true })
    await expect(
      requireMfaPermission(
        session(ROLES.ANALYST, 1, { auth_level: 'recovery', auth_method: 'backup_code' }),
        PERMISSIONS.ACCOUNTS_READ
      )
    ).resolves.toMatchObject({ ok: false })
  })

  it('requires recent TOTP-authenticated ADMIN for account mutations', async () => {
    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ role: ROLES.ADMIN, mfaRequired: true })
    )
    const recentAdmin = session(ROLES.ADMIN, 1, {
      auth_level: 'mfa',
      auth_method: 'totp',
      auth_time: 1_000,
    })

    await expect(
      requireRecentTotpAdmin(
        recentAdmin,
        PERMISSIONS.ACCOUNTS_MANAGE,
        () => 1_599
      )
    ).resolves.toEqual({ ok: true })

    guardHarness.getAccount.mockResolvedValueOnce(
      currentAccount({ role: ROLES.ANALYST, mfaRequired: true })
    )
    const analystResult = await requireRecentTotpAdmin(
      session(ROLES.ANALYST, 1, {
        auth_level: 'mfa',
        auth_method: 'totp',
        auth_time: 1_000,
      }),
      PERMISSIONS.ACCOUNTS_MANAGE,
      () => 1_001
    )
    expect(analystResult.ok).toBe(false)
    if (!analystResult.ok) expect(analystResult.response.status).toBe(403)

    guardHarness.getAccount.mockResolvedValue(
      currentAccount({ role: ROLES.ADMIN, mfaRequired: true })
    )
    for (const deniedSession of [
      session(ROLES.ADMIN, 1, {
        auth_level: 'password',
        auth_method: 'password',
        auth_time: 1_000,
      }),
      session(ROLES.ADMIN, 1, {
        auth_level: 'mfa',
        auth_method: 'totp',
        auth_time: 1_000,
      }),
    ]) {
      const result = await requireRecentTotpAdmin(
        deniedSession,
        PERMISSIONS.ACCOUNTS_MANAGE,
        () => 1_601
      )
      expect(result.ok).toBe(false)
      if (!result.ok) expect([401, 403]).toContain(result.response.status)
    }
  })
})
