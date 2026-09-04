import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  rpc: vi.fn(),
  from: vi.fn(),
  hashPassword: vi.fn(),
  protect: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('./client', () => ({
  getSupabaseServerClient: () => ({ rpc: harness.rpc, from: harness.from }),
}))
vi.mock('@/lib/auth/password-hash', () => ({
  PASSWORD_HASH_CONCURRENCY_LIMIT: 2,
  hashPassword: harness.hashPassword,
  validateNewPassword: (password: unknown) =>
    typeof password === 'string' && password.length >= 6
      ? { ok: true }
      : { ok: false, code: 'PASSWORD_TOO_SHORT' },
}))
vi.mock('@/lib/server/notifications/payload-crypto', () => ({
  protectNotificationPayload: harness.protect,
}))

import {
  AccountManagementError,
  changeManagedAccountRole,
  completeInitialPasswordSetup,
  createManagedAccount,
  listManagedAccounts,
  requestManagedEmailChange,
  resendPasswordSetup,
} from './account-management'

const actorId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'

describe('account management database boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_APP_ORIGIN = 'https://dashboard.example.test'
    harness.hashPassword.mockResolvedValue('$argon2id$approved')
    harness.protect.mockReturnValue({
      ciphertext: 'protected-payload',
      nonce: 'protected-nonce',
      key_version: 1,
    })
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
        password_set_at: '2026-07-10T00:00:00Z',
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
        setup_status: 'complete',
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
    expect(name).toBe('admin_create_auth_account_protected_v61')
    expect(params).toMatchObject({
      p_actor_account_id: actorId,
      p_email: 'new@example.test',
      p_name: 'New Analyst',
      p_role: 'ANALYST',
      p_protected_payload: {
        ciphertext: 'protected-payload',
        nonce: 'protected-nonce',
        key_version: 1,
      },
    })
    expect(params.p_setup_token_hash).toMatch(/^[a-f0-9]{64}$/)
    expect(params).not.toHaveProperty('p_setup_url')
    expect(harness.protect).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'password_setup',
        recipient: 'new@example.test',
      }),
      {
        setup_url: expect.stringMatching(
          /^https:\/\/dashboard\.example\.test\/setup-password\?token=/
        ),
      }
    )
    expect(JSON.stringify(result)).not.toContain('token')
  })

  it('uses protected atomic RPCs for setup resend and email verification', async () => {
    harness.rpc.mockResolvedValue({ data: true, error: null })
    const maybeSingle = vi.fn().mockResolvedValue({
      data: { email: 'target@example.test' },
      error: null,
    })
    const query = { eq: vi.fn(), is: vi.fn(), maybeSingle }
    query.eq.mockReturnValue(query)
    query.is.mockReturnValue(query)
    harness.from.mockReturnValue({ select: vi.fn().mockReturnValue(query) })

    await resendPasswordSetup(actorId, actorId)
    await requestManagedEmailChange(actorId, actorId, {
      email: 'changed@example.test',
    })

    expect(harness.rpc).toHaveBeenNthCalledWith(
      1,
      'admin_resend_password_setup_protected_v61',
      expect.objectContaining({
        p_protected_payload: expect.objectContaining({ key_version: 1 }),
      })
    )
    expect(harness.rpc).toHaveBeenNthCalledWith(
      2,
      'admin_request_managed_email_change_protected_v61',
      expect.objectContaining({
        p_new_email: 'changed@example.test',
        p_protected_payload: expect.objectContaining({ key_version: 1 }),
      })
    )
    expect(JSON.stringify(harness.rpc.mock.calls)).not.toContain(
      'p_verification_url'
    )
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
