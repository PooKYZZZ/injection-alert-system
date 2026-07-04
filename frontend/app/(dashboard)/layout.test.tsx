import { beforeEach, describe, expect, it, vi } from 'vitest'

import { PERMISSIONS } from '@/lib/auth/roles'

const layoutHarness = vi.hoisted(() => ({
  getSession: vi.fn(),
  redirect: vi.fn(),
  requirePermission: vi.fn(),
}))

vi.mock('@/lib/auth-session', () => ({
  getSession: layoutHarness.getSession,
}))

vi.mock('@/lib/auth/route-guard', () => ({
  requirePermission: layoutHarness.requirePermission,
}))

vi.mock('next/navigation', () => ({
  redirect: layoutHarness.redirect,
}))

const session = {
  user: {
    id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
    email: 'analyst@example.test',
    role: 'ANALYST',
    authz_version: 1,
  },
  expires: '2099-01-01T00:00:00.000Z',
}

describe('DashboardLayout', () => {
  beforeEach(() => {
    layoutHarness.getSession.mockReset()
    layoutHarness.redirect.mockReset()
    layoutHarness.requirePermission.mockReset()
  })

  it('requires current DB-backed account state before rendering', async () => {
    layoutHarness.getSession.mockResolvedValue(session)
    layoutHarness.requirePermission.mockResolvedValue({ ok: true })
    const { default: DashboardLayout } = await import('./layout')

    await DashboardLayout({ children: <div>dashboard</div> })

    expect(layoutHarness.requirePermission).toHaveBeenCalledWith(
      session,
      PERMISSIONS.ALERTS_READ
    )
    expect(layoutHarness.redirect).not.toHaveBeenCalled()
  })

  it('redirects a stale or disabled session to login', async () => {
    layoutHarness.getSession.mockResolvedValue(session)
    layoutHarness.requirePermission.mockResolvedValue({
      ok: false,
      response: new Response(null, { status: 401 }),
    })
    layoutHarness.redirect.mockImplementation(() => {
      throw new Error('NEXT_REDIRECT')
    })
    const { default: DashboardLayout } = await import('./layout')

    await expect(
      DashboardLayout({ children: <div>dashboard</div> })
    ).rejects.toThrow('NEXT_REDIRECT')
    expect(layoutHarness.redirect).toHaveBeenCalledWith('/login')
  })
})
