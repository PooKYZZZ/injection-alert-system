import 'server-only'

import { z } from 'zod'

import {
  decryptTotpSecret,
} from '@/lib/auth/mfa-crypto'
import {
  digestOpaqueToken,
  generateOpaqueToken,
} from '@/lib/auth/account-tokens'
import { digestPreAuthHandle, generatePreAuthHandle } from '@/lib/auth/preauth'
import { verifyTotpCode } from '@/lib/auth/totp'
import { isUserRole, type UserRole } from '@/lib/auth/roles'
import { getSupabaseServerClient } from './client'

const UUID = z.string().uuid()

export class MfaChallengeError extends Error {
  constructor(
    public readonly code: 'INVALID_REQUEST' | 'INVALID_CODE' | 'EXPIRED' | 'UNAVAILABLE'
  ) {
    super(code)
    this.name = 'MfaChallengeError'
  }
}

function id(value: unknown): string {
  const parsed = UUID.safeParse(value)
  if (!parsed.success) throw new MfaChallengeError('INVALID_REQUEST')
  return parsed.data
}

function validHandle(value: unknown): string {
  if (typeof value !== 'string') throw new MfaChallengeError('INVALID_REQUEST')
  try {
    digestPreAuthHandle(value)
    return value
  } catch {
    throw new MfaChallengeError('INVALID_REQUEST')
  }
}

function unavailable(error: { code?: string } | null): never {
  throw new MfaChallengeError(error?.code === 'P0001' ? 'EXPIRED' : 'UNAVAILABLE')
}

export async function beginLoginMfaChallenge(accountId: string): Promise<{
  challenge_id: string
  handle: string
}> {
  const account = id(accountId)
  const handle = generatePreAuthHandle()
  const { data, error } = await getSupabaseServerClient().rpc(
    'begin_login_mfa_challenge',
    {
      p_account_id: account,
      p_preauth_handle_hash: digestPreAuthHandle(handle),
      p_expires_at: new Date(Date.now() + 10 * 60 * 1_000).toISOString(),
    }
  )
  if (error) unavailable(error)
  const challengeId = UUID.safeParse(data)
  if (!challengeId.success) unavailable(null)
  return { challenge_id: challengeId.data, handle }
}

export async function verifyMfaLogin(
  accountId: string,
  preAuthHandle: string,
  code: string
): Promise<{ completion_token: string }> {
  const account = id(accountId)
  const handle = validHandle(preAuthHandle)
  const { data, error } = await getSupabaseServerClient()
    .from('auth_mfa_factors')
    .select('id,secret_ciphertext,secret_nonce,secret_key_version')
    .eq('account_id', account)
    .eq('factor_type', 'totp')
    .eq('status', 'active')
    .maybeSingle()
  if (error || !data) unavailable(error)
  let secret: string
  try {
    secret = decryptTotpSecret(
      {
        ciphertext: data.secret_ciphertext,
        nonce: data.secret_nonce,
        key_version: data.secret_key_version,
      },
      account,
      data.id
    )
  } catch {
    throw new MfaChallengeError('UNAVAILABLE')
  }
  const verification = verifyTotpCode(secret, code)
  if (!verification.valid || verification.timeStep === undefined) {
    throw new MfaChallengeError('INVALID_CODE')
  }
  const completionToken = generateOpaqueToken()
  const { error: rpcError } = await getSupabaseServerClient().rpc(
    'verify_totp_and_issue_completion',
    {
      p_account_id: account,
      p_preauth_handle_hash: digestPreAuthHandle(handle),
      p_factor_id: data.id,
      p_time_step: verification.timeStep,
      p_completion_token_hash: digestOpaqueToken(completionToken),
      p_completion_expires_at: new Date(Date.now() + 2 * 60 * 1_000).toISOString(),
    }
  )
  if (rpcError) unavailable(rpcError)
  return { completion_token: completionToken }
}

export async function consumeMfaCompletionToken(completionToken: string): Promise<{
  id: string
  role: UserRole
  authz_version: number
  auth_level: 'mfa'
  auth_method: 'totp'
}> {
  let digest: string
  try {
    digest = digestOpaqueToken(completionToken)
  } catch {
    throw new MfaChallengeError('INVALID_REQUEST')
  }
  const { data, error } = await getSupabaseServerClient().rpc(
    'consume_mfa_completion_token',
    { p_completion_token_hash: digest }
  )
  if (error || !Array.isArray(data) || data.length !== 1) unavailable(error)
  const row = z.object({
    account_id: z.string().uuid(),
    role: z.string(),
    authz_version: z.number().int().min(1),
  }).safeParse(data[0])
  if (!row.success || !isUserRole(row.data.role)) unavailable(null)
  return {
    id: row.data.account_id,
    role: row.data.role,
    authz_version: row.data.authz_version,
    auth_level: 'mfa',
    auth_method: 'totp',
  }
}
