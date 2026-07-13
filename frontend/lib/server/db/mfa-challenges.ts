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
    public readonly code:
      | 'INVALID_REQUEST'
      | 'INVALID_CODE'
      | 'LOCKED'
      | 'EXPIRED'
      | 'UNAVAILABLE'
  ) {
    super(code)
    this.name = 'MfaChallengeError'
  }
}

export type MfaChallengePurpose =
  | 'login_mfa'
  | 'mfa_enrollment'
  | 'recent_reauthentication'

export type MfaCompletionClaims = {
  id: string
  name: string
  email: string
  role: UserRole
  authz_version: number
  auth_level: 'mfa'
  auth_method: 'totp'
  verified_at: string
  completion_purpose: MfaChallengePurpose
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
  purpose: MfaChallengePurpose
  expires_at: string
}> {
  const account = id(accountId)
  const handle = generatePreAuthHandle()
  const { data, error } = await getSupabaseServerClient().rpc(
    'begin_mfa_challenge_v61',
    {
      p_account_id: account,
      p_preauth_handle_hash: digestPreAuthHandle(handle),
      p_expires_at: new Date(Date.now() + 10 * 60 * 1_000).toISOString(),
    }
  )
  if (error || !Array.isArray(data) || data.length !== 1) unavailable(error)
  const row = z.object({
    challenge_id: UUID,
    purpose: z.enum(['login_mfa', 'mfa_enrollment', 'recent_reauthentication']),
    expires_at: z.string().datetime({ offset: true }),
  }).safeParse(data[0])
  if (!row.success) unavailable(null)
  return {
    challenge_id: row.data.challenge_id,
    handle,
    purpose: row.data.purpose,
    expires_at: row.data.expires_at,
  }
}

export async function beginRecentTotpChallenge(accountId: string): Promise<{
  challenge_id: string
  handle: string
  purpose: 'recent_reauthentication'
  expires_at: string
}> {
  const account = id(accountId)
  const handle = generatePreAuthHandle()
  const { data, error } = await getSupabaseServerClient().rpc(
    'begin_recent_totp_challenge_v61',
    {
      p_account_id: account,
      p_preauth_handle_hash: digestPreAuthHandle(handle),
      p_expires_at: new Date(Date.now() + 5 * 60 * 1_000).toISOString(),
    }
  )
  if (error || !Array.isArray(data) || data.length !== 1) unavailable(error)
  const row = z.object({
    challenge_id: UUID,
    purpose: z.literal('recent_reauthentication'),
    expires_at: z.string().datetime({ offset: true }),
  }).safeParse(data[0])
  if (!row.success) unavailable(null)
  return { ...row.data, handle: handle }
}

export async function hasActiveMfaEnrollmentChallenge(
  accountId: string,
  preAuthHandle: string
): Promise<boolean> {
  const account = id(accountId)
  const handle = validHandle(preAuthHandle)
  const { data, error } = await getSupabaseServerClient().rpc(
    'mfa_enrollment_challenge_available_v61',
    {
      p_account_id: account,
      p_preauth_handle_hash: digestPreAuthHandle(handle),
    }
  )
  if (error || typeof data !== 'boolean') unavailable(error)
  return data
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
  const valid = verification.valid && verification.timeStep !== undefined
  const completionToken = generateOpaqueToken()
  const { data: outcomeData, error: outcomeError } = await getSupabaseServerClient().rpc(
    'record_totp_attempt_v61',
    {
      p_account_id: account,
      p_preauth_handle_hash: digestPreAuthHandle(handle),
      p_factor_id: data.id,
      p_is_valid: valid,
      p_time_step: verification.timeStep ?? null,
      p_completion_token_hash: valid
        ? digestOpaqueToken(completionToken)
        : null,
      p_completion_expires_at: valid
        ? new Date(Date.now() + 2 * 60 * 1_000).toISOString()
        : null,
    }
  )
  if (outcomeError || !Array.isArray(outcomeData) || outcomeData.length !== 1) {
    unavailable(outcomeError)
  }
  const outcome = z.object({
    outcome: z.enum(['verified', 'invalid', 'locked', 'expired']),
  }).safeParse(outcomeData[0])
  if (!outcome.success) unavailable(null)
  if (outcome.data.outcome !== 'verified') {
    throw new MfaChallengeError(
      outcome.data.outcome === 'locked'
        ? 'LOCKED'
        : outcome.data.outcome === 'expired'
          ? 'EXPIRED'
          : 'INVALID_CODE'
    )
  }
  return { completion_token: completionToken }
}

export async function verifyRecentTotp(
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
  const valid = verification.valid && verification.timeStep !== undefined
  const completionToken = generateOpaqueToken()
  const { data: outcomeData, error: outcomeError } = await getSupabaseServerClient().rpc(
    'record_recent_totp_attempt_v61',
    {
      p_account_id: account,
      p_preauth_handle_hash: digestPreAuthHandle(handle),
      p_factor_id: data.id,
      p_is_valid: valid,
      p_time_step: verification.timeStep ?? null,
      p_completion_token_hash: valid ? digestOpaqueToken(completionToken) : null,
      p_completion_expires_at: valid
        ? new Date(Date.now() + 2 * 60 * 1_000).toISOString()
        : null,
    }
  )
  if (outcomeError || !Array.isArray(outcomeData) || outcomeData.length !== 1) {
    unavailable(outcomeError)
  }
  const outcome = z.object({
    outcome: z.enum(['verified', 'invalid', 'locked', 'expired']),
  }).safeParse(outcomeData[0])
  if (!outcome.success) unavailable(null)
  if (outcome.data.outcome !== 'verified') {
    throw new MfaChallengeError(
      outcome.data.outcome === 'locked'
        ? 'LOCKED'
        : outcome.data.outcome === 'expired'
          ? 'EXPIRED'
          : 'INVALID_CODE'
    )
  }
  return { completion_token: completionToken }
}

export async function consumeMfaCompletionToken(
  completionToken: string
): Promise<MfaCompletionClaims> {
  let digest: string
  try {
    digest = digestOpaqueToken(completionToken)
  } catch {
    throw new MfaChallengeError('INVALID_REQUEST')
  }
  const { data, error } = await getSupabaseServerClient().rpc(
    'consume_mfa_completion_token_v61',
    { p_completion_token_hash: digest }
  )
  if (error || !Array.isArray(data) || data.length !== 1) unavailable(error)
  const row = z.object({
    account_id: z.string().uuid(),
    name: z.string().min(1),
    email: z.string().email(),
    role: z.string(),
    authz_version: z.number().int().min(1),
    auth_level: z.literal('mfa'),
    auth_method: z.literal('totp'),
    verified_at: z.string().datetime({ offset: true }),
    completion_purpose: z.enum([
      'login_mfa',
      'mfa_enrollment',
      'recent_reauthentication',
    ]),
  }).safeParse(data[0])
  if (!row.success || !isUserRole(row.data.role)) unavailable(null)
  return {
    id: row.data.account_id,
    name: row.data.name,
    email: row.data.email,
    role: row.data.role,
    authz_version: row.data.authz_version,
    auth_level: row.data.auth_level,
    auth_method: row.data.auth_method,
    verified_at: row.data.verified_at,
    completion_purpose: row.data.completion_purpose,
  }
}
