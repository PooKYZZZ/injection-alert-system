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
    public readonly code: 'INVALID_REQUEST' | 'INVALID_CODE' | 'COOLDOWN' | 'UNAVAILABLE'
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
    'consume_backup_code_for_recovery',
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
  const client = getSupabaseServerClient()
  const { data: account, error: accountError } = await client
    .from('auth_accounts')
    .select('email')
    .eq('id', id)
    .maybeSingle()
  if (accountError || !account || typeof account.email !== 'string') unavailable(accountError)
  const { error } = await client.rpc(
    'begin_email_recovery_challenge',
    {
      p_account_id: id,
      p_otp_digest: digestEmailOtp(otp),
      p_completion_token_hash: tokenDigest(completionToken),
      p_expires_at: expiresAt,
    }
  )
  if (error) unavailable(error)
  const { error: outboxError } = await client
    .from('notification_outbox')
    .insert({
      channel: 'email',
      recipient: account.email,
      kind: 'email_recovery_otp',
      template_version: 1,
      dedupe_key: `email-recovery/${id}/${tokenDigest(completionToken)}`,
      provider_idempotency_key: `email-recovery/${id}/${tokenDigest(completionToken)}`,
      payload_safe_json: { otp },
    })
  if (outboxError) unavailable(outboxError)
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
  const { error } = await getSupabaseServerClient().rpc(
    'consume_email_otp_for_recovery',
    { p_account_id: id, p_otp_digest: digest }
  )
  if (error) unavailable(error)
  return { status: 'verified' }
}

export async function consumeRecoveryCompletionToken(token: string): Promise<{
  id: string
  role: UserRole
  authz_version: number
  auth_level: 'recovery'
  auth_method: 'backup_code' | 'email_otp'
}> {
  const { data, error } = await getSupabaseServerClient().rpc(
    'consume_mfa_recovery_completion_token',
    { p_completion_token_hash: tokenDigest(token) }
  )
  if (error || !Array.isArray(data) || data.length !== 1) unavailable(error)
  const row = z.object({
    account_id: z.string().uuid(),
    role: z.string(),
    authz_version: z.number().int().min(1),
    auth_method: z.enum(['backup_code', 'email_otp']),
  }).safeParse(data[0])
  if (!row.success || !isUserRole(row.data.role)) unavailable(null)
  return {
    id: row.data.account_id,
    role: row.data.role,
    authz_version: row.data.authz_version,
    auth_level: 'recovery',
    auth_method: row.data.auth_method,
  }
}
