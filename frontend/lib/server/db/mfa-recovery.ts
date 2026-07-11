import 'server-only'

import { z } from 'zod'

import {
  backupCodeLookupPrefix,
  normalizeBackupCode,
} from '@/lib/auth/backup-codes'
import { digestEmailOtp, generateEmailOtp } from '@/lib/auth/email-otp'
import { digestOpaqueToken, generateOpaqueToken } from '@/lib/auth/account-tokens'
import { verifyBackupCode } from '@/lib/auth/backup-codes'
import { isUserRole, type UserRole } from '@/lib/auth/roles'
import { getSupabaseServerClient } from './client'

const UUID = z.string().uuid()

export class MfaRecoveryError extends Error {
  constructor(
    public readonly code:
      | 'INVALID_REQUEST'
      | 'INVALID_CODE'
      | 'LOCKED'
      | 'EXPIRED'
      | 'COOLDOWN'
      | 'UNAVAILABLE'
  ) {
    super(code)
    this.name = 'MfaRecoveryError'
  }
}

function accountId(value: unknown): string {
  const parsed = UUID.safeParse(value)
  if (!parsed.success) throw new MfaRecoveryError('INVALID_REQUEST')
  return parsed.data
}

function tokenDigest(token: string): string {
  try {
    return digestOpaqueToken(token)
  } catch {
    throw new MfaRecoveryError('INVALID_REQUEST')
  }
}

function unavailable(error: { code?: string } | null): never {
  throw new MfaRecoveryError(error?.code === 'P0001' ? 'INVALID_CODE' : 'UNAVAILABLE')
}

export async function consumeBackupCodeForRecovery(
  rawAccountId: string,
  code: string
): Promise<{ completion_token: string }> {
  const id = accountId(rawAccountId)
  const normalized = normalizeBackupCode(code)
  if (!normalized) throw new MfaRecoveryError('INVALID_CODE')
  const { data, error } = await getSupabaseServerClient().rpc(
    'list_backup_code_candidates',
    { p_account_id: id, p_lookup_prefix: backupCodeLookupPrefix(normalized) }
  )
  if (error || !Array.isArray(data)) unavailable(error)
  let matchingId: string | undefined
  for (const candidate of data) {
    if (
      UUID.safeParse(candidate.id).success &&
      typeof candidate.code_hash === 'string' &&
      (await verifyBackupCode(candidate.code_hash, normalized))
    ) {
      matchingId = candidate.id
      break
    }
  }
  if (!matchingId) throw new MfaRecoveryError('INVALID_CODE')
  const completionToken = generateOpaqueToken()
  const { error: consumeError } = await getSupabaseServerClient().rpc(
    'consume_backup_code_for_recovery_v61',
    {
      p_account_id: id,
      p_code_id: matchingId,
      p_completion_token_hash: tokenDigest(completionToken),
      p_completion_expires_at: new Date(Date.now() + 5 * 60 * 1_000).toISOString(),
    }
  )
  if (consumeError) unavailable(consumeError)
  return { completion_token: completionToken }
}

export async function requestEmailRecovery(
  rawAccountId: string
): Promise<{ status: 'sent'; completion_token: string }> {
  const id = accountId(rawAccountId)
  const otp = generateEmailOtp()
  const completionToken = generateOpaqueToken()
  const expiresAt = new Date(Date.now() + 5 * 60 * 1_000).toISOString()
  const dedupeKey = `email-recovery/${id}/${tokenDigest(completionToken)}`
  const { data, error } = await getSupabaseServerClient().rpc(
    'begin_email_recovery_challenge_v61',
    {
      p_account_id: id,
      p_otp_digest: digestEmailOtp(otp),
      p_completion_token_hash: tokenDigest(completionToken),
      p_expires_at: expiresAt,
      p_otp: otp,
      p_dedupe_key: dedupeKey,
      p_provider_idempotency_key: dedupeKey,
    }
  )
  if (error) unavailable(error)
  const result = z.array(z.object({ status: z.literal('sent') })).safeParse(data)
  if (!result.success || result.data.length !== 1) unavailable(null)
  return { status: 'sent', completion_token: completionToken }
}

export async function completeEmailRecovery(
  rawAccountId: string,
  otp: string
): Promise<{ status: 'verified' }> {
  const id = accountId(rawAccountId)
  let digest: string
  try {
    digest = digestEmailOtp(otp)
  } catch {
    throw new MfaRecoveryError('INVALID_CODE')
  }
  const { data, error } = await getSupabaseServerClient().rpc(
    'consume_email_otp_for_recovery_v61',
    { p_account_id: id, p_otp_digest: digest }
  )
  if (error) unavailable(error)
  const result = z.array(z.object({
    outcome: z.enum(['verified', 'invalid', 'locked', 'expired']),
  })).safeParse(data)
  if (!result.success || result.data.length !== 1) unavailable(null)
  if (result.data[0].outcome !== 'verified') {
    throw new MfaRecoveryError(
      result.data[0].outcome === 'locked'
        ? 'LOCKED'
        : result.data[0].outcome === 'expired'
          ? 'EXPIRED'
          : 'INVALID_CODE'
    )
  }
  return { status: 'verified' }
}

export type RecoveryCompletionClaims = {
  id: string
  name: string
  email: string
  role: UserRole
  authz_version: number
  auth_level: 'recovery'
  auth_method: 'backup_code' | 'email_otp'
  verified_at: string
  completion_purpose: 'mfa_recovery'
}

export async function consumeRecoveryCompletionToken(
  token: string
): Promise<RecoveryCompletionClaims> {
  const { data, error } = await getSupabaseServerClient().rpc(
    'consume_mfa_recovery_completion_token_v61',
    { p_completion_token_hash: tokenDigest(token) }
  )
  if (error || !Array.isArray(data) || data.length !== 1) unavailable(error)
  const row = z.object({
    account_id: z.string().uuid(),
    name: z.string().min(1),
    email: z.string().email(),
    role: z.string(),
    authz_version: z.number().int().min(1),
    auth_level: z.literal('recovery'),
    auth_method: z.enum(['backup_code', 'email_otp']),
    verified_at: z.string().datetime({ offset: true }),
    completion_purpose: z.literal('mfa_recovery'),
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
