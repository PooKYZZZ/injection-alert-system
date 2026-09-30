import { NextRequest } from 'next/server'
import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  auth: vi.fn(),
  requirePermission: vi.fn(),
  updateAlertAction: vi.fn(),
}))

vi.mock('@/auth', () => ({ auth: harness.auth }))
vi.mock('@/lib/auth/route-guard', () => ({
  requirePermission: harness.requirePermission,
}))
vi.mock('@/lib/bff-client', () => ({
  updateAlertAction: harness.updateAlertAction,
}))

describe('alert action BFF route', () => {
  beforeEach(() => vi.clearAllMocks())

  it('uses the authenticated session actor instead of a body-supplied actor', async () => {
    harness.auth.mockResolvedValue({ user: { id: 'analyst-42', role: 'ANALYST' } })
    harness.requirePermission.mockResolvedValue({ ok: true })
    harness.updateAlertAction.mockResolvedValue({ ok: true, data: { alert_id: '8' } })
    const { PATCH } = await import('./route')

    const response = await PATCH(
      new NextRequest('http://localhost/api/alerts/8/action', {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ action_taken: 'BLOCKED', actor_id: 'attacker' }),
      }),
      { params: Promise.resolve({ id: '8' }) }
    )

    expect(response.status).toBe(200)
    expect(harness.updateAlertAction).toHaveBeenCalledWith('8', 'BLOCKED', 'analyst-42')
  })

  it('does not update an action when permission checks deny the session', async () => {
    harness.auth.mockResolvedValue({ user: { id: 'analyst-42', role: 'ANALYST' } })
    harness.requirePermission.mockResolvedValue({
      ok: false,
      response: Response.json(
        { error: { code: 'FORBIDDEN', message: 'Forbidden.' } },
        { status: 403 }
      ),
    })
    const { PATCH } = await import('./route')

    const response = await PATCH(
      new NextRequest('http://localhost/api/alerts/8/action', {
        method: 'PATCH',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ action_taken: 'BLOCKED' }),
      }),
      { params: Promise.resolve({ id: '8' }) }
    )

    expect(response.status).toBe(403)
    expect(harness.updateAlertAction).not.toHaveBeenCalled()
  })
})
