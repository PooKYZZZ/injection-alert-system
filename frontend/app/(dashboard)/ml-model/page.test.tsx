import { describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  getSession: vi.fn(),
  requirePermission: vi.fn(),
  forbidden: vi.fn(),
  redirect: vi.fn(),
}))

vi.mock('@/lib/auth-session', () => ({ getSession: harness.getSession }))
vi.mock('@/lib/auth/route-guard', () => ({ requirePermission: harness.requirePermission }))
vi.mock('next/navigation', () => ({
  forbidden: harness.forbidden,
  redirect: harness.redirect,
}))
vi.mock('@/components/ml-model/MLModelWorkspace', () => ({
  MLModelWorkspace: ({ role }: { role?: string }) => <div data-testid="ml-model-workspace">{role}</div>,
}))

import MLModelPage from './page'

describe('MLModelPage', () => {
  it('renders only for an authorized Owner session', async () => {
    const session = { user: { id: 'owner-1', role: 'OWNER', authz_version: 1 } }
    harness.getSession.mockResolvedValue(session)
    harness.requirePermission.mockResolvedValue({ ok: true })

    const page = await MLModelPage()

    expect(page).toBeTruthy()
    expect(harness.requirePermission).toHaveBeenCalled()
  })

  it.each(['ADMIN', 'ANALYST', 'VIEWER'] as const)(
    'returns 403 through the forbidden boundary for %s',
    async (role) => {
      harness.getSession.mockResolvedValue({
        user: { id: `${role.toLowerCase()}-1`, role, authz_version: 1 },
      })
      harness.requirePermission.mockResolvedValue({
        ok: false,
        response: new Response(null, { status: 403 }),
      })
      harness.forbidden.mockImplementation(() => {
        throw new Error('NEXT_FORBIDDEN')
      })

      await expect(MLModelPage()).rejects.toThrow('NEXT_FORBIDDEN')
    }
  )
})
