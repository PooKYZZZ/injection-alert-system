import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  auth: vi.fn(),
  signIn: vi.fn(),
  guard: vi.fn(),
  readCompletionCookie: vi.fn(),
  clearCompletionCookie: vi.fn(),
  clearPreAuthCookie: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('@/auth', () => ({ auth: harness.auth, signIn: harness.signIn }))
vi.mock('@/lib/auth/route-guard', () => ({
  requireMfaChallengePermission: harness.guard,
}))
vi.mock('@/lib/auth/mfa-completion-cookie', () => ({
  readMfaCompletionCookie: harness.readCompletionCookie,
  clearMfaCompletionCookie: harness.clearCompletionCookie,
}))
vi.mock('@/lib/auth/preauth', () => ({
  clearPreAuthCookie: harness.clearPreAuthCookie,
}))

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
const completionToken = 'a'.repeat(43)

describe('MFA enrollment finalization route', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_MFA_ENROLLMENT_ENABLED = 'true'
    process.env.AUTH_APP_ORIGIN = 'http://localhost'
    harness.auth.mockResolvedValue({
      user: {
        id: accountId,
        role: 'ADMIN',
        auth_level: 'password',
        auth_method: 'password',
        mfa_challenge_purpose: 'mfa_enrollment',
        mfa_challenge_expires_at: '2099-01-01T00:00:00.000Z',
      },
    })
    harness.guard.mockResolvedValue({ ok: true })
    harness.readCompletionCookie.mockReturnValue(completionToken)
  })

  it('passes the completion-handoff exception and clears cookies only after sign-in', async () => {
    const { POST } = await import('./auth/mfa/enroll/finalize/route')
    const response = await POST(
      new NextRequest('http://localhost/api/auth/mfa/enroll/finalize', {
        method: 'POST',
        headers: {
          origin: 'http://localhost',
          cookie: '__Host-cybertrace-mfa-completion=' + completionToken,
        },
      })
    )

    expect(response.status).toBe(200)
    expect(harness.guard).toHaveBeenCalledWith(
      expect.objectContaining({ user: expect.objectContaining({ id: accountId }) }),
      'mfa:enrollment',
      { allowEnrollmentFinalization: true }
    )
    expect(harness.signIn).toHaveBeenCalledWith('credentials', {
      mfa_completion_token: completionToken,
      redirectTo: '/dashboard',
    })
    expect(harness.clearCompletionCookie).toHaveBeenCalledOnce()
    expect(harness.clearPreAuthCookie).toHaveBeenCalledOnce()
  })
})
