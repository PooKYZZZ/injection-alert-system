import { beforeEach, describe, expect, it, vi } from 'vitest'

const harness = vi.hoisted(() => ({ rpc: vi.fn() }))

vi.mock('server-only', () => ({}))
vi.mock('./client', () => ({
  getSupabaseServerClient: () => ({ rpc: harness.rpc }),
}))

import {
  beginLoginThrottleAttempt,
  completeLoginThrottleAttempt,
} from './login-throttle'

const ACCOUNT_ID = 'b8e7f806-a122-46ad-b867-42f9c2f32f5e'
const ATTEMPT_ID = 'd5c60380-817f-4f07-aadc-0ff30a2cb6dc'

beforeEach(() => {
  vi.clearAllMocks()
  harness.rpc.mockImplementation(async (_name, args) => ({
    data: [
      {
        allowed: true,
        reason_code: null,
        failure_count: 0,
        reservation_id: args.p_attempt_id,
      },
    ],
    error: null,
  }))
})

describe('shared login throttle adapter', () => {
  it('starts a canonical-account attempt with a server-generated reservation', async () => {
    const result = await beginLoginThrottleAttempt(ACCOUNT_ID, {
      turnstileEnabled: true,
      turnstileVerified: false,
    })

    expect(harness.rpc).toHaveBeenCalledWith(
      'begin_auth_login_attempt_v1',
      expect.objectContaining({
        p_account_id: ACCOUNT_ID,
        p_turnstile_enabled: true,
        p_turnstile_verified: false,
        p_challenge_threshold: 3,
        p_max_failures: 5,
        p_window_seconds: 300,
        p_cooldown_seconds: 60,
        p_attempt_id: expect.any(String),
      })
    )
    expect(result).toEqual({
      allowed: true,
      failureCount: 0,
      attemptId: expect.any(String),
    })
    expect(result.allowed && result.attemptId).toBe(
      harness.rpc.mock.calls[0][1].p_attempt_id
    )
  })

  it('preserves server decisions for challenge-required and cooldown states', async () => {
    harness.rpc.mockResolvedValueOnce({
      data: [
        {
          allowed: false,
          reason_code: 'VERIFICATION_REQUIRED',
          failure_count: 3,
          reservation_id: null,
        },
      ],
      error: null,
    })
    await expect(
      beginLoginThrottleAttempt(ACCOUNT_ID, {
        turnstileEnabled: true,
        turnstileVerified: false,
      })
    ).resolves.toEqual({
      allowed: false,
      failureCount: 3,
      reasonCode: 'VERIFICATION_REQUIRED',
    })

    harness.rpc.mockResolvedValueOnce({
      data: [
        {
          allowed: false,
          reason_code: 'IDENTIFIER_THROTTLED',
          failure_count: 5,
          reservation_id: null,
        },
      ],
      error: null,
    })
    await expect(
      beginLoginThrottleAttempt(ACCOUNT_ID, {
        turnstileEnabled: true,
        turnstileVerified: true,
      })
    ).resolves.toMatchObject({
      allowed: false,
      failureCount: 5,
      reasonCode: 'IDENTIFIER_THROTTLED',
    })
  })

  it('completes a reservation exactly once and returns the committed failure state', async () => {
    harness.rpc.mockResolvedValueOnce({
      data: [
        { completed: true, failure_count: 3, cooldown_active: false },
      ],
      error: null,
    })

    await expect(
      completeLoginThrottleAttempt(ACCOUNT_ID, ATTEMPT_ID, 'failure')
    ).resolves.toEqual({
      completed: true,
      failureCount: 3,
      cooldownActive: false,
    })
    expect(harness.rpc).toHaveBeenCalledWith(
      'complete_auth_login_attempt_v1',
      expect.objectContaining({
        p_account_id: ACCOUNT_ID,
        p_attempt_id: ATTEMPT_ID,
        p_outcome: 'failure',
      })
    )
  })

  it('fails closed on database errors and malformed RPC results', async () => {
    harness.rpc.mockResolvedValueOnce({ data: null, error: { code: 'XX000' } })
    await expect(
      beginLoginThrottleAttempt(ACCOUNT_ID, {
        turnstileEnabled: false,
        turnstileVerified: false,
      })
    ).rejects.toThrow('Login throttle is unavailable.')

    harness.rpc.mockResolvedValueOnce({ data: [], error: null })
    await expect(
      beginLoginThrottleAttempt(ACCOUNT_ID, {
        turnstileEnabled: false,
        turnstileVerified: false,
      })
    ).rejects.toThrow('Login throttle is unavailable.')
  })
})
