import { describe, expect, it, vi } from 'vitest'

import {
  parseTotpSecret,
  totpCodeAtStep,
  totpCodeAtTime,
  totpTimeStep,
  waitForTotpStepAfter,
} from './totp'

const RFC_6238_SECRET = 'GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ'

describe('authentication E2E TOTP support', () => {
  it('matches the RFC 6238 SHA-1 vector and the application six-digit form', () => {
    expect(totpCodeAtStep(RFC_6238_SECRET, 1, 8)).toBe('94287082')
    expect(totpCodeAtStep(RFC_6238_SECRET, 1)).toBe('287082')
  })

  it('returns the exact time step used to generate a runtime code', () => {
    expect(totpTimeStep(59_000)).toBe(1)
    expect(totpCodeAtTime(RFC_6238_SECRET, 59_000)).toEqual({
      code: '287082',
      step: 1,
    })
  })

  it('extracts only a valid Base32 secret from a provisioning URI', () => {
    expect(
      parseTotpSecret(
        `otpauth://totp/CyberTrace%3Aadmin?secret=${RFC_6238_SECRET}&issuer=CyberTrace`
      )
    ).toBe(RFC_6238_SECRET)
    expect(() => parseTotpSecret('https://example.test/not-totp')).toThrow(
      'TOTP provisioning URI is invalid.'
    )
  })

  it('waits only until a newer time step plus a small clock-settle margin', async () => {
    let nowMs = 29_990
    const sleep = vi.fn(async (durationMs: number) => {
      nowMs += durationMs
    })

    await expect(
      waitForTotpStepAfter(0, {
        now: () => nowMs,
        sleep,
        settleMs: 25,
      })
    ).resolves.toBe(1)
    expect(sleep).toHaveBeenCalledOnce()
    expect(sleep).toHaveBeenCalledWith(35)
  })

  it('does not sleep when a newer step is already available', async () => {
    const sleep = vi.fn(async () => undefined)

    await expect(
      waitForTotpStepAfter(4, {
        now: () => 5 * 30_000,
        sleep,
      })
    ).resolves.toBe(5)
    expect(sleep).not.toHaveBeenCalled()
  })

  it('fails closed instead of waiting for an unreasonable future step', async () => {
    await expect(
      waitForTotpStepAfter(20, {
        now: () => 0,
        sleep: async () => undefined,
      })
    ).rejects.toThrow('A newer TOTP time step is not safely reachable.')
  })
})
