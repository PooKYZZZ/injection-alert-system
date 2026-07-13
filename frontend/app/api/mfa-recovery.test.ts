import { NextRequest, NextResponse } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  auth: vi.fn(),
  signIn: vi.fn(),
  guard: vi.fn(),
  backup: vi.fn(),
  requestEmail: vi.fn(),
  verifyEmail: vi.fn(),
  clearPreAuth: vi.fn(),
  clearRecovery: vi.fn(),
  recoveryCookie: null as string | null,
}))

vi.mock('server-only', () => ({}))
vi.mock('@/auth', () => ({ auth: harness.auth, signIn: harness.signIn }))
vi.mock('@/lib/auth/route-guard', () => ({ requireMfaChallengePermission: harness.guard }))
vi.mock('@/lib/server/db/mfa-recovery', () => ({
  consumeBackupCodeForRecovery: harness.backup,
  requestEmailRecovery: harness.requestEmail,
  completeEmailRecovery: harness.verifyEmail,
}))
vi.mock('@/lib/auth/recovery-cookie', () => ({
  setRecoveryCompletionCookie: vi.fn(),
  readRecoveryCompletionCookie: () => harness.recoveryCookie,
  clearRecoveryCompletionCookie: harness.clearRecovery,
}))
vi.mock('@/lib/auth/preauth', () => ({
  clearPreAuthCookie: harness.clearPreAuth,
}))

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'

describe('MFA recovery routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    harness.recoveryCookie = null
    process.env.AUTH_MFA_ENROLLMENT_ENABLED = 'true'
    process.env.AUTH_EMAIL_RECOVERY_ENABLED = 'true'
    process.env.AUTH_APP_ORIGIN = 'http://localhost'
    harness.auth.mockResolvedValue({ user: { id: accountId, role: 'ADMIN', auth_level: 'password' } })
    harness.guard.mockResolvedValue({ ok: true })
    harness.backup.mockResolvedValue({ completion_token: 'b'.repeat(43) })
    harness.requestEmail.mockResolvedValue({ status: 'sent', completion_token: 'c'.repeat(43) })
    harness.verifyEmail.mockResolvedValue({ status: 'verified' })
  })

  it('consumes backup recovery server-side and never returns its completion token', async () => {
    const { POST } = await import('./auth/mfa/recovery/backup/route')
    const response = await POST(new NextRequest('http://localhost/api/auth/mfa/recovery/backup', {
      method: 'POST', headers: { origin: 'http://localhost' }, body: JSON.stringify({ code: 'ABCD-EFGH-JKLM' }),
    }))
    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ status: 'recovery_started' })
    expect(harness.signIn).toHaveBeenCalledWith('credentials', expect.objectContaining({ recovery_completion_token: 'b'.repeat(43), redirect: false }))
    expect(harness.clearRecovery).toHaveBeenCalledOnce()
    expect(harness.clearPreAuth).toHaveBeenCalledOnce()
  })

  it('retries an existing recovery completion cookie without consuming another code', async () => {
    harness.recoveryCookie = 'c'.repeat(43)
    const { POST } = await import('./auth/mfa/recovery/backup/route')
    const response = await POST(new NextRequest('http://localhost/api/auth/mfa/recovery/backup', {
      method: 'POST', headers: { origin: 'http://localhost', cookie: `__Host-cybertrace-recovery=${harness.recoveryCookie}` }, body: JSON.stringify({ code: 'ignored' }),
    }))
    expect(response.status).toBe(200)
    expect(harness.backup).not.toHaveBeenCalled()
    expect(harness.guard).toHaveBeenCalledWith(
      expect.anything(),
      'mfa:enrollment',
      { allowRecoveryFinalization: true }
    )
    expect(harness.signIn).toHaveBeenCalledWith('credentials', expect.objectContaining({ recovery_completion_token: harness.recoveryCookie, redirect: false }))
    expect(harness.clearRecovery).toHaveBeenCalledOnce()
    expect(harness.clearPreAuth).toHaveBeenCalledOnce()
  })

  it('retries email handoff when OTP completion already committed', async () => {
    harness.verifyEmail.mockRejectedValue(new Error('INVALID_CODE'))
    harness.recoveryCookie = 'c'.repeat(43)
    const { POST } = await import('./auth/mfa/recovery/email/verify/route')
    const response = await POST(new NextRequest('http://localhost/api/auth/mfa/recovery/email/verify', {
      method: 'POST', headers: { origin: 'http://localhost', cookie: `__Host-cybertrace-recovery=${harness.recoveryCookie}` }, body: JSON.stringify({ code: '123456' }),
    }))
    expect(response.status).toBe(200)
    expect(harness.guard).toHaveBeenCalledWith(
      expect.anything(),
      'mfa:enrollment',
      { allowRecoveryFinalization: true }
    )
    expect(harness.signIn).toHaveBeenCalledWith('credentials', expect.objectContaining({ recovery_completion_token: harness.recoveryCookie, redirect: false }))
    expect(harness.clearRecovery).toHaveBeenCalledOnce()
    expect(harness.clearPreAuth).toHaveBeenCalledOnce()
  })

  it('denies email recovery before body parsing when the guard fails', async () => {
    harness.guard.mockResolvedValue({ ok: false, response: NextResponse.json({}, { status: 403 }) })
    const { POST } = await import('./auth/mfa/recovery/email/request/route')
    const json = vi.fn()
    const response = await POST({ headers: new Headers({ origin: 'http://localhost' }), json } as unknown as Request)
    expect(response.status).toBe(403)
    expect(json).not.toHaveBeenCalled()
  })

  it('binds email recovery delivery to the authenticated address', async () => {
    harness.auth.mockResolvedValue({
      user: {
        id: accountId,
        email: 'admin@example.test',
        role: 'ADMIN',
        auth_level: 'password',
      },
    })
    const { POST } = await import(
      './auth/mfa/recovery/email/request/route'
    )

    const response = await POST(
      new NextRequest(
        'http://localhost/api/auth/mfa/recovery/email/request',
        { method: 'POST', headers: { origin: 'http://localhost' } }
      )
    )

    expect(response.status).toBe(200)
    expect(harness.requestEmail).toHaveBeenCalledWith(
      accountId,
      'admin@example.test'
    )
  })
})
