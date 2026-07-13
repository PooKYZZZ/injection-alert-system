import fs from 'node:fs'
import path from 'node:path'

import { NextRequest, NextResponse } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  auth: vi.fn(),
  signIn: vi.fn(),
  guard: vi.fn(),
  verify: vi.fn(),
  clearCookie: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('@/auth', () => ({ auth: harness.auth, signIn: harness.signIn }))
vi.mock('@/lib/auth/route-guard', () => ({
  requireMfaChallengePermission: harness.guard,
}))
vi.mock('@/lib/server/db/mfa-challenges', () => ({ verifyMfaLogin: harness.verify }))
vi.mock('@/lib/auth/preauth', () => ({
  readPreAuthHandle: () => 'a'.repeat(43),
  clearPreAuthCookie: harness.clearCookie,
}))

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'

describe('MFA verification route', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_MFA_ENROLLMENT_ENABLED = 'true'
    process.env.AUTH_APP_ORIGIN = 'http://localhost'
    harness.auth.mockResolvedValue({ user: { id: accountId, role: 'ADMIN', auth_level: 'password' } })
    harness.guard.mockResolvedValue({ ok: true })
    harness.verify.mockResolvedValue({ completion_token: 'b'.repeat(43) })
    harness.clearCookie.mockResolvedValue(undefined)
  })

  it('is POST-only and performs server-side Auth.js completion handoff', async () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, 'auth/mfa/verify/route.ts'),
      'utf8'
    )
    expect(source).toContain('signIn')
    expect(source).toContain('readPreAuthHandle')
    expect(source).not.toContain('export async function GET')
    const { POST } = await import('./auth/mfa/verify/route')
    const response = await POST(
      new NextRequest('http://localhost/api/auth/mfa/verify', {
        method: 'POST',
        headers: { origin: 'http://localhost' },
        body: JSON.stringify({ code: '123456' }),
      })
    )
    expect(response.status).toBe(200)
    expect(harness.verify).toHaveBeenCalledWith(accountId, 'a'.repeat(43), '123456')
    expect(harness.signIn).toHaveBeenCalledWith('credentials', expect.objectContaining({
      mfa_completion_token: 'b'.repeat(43),
      redirect: false,
      redirectTo: '/dashboard',
    }))
    expect(harness.clearCookie).toHaveBeenCalled()
  })

  it('rejects a denied challenge before reading the code body', async () => {
    harness.guard.mockResolvedValue({
      ok: false,
      response: NextResponse.json({ error: { code: 'FORBIDDEN' } }, { status: 403 }),
    })
    const { POST } = await import('./auth/mfa/verify/route')
    const json = vi.fn()
    const response = await POST({
      headers: new Headers({ origin: 'http://localhost' }),
      json,
    } as unknown as Request)
    expect(response.status).toBe(403)
    expect(json).not.toHaveBeenCalled()
  })
})
