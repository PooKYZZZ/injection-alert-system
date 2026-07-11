import 'server-only'

import { randomUUID } from 'node:crypto'
import { z } from 'zod'

import { buildTrustedActionUrl, digestOpaqueToken, generateOpaqueToken } from '@/lib/auth/account-tokens'
import { hashPassword, validateNewPassword } from '@/lib/auth/password-hash'
import { passwordHashConcurrencyGate } from '@/lib/auth/login-throttle'
import { getSupabaseServerClient } from './client'
import { preflightPasswordToken } from './password-token-preflight'

const UUID = z.string().uuid()
const EMAIL = z.string().email()

export class PasswordRecoveryError extends Error {
  constructor(public readonly code: 'INVALID_REQUEST' | 'UNAVAILABLE') {
    super(code)
    this.name = 'PasswordRecoveryError'
  }
}

function accountId(value: unknown): string {
  const parsed = UUID.safeParse(value)
  if (!parsed.success) throw new PasswordRecoveryError('INVALID_REQUEST')
  return parsed.data
}

function key(kind: string): string {
  return `${kind}/${randomUUID()}`
}

export async function requestPasswordReset(email: string): Promise<{ status: 'sent' }> {
  const normalized = EMAIL.safeParse(email.trim().toLowerCase())
  if (!normalized.success) return { status: 'sent' }
  const client = getSupabaseServerClient()
  const { data, error } = await client
    .from('auth_accounts')
    .select('id')
    .eq('email', normalized.data)
    .is('disabled_at', null)
    .not('email_verified_at', 'is', null)
    .maybeSingle()
  if (error || !data || typeof data.id !== 'string') return { status: 'sent' }
  const token = generateOpaqueToken()
  const dedupe = key('password-reset')
  const { error: rpcError } = await client.rpc('create_password_reset_token', {
    p_account_id: data.id,
    p_token_hash: digestOpaqueToken(token),
    p_expires_at: new Date(Date.now() + 30 * 60 * 1_000).toISOString(),
    p_reset_url: buildTrustedActionUrl(process.env.AUTH_APP_ORIGIN ?? '', '/reset-password', token),
    p_dedupe_key: dedupe,
    p_provider_idempotency_key: dedupe,
    p_reason: 'user_requested',
  })
  if (rpcError) throw new PasswordRecoveryError('UNAVAILABLE')
  return { status: 'sent' }
}

export async function completePasswordReset(
  token: string,
  password: string
): Promise<{ account_id: string }> {
  if (typeof token !== 'string' || token.length < 40) throw new PasswordRecoveryError('INVALID_REQUEST')
  const validation = validateNewPassword(password)
  if (!validation.ok) throw new PasswordRecoveryError('INVALID_REQUEST')
  try {
    await preflightPasswordToken(token, 'password_reset')
  } catch {
    throw new PasswordRecoveryError('UNAVAILABLE')
  }
  const hashed = await passwordHashConcurrencyGate.run(() => hashPassword(password))
  if (!hashed.ok) throw new PasswordRecoveryError('UNAVAILABLE')
  const passwordHash = hashed.value
  const { data, error } = await getSupabaseServerClient().rpc('consume_password_reset_and_change_password', {
    p_token_hash: digestOpaqueToken(token),
    p_password_hash: passwordHash,
  })
  if (error || !UUID.safeParse(data).success) throw new PasswordRecoveryError('UNAVAILABLE')
  return { account_id: data }
}

export async function resetManagedAccountMfa(
  actorAccountId: string,
  targetAccountId: string,
  reason: string
): Promise<{ status: 'reset' }> {
  const actor = accountId(actorAccountId)
  const target = accountId(targetAccountId)
  if (actor === target || typeof reason !== 'string' || reason.trim().length < 1 || reason.length > 128) {
    throw new PasswordRecoveryError('INVALID_REQUEST')
  }
  const dedupe = key('admin-mfa-reset')
  const { error } = await getSupabaseServerClient().rpc('admin_reset_mfa', {
    p_actor_account_id: actor,
    p_target_account_id: target,
    p_reason: reason.trim(),
    p_dedupe_key: dedupe,
    p_provider_idempotency_key: dedupe,
  })
  if (error) throw new PasswordRecoveryError('UNAVAILABLE')
  return { status: 'reset' }
}
