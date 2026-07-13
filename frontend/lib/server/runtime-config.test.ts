import { afterEach, describe, expect, it, vi } from 'vitest'

vi.mock('server-only', () => ({}))

const connectionMock = vi.hoisted(() => vi.fn().mockResolvedValue(undefined))

vi.mock('next/server', () => ({ connection: connectionMock }))

import { readPageRuntimeAuthFlags, readRuntimeAuthFlags } from './runtime-config'

const flagNames = [
  'AUTH_ACCOUNT_MANAGEMENT_ENABLED',
  'AUTH_MFA_ENROLLMENT_ENABLED',
  'AUTH_EMAIL_RECOVERY_ENABLED',
  'AUTH_PASSWORD_RESET_ENABLED',
] as const

afterEach(() => {
  for (const name of flagNames) delete process.env[name]
})

describe('readRuntimeAuthFlags', () => {
  it('treats undefined flags as disabled', () => {
    expect(readRuntimeAuthFlags()).toEqual({
      accountManagementEnabled: false,
      mfaEnrollmentEnabled: false,
      emailRecoveryEnabled: false,
      passwordResetEnabled: false,
    })
  })

  it('maps all supported flags to booleans', () => {
    process.env.AUTH_ACCOUNT_MANAGEMENT_ENABLED = 'true'
    process.env.AUTH_MFA_ENROLLMENT_ENABLED = 'false'
    process.env.AUTH_EMAIL_RECOVERY_ENABLED = 'true'
    process.env.AUTH_PASSWORD_RESET_ENABLED = 'false'

    expect(readRuntimeAuthFlags()).toEqual({
      accountManagementEnabled: true,
      mfaEnrollmentEnabled: false,
      emailRecoveryEnabled: true,
      passwordResetEnabled: false,
    })
  })

  it.each(['TRUE', ' true ', 'yes', '1'])('rejects invalid value %j', (value) => {
    process.env.AUTH_MFA_ENROLLMENT_ENABLED = value

    expect(() => readRuntimeAuthFlags()).toThrow(
      'Invalid runtime auth feature flag configuration.'
    )
    expect(() => readRuntimeAuthFlags()).toThrowError(
      expect.not.objectContaining({ message: expect.stringContaining(value) })
    )
  })

  it('establishes the request boundary before reading page flags', async () => {
    process.env.AUTH_MFA_ENROLLMENT_ENABLED = 'true'

    await expect(readPageRuntimeAuthFlags()).resolves.toMatchObject({
      mfaEnrollmentEnabled: true,
    })
    expect(connectionMock).toHaveBeenCalledOnce()
  })
})
