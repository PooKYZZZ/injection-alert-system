import 'server-only'

import { digestOpaqueToken } from '@/lib/auth/account-tokens'
import { getSupabaseServerClient } from './client'

export type PasswordTokenPurpose = 'password_setup' | 'password_reset'

export class PasswordTokenPreflightError extends Error {
  constructor(public readonly code: 'INVALID_OR_EXPIRED' | 'UNAVAILABLE') {
    super(code)
    this.name = 'PasswordTokenPreflightError'
  }
}

export async function preflightPasswordToken(
  token: string,
  purpose: PasswordTokenPurpose
): Promise<void> {
  let tokenHash: string
  try {
    tokenHash = digestOpaqueToken(token)
  } catch {
    throw new PasswordTokenPreflightError('INVALID_OR_EXPIRED')
  }
  const { data, error } = await getSupabaseServerClient().rpc(
    'preflight_password_token_v61',
    { p_token_hash: tokenHash, p_purpose: purpose }
  )
  if (error) throw new PasswordTokenPreflightError('UNAVAILABLE')
  if (data !== true) throw new PasswordTokenPreflightError('INVALID_OR_EXPIRED')
}
