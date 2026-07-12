import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  from: vi.fn(),
  rpc: vi.fn(),
  hash: vi.fn(),
  protect: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('./client', () => ({ getSupabaseServerClient: () => ({ from: harness.from, rpc: harness.rpc }) }))
vi.mock('@/lib/auth/password-hash', () => ({
  PASSWORD_HASH_CONCURRENCY_LIMIT: 2,
  hashPassword: harness.hash,
  validateNewPassword: (password: unknown) => typeof password === 'string' && password.length >= 15 ? { ok: true } : { ok: false, code: 'PASSWORD_TOO_SHORT' },
}))
vi.mock('@/lib/server/notifications/payload-crypto', () => ({
  protectNotificationPayload: harness.protect,
}))

import {
  completePasswordReset,
  requestPasswordReset,
  resetManagedAccountMfa,
} from './password-recovery'

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'

describe('password recovery database boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    process.env.AUTH_APP_ORIGIN = 'https://dashboard.example.test'
    harness.hash.mockResolvedValue('$argon2id$v=19$m=19456,t=2,p=1$hash')
    harness.protect.mockReturnValue({
      ciphertext: 'protected-payload',
      nonce: 'protected-nonce',
      key_version: 1,
    })
    harness.rpc.mockResolvedValue({ data: accountId, error: null })
  })

  it('returns a generic reset result for unknown accounts', async () => {
    const maybeSingle = vi.fn().mockResolvedValue({ data: null, error: null })
    const query = { eq: vi.fn(), is: vi.fn(), not: vi.fn(), maybeSingle }
    query.eq.mockReturnValue(query)
    query.is.mockReturnValue(query)
    query.not.mockReturnValue(query)
    harness.from.mockReturnValue({ select: vi.fn().mockReturnValue(query) })
    await expect(requestPasswordReset('unknown@example.test')).resolves.toEqual({ status: 'sent' })
    expect(harness.rpc).not.toHaveBeenCalled()
  })

  it('persists only a protected reset payload through the atomic RPC', async () => {
    const maybeSingle = vi.fn().mockResolvedValue({
      data: { id: accountId },
      error: null,
    })
    const query = { eq: vi.fn(), is: vi.fn(), not: vi.fn(), maybeSingle }
    query.eq.mockReturnValue(query)
    query.is.mockReturnValue(query)
    query.not.mockReturnValue(query)
    harness.from.mockReturnValue({ select: vi.fn().mockReturnValue(query) })

    await expect(requestPasswordReset('owner@example.test')).resolves.toEqual({
      status: 'sent',
    })

    expect(harness.rpc).toHaveBeenCalledWith(
      'create_password_reset_token_protected_v61',
      expect.objectContaining({
        p_protected_payload: expect.objectContaining({ key_version: 1 }),
      })
    )
    expect(JSON.stringify(harness.rpc.mock.calls)).not.toContain('p_reset_url')
    expect(harness.protect).toHaveBeenCalledWith(
      expect.objectContaining({
        kind: 'password_reset',
        recipient: 'owner@example.test',
      }),
      {
        reset_url: expect.stringContaining('/reset-password?token='),
      }
    )
  })

  it('hashes a new password before consuming the reset token', async () => {
    harness.rpc
      .mockResolvedValueOnce({ data: true, error: null })
      .mockResolvedValueOnce({ data: accountId, error: null })
    await expect(completePasswordReset('a'.repeat(43), 'correct horse battery staple')).resolves.toEqual({ account_id: accountId })
    expect(harness.hash).toHaveBeenCalledWith('correct horse battery staple')
    expect(harness.rpc).toHaveBeenCalledWith('consume_password_reset_and_change_password', expect.objectContaining({ p_token_hash: expect.stringMatching(/^[a-f0-9]{64}$/) }))
  })

  it('does not hash an invalid reset token after cheap preflight', async () => {
    harness.rpc.mockResolvedValue({ data: false, error: null })
    await expect(
      completePasswordReset('a'.repeat(43), 'correct horse battery staple')
    ).rejects.toMatchObject({ code: 'UNAVAILABLE' })
    expect(harness.hash).not.toHaveBeenCalled()
    expect(harness.rpc).toHaveBeenCalledWith(
      'preflight_password_token_v61',
      expect.objectContaining({ p_purpose: 'password_reset' })
    )
  })

  it('requires a distinct target and bounded reason for MFA reset', async () => {
    await expect(resetManagedAccountMfa(accountId, accountId, 'self reset')).rejects.toMatchObject({ code: 'INVALID_REQUEST' })
    expect(harness.rpc).not.toHaveBeenCalled()
  })
})
