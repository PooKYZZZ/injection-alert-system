import fs from 'node:fs'
import path from 'node:path'

import { NextRequest, NextResponse } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  auth: vi.fn(),
  guard: vi.fn(),
  begin: vi.fn(),
  complete: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('@/auth', () => ({ auth: harness.auth }))
vi.mock('@/lib/auth/route-guard', () => ({
  requireMfaEnrollmentPermission: harness.guard,
}))
vi.mock('@/lib/server/db/totp-enrollment', () => ({
  beginTotpEnrollment: harness.begin,
  completeTotpEnrollment: harness.complete,
}))

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'

describe('TOTP enrollment routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_MFA_ENROLLMENT_ENABLED = 'true'
    process.env.AUTH_APP_ORIGIN = 'http://localhost'
    harness.auth.mockResolvedValue({ user: { id: accountId, role: 'ANALYST' } })
    harness.guard.mockResolvedValue({ ok: true })
  })

  it('uses POST-only routes and same-origin protection', async () => {
    for (const route of [
      'auth/mfa/enroll/route.ts',
      'auth/mfa/enroll/verify/route.ts',
    ]) {
      const source = fs.readFileSync(path.resolve(__dirname, route), 'utf8')
      expect(source).toContain('requireTrustedOrigin')
      expect(source).toContain('export async function POST')
      expect(source).not.toContain('export async function GET')
    }
  })

  it('does not begin enrollment when authorization fails', async () => {
    harness.guard.mockResolvedValue({
      ok: false,
      response: NextResponse.json({ error: { code: 'FORBIDDEN' } }, { status: 403 }),
    })
    const { POST } = await import('./auth/mfa/enroll/route')
    const response = await POST(
      new NextRequest('http://localhost/api/auth/mfa/enroll', {
        method: 'POST',
        headers: { origin: 'http://localhost' },
      })
    )
    expect(response.status).toBe(403)
    expect(harness.begin).not.toHaveBeenCalled()
  })

  it('returns enrollment material only after a guarded begin request', async () => {
    harness.begin.mockResolvedValue({
      factor_id: '2c0d7d68-e70d-4f22-9487-57b3df572b6c',
      manual_key: 'JBSWY3DPEHPK3PXP',
      provisioning_uri: 'otpauth://totp/CyberTrace%3Aanalyst%40example.test',
      expires_at: '2026-07-10T00:10:00Z',
    })
    const { POST } = await import('./auth/mfa/enroll/route')
    const response = await POST(
      new NextRequest('http://localhost/api/auth/mfa/enroll', {
        method: 'POST',
        headers: { origin: 'http://localhost' },
      })
    )
    expect(response.status).toBe(200)
    expect(await response.json()).toMatchObject({ manual_key: 'JBSWY3DPEHPK3PXP' })
    expect(harness.begin).toHaveBeenCalledWith(accountId)
  })
})
