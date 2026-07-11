import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  auth: vi.fn(),
  guard: vi.fn(),
  begin: vi.fn(),
  verify: vi.fn(),
  setCookie: vi.fn(),
  clearCookie: vi.fn(),
  readCookie: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('@/auth', () => ({ auth: harness.auth, signIn: vi.fn() }))
vi.mock('@/lib/auth/route-guard', () => ({
  requireMfaChallengePermission: harness.guard,
}))
vi.mock('@/lib/auth/preauth', () => ({
  generatePreAuthHandle: () => 'a'.repeat(43),
  setPreAuthCookie: harness.setCookie,
  clearPreAuthCookie: harness.clearCookie,
  readPreAuthHandle: harness.readCookie,
}))
vi.mock('@/lib/server/db/mfa-challenges', () => ({
  beginRecentTotpChallenge: harness.begin,
  verifyRecentTotp: harness.verify,
}))

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'

describe('recent TOTP step-up routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_MFA_ENROLLMENT_ENABLED = 'true'
    process.env.AUTH_APP_ORIGIN = 'http://localhost'
    harness.auth.mockResolvedValue({ user: { id: accountId, role: 'ADMIN', auth_level: 'mfa' } })
    harness.guard.mockResolvedValue({ ok: true })
    harness.begin.mockResolvedValue({
      challenge_id: '2c0d7d68-e70d-4f22-9487-57b3df572b6c',
      handle: 'a'.repeat(43),
      purpose: 'recent_reauthentication',
      expires_at: '2026-07-11T02:10:00.000Z',
    })
    harness.verify.mockResolvedValue({ completion_token: 'b'.repeat(43) })
    harness.readCookie.mockReturnValue('a'.repeat(43))
  })

  it('starts a database-bound recent reauthentication challenge', async () => {
    const { POST } = await import('./auth/mfa/step-up/route')
    const response = await POST(new NextRequest('http://localhost/api/auth/mfa/step-up', {
      method: 'POST', headers: { origin: 'http://localhost' },
    }))

    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({
      status: 'challenge_started',
      expires_at: '2026-07-11T02:10:00.000Z',
    })
    expect(harness.begin).toHaveBeenCalledWith(accountId)
    expect(harness.setCookie).toHaveBeenCalledWith('a'.repeat(43))
  })

  it('signs in with the verified completion and constrains redirect targets', async () => {
    const { signIn } = await import('@/auth')
    const { POST } = await import('./auth/mfa/step-up/verify/route')
    const response = await POST(new NextRequest('http://localhost/api/auth/mfa/step-up/verify', {
      method: 'POST',
      headers: { origin: 'http://localhost', cookie: '__Host-cybertrace-preauth=' + 'a'.repeat(43) },
      body: JSON.stringify({ code: '123456', redirect_to: 'https://evil.example/' }),
    }))

    expect(response.status).toBe(200)
    expect(harness.verify).toHaveBeenCalledWith(accountId, 'a'.repeat(43), '123456')
    expect(signIn).toHaveBeenCalledWith('credentials', {
      mfa_completion_token: 'b'.repeat(43),
      redirectTo: '/dashboard',
    })
    expect(harness.clearCookie).toHaveBeenCalled()
  })
})
