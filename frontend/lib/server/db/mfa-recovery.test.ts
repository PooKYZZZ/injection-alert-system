import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({
  from: vi.fn(),
  rpc: vi.fn(),
  verify: vi.fn(),
  hash: vi.fn(),
}))

vi.mock('server-only', () => ({}))
vi.mock('./client', () => ({
  getSupabaseServerClient: () => ({ from: harness.from, rpc: harness.rpc }),
}))
vi.mock('@/lib/auth/password-hash', () => ({
  verifyPasswordHash: harness.verify,
}))

import {
  consumeBackupCodeForRecovery,
  consumeRecoveryCompletionToken,
  requestEmailRecovery,
} from './mfa-recovery'

const accountId = '7a7bb9de-1dff-44b7-9a44-12efe8a6716f'
const codeId = '2c0d7d68-e70d-4f22-9487-57b3df572b6c'

describe('MFA recovery persistence boundary', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    harness.rpc.mockResolvedValue({ data: [{ outcome: 'verified' }], error: null })
    harness.verify.mockResolvedValue(true)
  })

  it('consumes a verified backup code only after candidate hash verification', async () => {
    harness.rpc.mockResolvedValueOnce({ data: [{ id: codeId, code_hash: '$argon2$hash' }], error: null })
    const result = await consumeBackupCodeForRecovery(accountId, 'ABCD-EFGH-JKLM')
    expect(result).toMatchObject({ completion_token: expect.stringMatching(/^[A-Za-z0-9_-]{40,128}$/) })
    expect(harness.verify).toHaveBeenCalledWith('$argon2$hash', 'ABCD-EFGH-JKLM')
    expect(harness.rpc).toHaveBeenCalledWith('consume_backup_code_for_recovery_v61', expect.objectContaining({ p_code_id: codeId }))
  })

  it('creates an email OTP challenge without returning the OTP', async () => {
    process.env.AUTH_EMAIL_OTP_KEY = 'test-email-otp-key-with-at-least-32-bytes'
    harness.rpc.mockResolvedValue({ data: [{ status: 'sent' }], error: null })
    const result = await requestEmailRecovery(accountId)
    expect(result).toMatchObject({ status: 'sent', completion_token: expect.any(String) })
    expect(harness.rpc).toHaveBeenCalledWith('begin_email_recovery_challenge_v61', expect.objectContaining({ p_account_id: accountId, p_otp: expect.stringMatching(/^\d{6}$/) }))
    expect(JSON.stringify(result)).not.toMatch(/\d{6}/)
  })

  it('maps only recovery claims from the one-time completion RPC', async () => {
    harness.rpc.mockResolvedValue({
      data: [{
        account_id: accountId,
        name: 'Analyst User',
        email: 'analyst@example.test',
        role: 'ANALYST',
        authz_version: 9,
        auth_level: 'recovery',
        auth_method: 'email_otp',
        verified_at: '2026-07-11T02:00:00.000Z',
        completion_purpose: 'mfa_recovery',
      }],
      error: null,
    })
    await expect(consumeRecoveryCompletionToken('a'.repeat(43))).resolves.toEqual({
      id: accountId,
      name: 'Analyst User',
      email: 'analyst@example.test',
      role: 'ANALYST',
      authz_version: 9,
      auth_level: 'recovery',
      auth_method: 'email_otp',
      verified_at: '2026-07-11T02:00:00.000Z',
      completion_purpose: 'mfa_recovery',
    })
  })
})
