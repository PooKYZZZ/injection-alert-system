import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  from: vi.fn(),
  rpc: vi.fn(),
  encrypt: vi.fn(),
  hash: vi.fn(),
  decrypt: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('./client', () => ({
  getSupabaseServerClient: () => ({ from: harness.from, rpc: harness.rpc }),
}))
vi.mock('@/lib/auth/mfa-crypto', () => ({
  encryptTotpSecret: harness.encrypt,
  decryptTotpSecret: harness.decrypt,
}))
vi.mock('@/lib/auth/totp', async () => {
  const actual = await vi.importActual<typeof import('@/lib/auth/totp')>('@/lib/auth/totp')
  return {
    ...actual,
    verifyTotpCode: vi.fn(() => ({ valid: true, timeStep: 10 })),
  }
})
vi.mock('@/lib/auth/password-hash', () => ({
  hashPassword: harness.hash,
  verifyPasswordHash: vi.fn(),
}))

import {
  beginTotpEnrollment,
  completeTotpEnrollment,
} from './totp-enrollment'

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
const factorId = '2c0d7d68-e70d-4f22-9487-57b3df572b6c'

describe('TOTP enrollment database boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    harness.encrypt.mockReturnValue({ ciphertext: 'cipher', nonce: 'nonce', key_version: 1 })
    harness.rpc.mockResolvedValue({ data: factorId, error: null })
    harness.hash.mockResolvedValue('$argon2id$backup')
    harness.decrypt.mockReturnValue('JBSWY3DPEHPK3PXP')
  })

  it('returns a provisioning URI and never persists a plaintext secret', async () => {
    const maybeSingle = vi.fn().mockResolvedValue({ data: { email: 'analyst@example.test' }, error: null })
    const query = { eq: vi.fn(), maybeSingle }
    query.eq.mockReturnValue(query)
    const select = vi.fn().mockReturnValue(query)
    harness.from.mockReturnValue({ select })

    const result = await beginTotpEnrollment(accountId, 'a'.repeat(43))

    expect(result.manual_key).toMatch(/^[A-Z2-7]+$/)
    expect(result.provisioning_uri).toContain('otpauth://totp/')
    expect(harness.rpc).toHaveBeenCalledWith('begin_totp_enrollment_v61', expect.objectContaining({
      p_account_id: accountId,
      p_ciphertext: 'cipher',
    }))
    expect(JSON.stringify(harness.rpc.mock.calls)).not.toContain(result.manual_key)
  })

  it('activates with exactly eight hashed backup codes', async () => {
    const maybeSingle = vi.fn().mockResolvedValue({
      data: {
        id: factorId,
        account_id: accountId,
        status: 'pending',
        secret_ciphertext: 'cipher',
        secret_nonce: 'nonce',
        secret_key_version: 1,
      },
      error: null,
    })
    const query = { eq: vi.fn(), maybeSingle }
    query.eq.mockReturnValue(query)
    const select = vi.fn().mockReturnValue(query)
    harness.from.mockReturnValue({ select })

    harness.rpc.mockResolvedValue({ data: [{ outcome: 'verified' }], error: null })
    const result = await completeTotpEnrollment(accountId, factorId, '000000', 'a'.repeat(43))

    expect(result.backup_codes).toHaveLength(8)
    expect(harness.hash).toHaveBeenCalledTimes(8)
    expect(harness.rpc).toHaveBeenCalledWith('complete_totp_enrollment_v61', expect.objectContaining({
      p_account_id: accountId,
      p_factor_id: factorId,
      p_backup_codes: expect.arrayContaining([
        expect.objectContaining({ code_hash: '$argon2id$backup' }),
      ]),
    }))
    expect(JSON.stringify(result)).not.toContain('$argon2id$backup')
  })
})
