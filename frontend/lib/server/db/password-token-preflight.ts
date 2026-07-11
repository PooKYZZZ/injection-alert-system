import 'server-only'

import { digestOpaqueToken } from '@/lib/auth/account-tokens'
import { getSupabaseServerClient } from './client'

export type PasswordTokenPurpose = 'password_setup' | 'password_reset'

export async function preflightPasswordToken(
  token: string,
  purpose: PasswordTokenPurpose
): Promise<void> {
  let tokenHash: string
  try {
    tokenHash = digestOpaqueToken(token)
  } catch {
    throw new Error('INVALID_OR_EXPIRED')
  }
  const { data, error } = await getSupabaseServerClient().rpc(
    'preflight_password_token_v61',
    { p_token_hash: tokenHash, p_purpose: purpose }
  )
  if (error || data !== true) throw new Error('INVALID_OR_EXPIRED')
}
