import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  from: vi.fn(),
  rpc: vi.fn(),
  decrypt: vi.fn(),
  verify: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('./client', () => ({
  getSupabaseServerClient: () => ({ from: harness.from, rpc: harness.rpc }),
}))
vi.mock('@/lib/auth/mfa-crypto', () => ({ decryptTotpSecret: harness.decrypt }))
vi.mock('@/lib/auth/totp', () => ({ verifyTotpCode: harness.verify }))

import {
  beginRecentTotpChallenge,
  beginLoginMfaChallenge,
  consumeMfaCompletionToken,
  verifyRecentTotp,
  verifyMfaLogin,
} from './mfa-challenges'

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
const factorId = '2c0d7d68-e70d-4f22-9487-57b3df572b6c'

describe('MFA challenge persistence boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    harness.rpc.mockResolvedValue({ data: [{ outcome: 'verified' }], error: null })
    harness.decrypt.mockReturnValue('JBSWY3DPEHPK3PXP')
    harness.verify.mockReturnValue({ valid: true, timeStep: 10 })
  })

  it('starts a challenge with only a digest', async () => {
    harness.rpc.mockResolvedValueOnce({
      data: [{
        challenge_id: '2c0d7d68-e70d-4f22-9487-57b3df572b6c',
        purpose: 'login_mfa',
        expires_at: '2026-07-11T02:10:00.000Z',
      }],
      error: null,
    })
    const result = await beginLoginMfaChallenge(accountId)
    expect(result).toMatchObject({
      handle: expect.stringMatching(/^[A-Za-z0-9_-]{40,128}$/),
      challenge_id: expect.anything(),
    })
    const [, params] = harness.rpc.mock.calls[0] as [string, Record<string, unknown>]
    expect(params.p_preauth_handle_hash).toMatch(/^[a-f0-9]{64}$/)
    expect(JSON.stringify(params)).not.toContain(result.handle)
  })

  it('verifies TOTP and keeps the completion token server-side', async () => {
    const maybeSingle = vi.fn().mockResolvedValue({
      data: {
        id: factorId,
        secret_ciphertext: 'cipher',
        secret_nonce: 'nonce',
        secret_key_version: 1,
      },
      error: null,
    })
    const query = { eq: vi.fn(), maybeSingle }
    query.eq.mockReturnValue(query)
    harness.from.mockReturnValue({ select: vi.fn().mockReturnValue(query) })
    const result = await verifyMfaLogin(accountId, 'a'.repeat(43), '123456')
    expect(result).toMatchObject({ completion_token: expect.stringMatching(/^[A-Za-z0-9_-]{40,128}$/) })
    expect(harness.rpc).toHaveBeenCalledWith(
      'record_totp_attempt_v61',
      expect.objectContaining({ p_account_id: accountId, p_factor_id: factorId })
    )
    expect(JSON.stringify(harness.rpc.mock.calls)).not.toContain(result.completion_token)
  })

  it('uses a separate recent-reauthentication purpose', async () => {
    harness.rpc.mockResolvedValueOnce({
      data: [{
        challenge_id: factorId,
        purpose: 'recent_reauthentication',
        expires_at: '2026-07-11T02:10:00.000Z',
      }],
      error: null,
    })
    const result = await beginRecentTotpChallenge(accountId)
    expect(result.purpose).toBe('recent_reauthentication')
    expect(harness.rpc).toHaveBeenCalledWith(
      'begin_recent_totp_challenge_v61',
      expect.objectContaining({ p_account_id: accountId })
    )

    const maybeSingle = vi.fn().mockResolvedValue({
      data: {
        id: factorId,
        secret_ciphertext: 'cipher',
        secret_nonce: 'nonce',
        secret_key_version: 1,
      },
      error: null,
    })
    const query = { eq: vi.fn(), maybeSingle }
    query.eq.mockReturnValue(query)
    harness.from.mockReturnValue({ select: vi.fn().mockReturnValue(query) })
    await expect(verifyRecentTotp(accountId, result.handle, '123456')).resolves.toMatchObject({
      completion_token: expect.any(String),
    })
    expect(harness.rpc).toHaveBeenCalledWith(
      'record_recent_totp_attempt_v61',
      expect.objectContaining({ p_factor_id: factorId })
    )
  })

  it('maps only safe final claims from the completion RPC', async () => {
    harness.rpc.mockResolvedValue({
      data: [{
        account_id: accountId,
        name: 'Admin User',
        email: 'admin@example.test',
        role: 'ADMIN',
        authz_version: 4,
        auth_level: 'mfa',
        auth_method: 'totp',
        verified_at: '2026-07-11T02:00:00.000Z',
        completion_purpose: 'login_mfa',
      }],
      error: null,
    })
    await expect(consumeMfaCompletionToken('a'.repeat(43))).resolves.toEqual({
      id: accountId,
      name: 'Admin User',
      email: 'admin@example.test',
      role: 'ADMIN',
      authz_version: 4,
      auth_level: 'mfa',
      auth_method: 'totp',
      verified_at: '2026-07-11T02:00:00.000Z',
      completion_purpose: 'login_mfa',
    })
  })
})
