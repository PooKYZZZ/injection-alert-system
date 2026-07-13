import 'server-only'

import { connection } from 'next/server'

export type RuntimeAuthFlags = Readonly<{
  accountManagementEnabled: boolean
  mfaEnrollmentEnabled: boolean
  emailRecoveryEnabled: boolean
  passwordResetEnabled: boolean
}>

function readFlag(value: string | undefined): boolean {
  if (value === undefined || value === 'false') return false
  if (value === 'true') return true
  throw new Error('Invalid runtime auth feature flag configuration.')
}

export function readRuntimeAuthFlags(): RuntimeAuthFlags {
  return {
    accountManagementEnabled: readFlag(
      process.env.AUTH_ACCOUNT_MANAGEMENT_ENABLED
    ),
    mfaEnrollmentEnabled: readFlag(process.env.AUTH_MFA_ENROLLMENT_ENABLED),
    emailRecoveryEnabled: readFlag(process.env.AUTH_EMAIL_RECOVERY_ENABLED),
    passwordResetEnabled: readFlag(process.env.AUTH_PASSWORD_RESET_ENABLED),
  }
}

export async function readPageRuntimeAuthFlags(): Promise<RuntimeAuthFlags> {
  await connection()
  return readRuntimeAuthFlags()
}
