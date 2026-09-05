import { NextRequest, NextResponse } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  request: vi.fn(),
  complete: vi.fn(),
  auth: vi.fn(),
  guard: vi.fn(),
  resetMfa: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('@/lib/server/db/password-recovery', () => ({
  requestPasswordReset: harness.request,
  completePasswordReset: harness.complete,
  resetManagedAccountMfa: harness.resetMfa,
}))
vi.mock('@/auth', () => ({ auth: harness.auth }))
vi.mock('@/lib/auth/route-guard', () => ({ requireRecentTotp: harness.guard }))

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
const targetId = '2c0d7d68-e70d-4f22-9487-57b3df572b6c'

describe('password recovery routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_PASSWORD_RESET_ENABLED = 'true'
    process.env.AUTH_ACCOUNT_MANAGEMENT_ENABLED = 'true'
    process.env.AUTH_APP_ORIGIN = 'http://localhost'
    harness.request.mockResolvedValue({ status: 'sent' })
    harness.complete.mockResolvedValue({ account_id: accountId })
    harness.auth.mockResolvedValue({ user: { id: accountId, role: 'ADMIN' } })
    harness.guard.mockResolvedValue({ ok: true })
    harness.resetMfa.mockResolvedValue({ status: 'reset' })
  })

  it('keeps forgot-password responses generic', async () => {
    const { POST } = await import('./auth/forgot-password/route')
    const response = await POST(new NextRequest('http://localhost/api/auth/forgot-password', {
      method: 'POST', headers: { origin: 'http://localhost' }, body: JSON.stringify({ email: 'unknown@example.test' }),
    }))
    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ status: 'sent', message: expect.any(String) })
  })

  it('consumes reset only on deliberate POST', async () => {
    const { POST } = await import('./auth/reset-password/route')
    const response = await POST(new NextRequest('http://localhost/api/auth/reset-password', {
      method: 'POST', headers: { origin: 'http://localhost' }, body: JSON.stringify({ token: 'a'.repeat(43), password: 'correct horse battery staple' }),
    }))
    expect(response.status).toBe(200)
    expect(harness.complete).toHaveBeenCalled()
  })

  it('guards ADMIN MFA reset and never allows the route to choose a password', async () => {
    const { POST } = await import('./admin/users/[id]/mfa-reset/route')
    const response = await POST(new NextRequest(`http://localhost/api/admin/users/${targetId}/mfa-reset`, {
      method: 'POST', headers: { origin: 'http://localhost' }, body: JSON.stringify({ reason: 'lost authenticator' }),
    }), { params: Promise.resolve({ id: targetId }) })
    expect(response.status).toBe(200)
    expect(harness.resetMfa).toHaveBeenCalledWith(accountId, targetId, 'lost authenticator')
  })

  it('denies ADMIN MFA reset when recent-auth guard fails', async () => {
    harness.guard.mockResolvedValue({ ok: false, response: NextResponse.json({}, { status: 403 }) })
    const { POST } = await import('./admin/users/[id]/mfa-reset/route')
    const response = await POST({ headers: new Headers({ origin: 'http://localhost' }) } as unknown as Request, { params: Promise.resolve({ id: targetId }) })
    expect(response.status).toBe(403)
    expect(harness.resetMfa).not.toHaveBeenCalled()
  })
})
