import 'server-only'

import { randomUUID } from 'node:crypto'
import { z } from 'zod'

import {
  accountEnabledSchema,
  accountRoleSchema,
  createAccountSchema,
  managedEmailSchema,
  type SafeManagedAccount,
} from '@/features/user-management/contract'
import {
  buildTrustedActionUrl,
  digestOpaqueToken,
  generateOpaqueToken,
} from '@/lib/auth/account-tokens'
import { hashPassword, validateNewPassword } from '@/lib/auth/password-hash'
import { passwordHashConcurrencyGate } from '@/lib/auth/login-throttle'
import { protectNotificationPayload } from '@/lib/server/notifications/payload-crypto'
import { getSupabaseServerClient } from './client'
import { preflightPasswordToken } from './password-token-preflight'

const ACCOUNT_FIELDS =
  'id,email,pending_email,name,role,mfa_required,password_set_at,email_verified_at,disabled_at,created_at,auth_mfa_factors(status)'
const UUID = z.string().uuid()

const managedAccountRow = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  pending_email: z.string().email().nullable(),
  name: z.string().min(1),
  role: z.enum(['ADMIN', 'ANALYST', 'VIEWER']),
  mfa_required: z.boolean(),
  password_set_at: z.string().nullable(),
  email_verified_at: z.string().nullable(),
  disabled_at: z.string().nullable(),
  created_at: z.string().min(1),
  auth_mfa_factors: z
    .array(z.object({ status: z.string() }))
    .nullable()
    .default([]),
})

export class AccountManagementError extends Error {
  constructor(
    public readonly code:
      | 'INVALID_REQUEST'
      | 'CONFLICT'
      | 'NOT_FOUND'
      | 'UNAVAILABLE'
  ) {
    super(code)
    this.name = 'AccountManagementError'
  }
}

function configuredOrigin(): string {
  const origin = process.env.AUTH_APP_ORIGIN?.trim()
  if (!origin) throw new AccountManagementError('UNAVAILABLE')
  return origin
}

function expiresInThirtyMinutes(): string {
  return new Date(Date.now() + 30 * 60 * 1_000).toISOString()
}

function operationKeys(kind: string): {
  dedupeKey: string
  providerKey: string
} {
  const id = randomUUID()
  const key = `${kind}/${id}`
  return { dedupeKey: key, providerKey: key }
}

function rpcError(error: { code?: string } | null): never {
  if (error?.code === '23505') throw new AccountManagementError('CONFLICT')
  throw new AccountManagementError('UNAVAILABLE')
}

function accountId(value: unknown): string {
  const parsed = UUID.safeParse(value)
  if (!parsed.success) throw new AccountManagementError('UNAVAILABLE')
  return parsed.data
}

function requestUuid(value: unknown): string {
  const parsed = UUID.safeParse(value)
  if (!parsed.success) throw new AccountManagementError('INVALID_REQUEST')
  return parsed.data
}

function mapAccount(value: unknown): SafeManagedAccount {
  const parsed = managedAccountRow.safeParse(value)
  if (!parsed.success) throw new AccountManagementError('UNAVAILABLE')
  const row = parsed.data
  const activeFactor = (row.auth_mfa_factors ?? []).some((factor) =>
    ['verified', 'active'].includes(factor.status)
  )
  return {
    id: row.id,
    display_name: row.name,
    email: row.email,
    pending_email: row.pending_email,
    role: row.role,
    enabled: row.disabled_at === null,
    email_verified: row.email_verified_at !== null,
    mfa_status: !row.mfa_required
      ? 'not_required'
      : activeFactor
        ? 'active'
        : 'enrollment_required',
    setup_status: row.password_set_at === null ? 'pending' : 'complete',
    created_at: row.created_at,
  }
}

async function passwordSetupRecipient(
  targetAccountId: string
): Promise<string> {
  const { data, error } = await getSupabaseServerClient()
    .from('auth_accounts')
    .select('email')
    .eq('id', targetAccountId)
    .is('disabled_at', null)
    .is('password_hash', null)
    .maybeSingle()
  const parsed = z.object({ email: z.string().email() }).safeParse(data)
  if (error || !parsed.success) throw new AccountManagementError('UNAVAILABLE')
  return parsed.data.email
}

export async function listManagedAccounts(): Promise<SafeManagedAccount[]> {
  const { data, error } = await getSupabaseServerClient()
    .from('auth_accounts')
    .select(ACCOUNT_FIELDS)
    .order('created_at', { ascending: true })
  if (error || !Array.isArray(data)) rpcError(error)
  return data.map(mapAccount)
}

export async function createManagedAccount(
  actorAccountId: string,
  input: unknown
): Promise<{ account_id: string }> {
  const actor = UUID.safeParse(actorAccountId)
  const account = createAccountSchema.safeParse(input)
  if (!actor.success || !account.success) {
    throw new AccountManagementError('INVALID_REQUEST')
  }
  const token = generateOpaqueToken()
  const keys = operationKeys('password-setup')
  const setupUrl = buildTrustedActionUrl(
    configuredOrigin(),
    '/setup-password',
    token
  )
  const { data, error } = await getSupabaseServerClient().rpc(
    'admin_create_auth_account_protected_v61',
    {
      p_actor_account_id: actor.data,
      p_email: account.data.email,
      p_name: account.data.display_name,
      p_role: account.data.role,
      p_setup_token_hash: digestOpaqueToken(token),
      p_expires_at: expiresInThirtyMinutes(),
      p_protected_payload: protectNotificationPayload(
        {
          kind: 'password_setup',
          recipient: account.data.email,
          idempotencyKey: keys.providerKey,
        },
        { setup_url: setupUrl }
      ),
      p_dedupe_key: keys.dedupeKey,
      p_provider_idempotency_key: keys.providerKey,
    }
  )
  if (error) rpcError(error)
  return { account_id: accountId(data) }
}

export async function resendPasswordSetup(
  actorAccountId: string,
  targetAccountId: string
): Promise<void> {
  const actor = requestUuid(actorAccountId)
  const target = requestUuid(targetAccountId)
  const recipient = await passwordSetupRecipient(target)
  const token = generateOpaqueToken()
  const keys = operationKeys('password-setup-resend')
  const setupUrl = buildTrustedActionUrl(
    configuredOrigin(),
    '/setup-password',
    token
  )
  const { error } = await getSupabaseServerClient().rpc(
    'admin_resend_password_setup_protected_v61',
    {
      p_actor_account_id: actor,
      p_target_account_id: target,
      p_recipient: recipient,
      p_setup_token_hash: digestOpaqueToken(token),
      p_expires_at: expiresInThirtyMinutes(),
      p_protected_payload: protectNotificationPayload(
        {
          kind: 'password_setup',
          recipient,
          idempotencyKey: keys.providerKey,
        },
        { setup_url: setupUrl }
      ),
      p_dedupe_key: keys.dedupeKey,
      p_provider_idempotency_key: keys.providerKey,
    }
  )
  if (error) rpcError(error)
}

export async function changeManagedAccountRole(
  actorAccountId: string,
  targetAccountId: string,
  input: unknown
): Promise<void> {
  const parsed = accountRoleSchema.safeParse(input)
  if (!parsed.success) throw new AccountManagementError('INVALID_REQUEST')
  const { error } = await getSupabaseServerClient().rpc(
    'admin_change_account_role',
    {
      p_actor_account_id: requestUuid(actorAccountId),
      p_target_account_id: requestUuid(targetAccountId),
      p_role: parsed.data.role,
    }
  )
  if (error) rpcError(error)
}

export async function setManagedAccountEnabled(
  actorAccountId: string,
  targetAccountId: string,
  input: unknown
): Promise<void> {
  const parsed = accountEnabledSchema.safeParse(input)
  if (!parsed.success) throw new AccountManagementError('INVALID_REQUEST')
  const { error } = await getSupabaseServerClient().rpc(
    'admin_set_account_enabled_v61',
    {
      p_actor_account_id: requestUuid(actorAccountId),
      p_target_account_id: requestUuid(targetAccountId),
      p_enabled: parsed.data.enabled,
    }
  )
  if (error) rpcError(error)
}

export async function requestManagedEmailChange(
  actorAccountId: string,
  targetAccountId: string,
  input: unknown
): Promise<void> {
  const parsed = managedEmailSchema.safeParse(input)
  if (!parsed.success) throw new AccountManagementError('INVALID_REQUEST')
  const token = generateOpaqueToken()
  const keys = operationKeys('managed-email-verification')
  const verificationUrl = buildTrustedActionUrl(
    configuredOrigin(),
    '/verify-email',
    token
  )
  const { error } = await getSupabaseServerClient().rpc(
    'admin_request_managed_email_change_protected_v61',
    {
      p_actor_account_id: requestUuid(actorAccountId),
      p_target_account_id: requestUuid(targetAccountId),
      p_new_email: parsed.data.email,
      p_token_hash: digestOpaqueToken(token),
      p_expires_at: expiresInThirtyMinutes(),
      p_protected_payload: protectNotificationPayload(
        {
          kind: 'email_verification',
          recipient: parsed.data.email,
          idempotencyKey: keys.providerKey,
        },
        { verification_url: verificationUrl }
      ),
      p_dedupe_key: keys.dedupeKey,
      p_provider_idempotency_key: keys.providerKey,
    }
  )
  if (error) rpcError(error)
}

export async function completeInitialPasswordSetup(
  token: string,
  password: string
): Promise<{ account_id: string }> {
  const policy = validateNewPassword(password)
  if (!policy.ok) throw new Error('Password does not meet policy.')
  try {
    await preflightPasswordToken(token, 'password_setup')
  } catch {
    throw new AccountManagementError('INVALID_REQUEST')
  }
  const hashed = await passwordHashConcurrencyGate.run(() => hashPassword(password))
  if (!hashed.ok) throw new AccountManagementError('UNAVAILABLE')
  const passwordHash = hashed.value
  const { data, error } = await getSupabaseServerClient().rpc(
    'consume_password_setup_token',
    {
      p_token_hash: digestOpaqueToken(token),
      p_password_hash: passwordHash,
    }
  )
  if (error) rpcError(error)
  return { account_id: accountId(data) }
}

export async function activateManagedEmail(token: string): Promise<void> {
  const { error } = await getSupabaseServerClient().rpc(
    'activate_verified_managed_email',
    { p_token_hash: digestOpaqueToken(token) }
  )
  if (error) rpcError(error)
}
