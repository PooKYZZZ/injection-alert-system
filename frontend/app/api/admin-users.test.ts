import fs from 'node:fs'
import path from 'node:path'

import { NextRequest, NextResponse } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  auth: vi.fn(),
  requireMfa: vi.fn(),
  requireRecentAdmin: vi.fn(),
  list: vi.fn(),
  create: vi.fn(),
  changeRole: vi.fn(),
  setEnabled: vi.fn(),
  changeEmail: vi.fn(),
  resendSetup: vi.fn(),
  completeSetup: vi.fn(),
  activateEmail: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('@/auth', () => ({ auth: harness.auth }))
vi.mock('@/lib/auth/route-guard', () => ({
  requireMfaPermission: harness.requireMfa,
  requireRecentTotpAdmin: harness.requireRecentAdmin,
}))
vi.mock('@/lib/server/db/account-management', () => ({
  listManagedAccounts: harness.list,
  createManagedAccount: harness.create,
  changeManagedAccountRole: harness.changeRole,
  setManagedAccountEnabled: harness.setEnabled,
  requestManagedEmailChange: harness.changeEmail,
  resendPasswordSetup: harness.resendSetup,
  completeInitialPasswordSetup: harness.completeSetup,
  activateManagedEmail: harness.activateEmail,
}))

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
const session = { user: { id: accountId, role: 'ADMIN' } }

describe('ADMIN user management routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_ACCOUNT_MANAGEMENT_ENABLED = 'true'
    process.env.AUTH_APP_ORIGIN = 'http://localhost'
    harness.auth.mockResolvedValue(session)
    harness.requireMfa.mockResolvedValue({ ok: true })
    harness.requireRecentAdmin.mockResolvedValue({ ok: true })
  })

  it('guards every account-management mutation before reading its body', () => {
    for (const route of [
      'admin/users/route.ts',
      'admin/users/[id]/role/route.ts',
      'admin/users/[id]/status/route.ts',
      'admin/users/[id]/email/route.ts',
      'admin/users/[id]/resend-setup/route.ts',
      'admin/users/[id]/mfa-reset/route.ts',
    ]) {
      const source = fs.readFileSync(path.resolve(__dirname, route), 'utf8')
      expect(source).toContain('requireRecentTotpAdmin')
      expect(source).toMatch(/await\s+requireRecentTotpAdmin\s*\(/)
      expect(source).toContain('requireTrustedOrigin')
    }
  })

  it('guards the User Management page on the server', () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, '../(dashboard)/user-management/page.tsx'),
      'utf8'
    )
    expect(source).toContain('requireMfaPermission')
    expect(source).toContain('listManagedAccounts')
    expect(source).toContain('notFound')
  })

  it('lists only after an ADMIN MFA guard succeeds', async () => {
    harness.list.mockResolvedValue([{ id: accountId, email: 'admin@example.test' }])
    const { GET } = await import('./admin/users/route')

    const response = await GET()

    expect(response.status).toBe(200)
    expect(harness.requireMfa).toHaveBeenCalled()
    expect(await response.json()).toEqual({
      accounts: [{ id: accountId, email: 'admin@example.test' }],
    })
  })

  it('rejects a denied mutation before parsing or calling the database', async () => {
    const denied = NextResponse.json({ error: { code: 'FORBIDDEN' } }, { status: 403 })
    harness.requireRecentAdmin.mockResolvedValue({ ok: false, response: denied })
    const { POST } = await import('./admin/users/route')
    const json = vi.fn()

    const response = await POST({ json } as unknown as NextRequest)

    expect(response.status).toBe(403)
    expect(json).not.toHaveBeenCalled()
    expect(harness.create).not.toHaveBeenCalled()
  })

  it('creates an account without accepting an ADMIN-chosen password', async () => {
    harness.create.mockResolvedValue({ account_id: accountId })
    const { POST } = await import('./admin/users/route')
    const valid = new NextRequest('http://localhost/api/admin/users', {
      method: 'POST',
      headers: { origin: 'http://localhost' },
      body: JSON.stringify({
        email: 'new@example.test',
        display_name: 'New Analyst',
        role: 'ANALYST',
      }),
    })

    const response = await POST(valid)

    expect(response.status).toBe(201)
    expect(harness.create).toHaveBeenCalledWith(accountId, {
      email: 'new@example.test',
      display_name: 'New Analyst',
      role: 'ANALYST',
    })
  })
})

describe('public setup and verification routes', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_ACCOUNT_MANAGEMENT_ENABLED = 'true'
    process.env.AUTH_APP_ORIGIN = 'http://localhost'
  })

  it('rejects cross-site token consumption before reading the request body', async () => {
    const { POST } = await import('./auth/setup-password/route')
    const request = new NextRequest('http://localhost/api/auth/setup-password', {
      method: 'POST',
      headers: { origin: 'https://attacker.example' },
      body: JSON.stringify({
        token: 'opaque-token-that-is-long-enough',
        password: 'correct horse battery staple',
      }),
    })

    const response = await POST(request)

    expect(response.status).toBe(403)
    expect(harness.completeSetup).not.toHaveBeenCalled()
  })

  it('exposes deliberate POST only for scanner-safe setup consumption', async () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, 'auth/setup-password/route.ts'),
      'utf8'
    )
    expect(source).toContain('export async function POST')
    expect(source).not.toContain('export async function GET')

    harness.completeSetup.mockResolvedValue({ account_id: accountId })
    const { POST } = await import('./auth/setup-password/route')
    const response = await POST(
      new NextRequest('http://localhost/api/auth/setup-password', {
        method: 'POST',
        headers: { origin: 'http://localhost' },
        body: JSON.stringify({
          token: 'opaque-token-that-is-long-enough',
          password: 'correct horse battery staple',
        }),
      })
    )

    expect(response.status).toBe(200)
    expect(await response.json()).toEqual({ status: 'password_set' })
  })

  it('uses deliberate POST to activate a verified managed email', async () => {
    const { POST } = await import('./auth/verify-email/route')
    const response = await POST(
      new NextRequest('http://localhost/api/auth/verify-email', {
        method: 'POST',
        headers: { origin: 'http://localhost' },
        body: JSON.stringify({ token: 'opaque-token-that-is-long-enough' }),
      })
    )

    expect(response.status).toBe(200)
    expect(harness.activateEmail).toHaveBeenCalledWith(
      'opaque-token-that-is-long-enough'
    )
  })
})
