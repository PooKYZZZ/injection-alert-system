import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  rpc: vi.fn(),
  from: vi.fn(),
  hashPassword: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('./client', () => ({
  getSupabaseServerClient: () => ({ rpc: harness.rpc, from: harness.from }),
}))
vi.mock('@/lib/auth/password-hash', () => ({
  PASSWORD_HASH_CONCURRENCY_LIMIT: 2,
  hashPassword: harness.hashPassword,
  validateNewPassword: (password: unknown) =>
    typeof password === 'string' && password.length >= 15
      ? { ok: true }
      : { ok: false, code: 'PASSWORD_TOO_SHORT' },
}))

import {
  AccountManagementError,
  changeManagedAccountRole,
  completeInitialPasswordSetup,
  createManagedAccount,
  listManagedAccounts,
} from './account-management'

const actorId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'

describe('account management database boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_APP_ORIGIN = 'https://dashboard.example.test'
    harness.hashPassword.mockResolvedValue('$argon2id$approved')
  })

  it('lists only safe account fields and derives MFA status', async () => {
    const rows = [
      {
        id: actorId,
        email: 'admin@example.test',
        pending_email: null,
        name: 'SOC Admin',
        role: 'ADMIN',
        mfa_required: true,
        email_verified_at: '2026-07-10T00:00:00Z',
        disabled_at: null,
        created_at: '2026-07-01T00:00:00Z',
        auth_mfa_factors: [{ status: 'verified' }],
      },
    ]
    const order = vi.fn().mockResolvedValue({ data: rows, error: null })
    const select = vi.fn((_fields: string) => ({ order }))
    harness.from.mockReturnValue({ select })

    await expect(listManagedAccounts()).resolves.toEqual([
      {
        id: actorId,
        display_name: 'SOC Admin',
        email: 'admin@example.test',
        pending_email: null,
        role: 'ADMIN',
        enabled: true,
        email_verified: true,
        mfa_status: 'active',
        created_at: '2026-07-01T00:00:00Z',
      },
    ])
    expect(select.mock.calls[0][0]).not.toContain('password_hash')
    expect(select.mock.calls[0][0]).not.toContain('secret')
  })

  it('creates a pending account and queues setup without accepting a password', async () => {
    harness.rpc.mockResolvedValue({ data: actorId, error: null })

    const result = await createManagedAccount(actorId, {
      email: 'new@example.test',
      display_name: 'New Analyst',
      role: 'ANALYST',
    })

    expect(result).toEqual({ account_id: actorId })
    expect(harness.rpc).toHaveBeenCalledTimes(1)
    const [name, params] = harness.rpc.mock.calls[0] as unknown as [
      string,
      Record<string, string>,
    ]
    expect(name).toBe('admin_create_auth_account')
    expect(params).toMatchObject({
      p_actor_account_id: actorId,
      p_email: 'new@example.test',
      p_name: 'New Analyst',
      p_role: 'ANALYST',
    })
    expect(params.p_setup_token_hash).toMatch(/^[a-f0-9]{64}$/)
    expect(params.p_setup_url).toMatch(
      /^https:\/\/dashboard\.example\.test\/setup-password\?token=/
    )
    expect(JSON.stringify(result)).not.toContain('token')
  })

  it('validates and hashes a setup password before atomic token consumption', async () => {
    harness.rpc
      .mockResolvedValueOnce({ data: true, error: null })
      .mockResolvedValueOnce({ data: actorId, error: null })

    await expect(
      completeInitialPasswordSetup('opaque-token', 'short')
    ).rejects.toThrow('Password does not meet policy.')
    expect(harness.rpc).not.toHaveBeenCalled()

    await expect(
      completeInitialPasswordSetup(
        'opaque-token',
        'correct horse battery staple'
      )
    ).resolves.toEqual({ account_id: actorId })
    expect(harness.hashPassword).toHaveBeenCalledWith(
      'correct horse battery staple'
    )
    expect(harness.rpc).toHaveBeenCalledWith(
      'consume_password_setup_token',
      {
        p_token_hash: expect.stringMatching(/^[a-f0-9]{64}$/),
        p_password_hash: '$argon2id$approved',
      }
    )
  })

  it('does not hash an invalid setup token after cheap preflight', async () => {
    harness.rpc.mockResolvedValue({ data: false, error: null })

    await expect(
      completeInitialPasswordSetup(
        'a'.repeat(43),
        'correct horse battery staple'
      )
    ).rejects.toMatchObject({ code: 'INVALID_REQUEST' })
    expect(harness.hashPassword).not.toHaveBeenCalled()
    expect(harness.rpc).toHaveBeenCalledWith(
      'preflight_password_token_v61',
      expect.objectContaining({ p_purpose: 'password_setup' })
    )
  })

  it('classifies malformed account ids as invalid requests', async () => {
    await expect(
      changeManagedAccountRole(actorId, 'not-a-uuid', { role: 'VIEWER' })
    ).rejects.toMatchObject({
      code: 'INVALID_REQUEST',
    } satisfies Partial<AccountManagementError>)
    expect(harness.rpc).not.toHaveBeenCalled()
  })
})
