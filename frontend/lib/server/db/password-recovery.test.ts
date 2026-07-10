import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  from: vi.fn(),
  rpc: vi.fn(),
  hash: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('./client', () => ({ getSupabaseServerClient: () => ({ from: harness.from, rpc: harness.rpc }) }))
vi.mock('@/lib/auth/password-hash', () => ({
  hashPassword: harness.hash,
  validateNewPassword: (password: unknown) => typeof password === 'string' && password.length >= 15 ? { ok: true } : { ok: false, code: 'PASSWORD_TOO_SHORT' },
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

  it('hashes a new password before consuming the reset token', async () => {
    await expect(completePasswordReset('a'.repeat(43), 'correct horse battery staple')).resolves.toEqual({ account_id: accountId })
    expect(harness.hash).toHaveBeenCalledWith('correct horse battery staple')
    expect(harness.rpc).toHaveBeenCalledWith('consume_password_reset_and_change_password', expect.objectContaining({ p_token_hash: expect.stringMatching(/^[a-f0-9]{64}$/) }))
  })

  it('requires a distinct target and bounded reason for MFA reset', async () => {
    await expect(resetManagedAccountMfa(accountId, accountId, 'self reset')).rejects.toMatchObject({ code: 'INVALID_REQUEST' })
    expect(harness.rpc).not.toHaveBeenCalled()
  })
})
