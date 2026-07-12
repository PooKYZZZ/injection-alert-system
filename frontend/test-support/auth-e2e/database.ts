import { createClient, type SupabaseClient } from '@supabase/supabase-js'

import {
  unprotectNotificationPayload,
  type ProtectedNotificationPayload,
} from '@/lib/server/notifications/payload-crypto-core'

function requiredEnvironment(name: string): string {
  const value = process.env[name]?.trim()
  if (!value) throw new Error('Authentication E2E database is unavailable.')
  return value
}

export function safeDatabaseErrorCode(error: unknown): string {
  if (!error || typeof error !== 'object' || !('code' in error)) {
    return 'UNKNOWN'
  }
  const code = error.code
  return typeof code === 'string' && /^[A-Z0-9_]{1,32}$/i.test(code)
    ? code
    : 'UNKNOWN'
}

export function createAuthE2EClient(): SupabaseClient {
  return createClient(
    requiredEnvironment('SUPABASE_URL'),
    requiredEnvironment('SUPABASE_SERVICE_ROLE_KEY'),
    {
      auth: {
        persistSession: false,
        autoRefreshToken: false,
        detectSessionInUrl: false,
      },
    }
  )
}

type EmailRecoveryOutboxRow = {
  payload_safe_json: unknown
  provider_idempotency_key: unknown
}

export function readEmailRecoveryOtp(
  email: string,
  row: EmailRecoveryOutboxRow
): string {
  try {
    if (typeof row.provider_idempotency_key !== 'string') throw new Error()
    const payload = unprotectNotificationPayload(
      {
        kind: 'email_recovery_otp',
        recipient: email,
        idempotencyKey: row.provider_idempotency_key,
      },
      row.payload_safe_json as ProtectedNotificationPayload
    )
    if (!/^\d{6}$/.test(payload.otp ?? '')) throw new Error()
    return payload.otp
  } catch {
    throw new Error('Authentication E2E database is unavailable.')
  }
}

export async function waitForEmailRecoveryOtp(
  email: string,
  timeoutMs = 10_000
): Promise<string> {
  const client = createAuthE2EClient()
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    const { data, error } = await client
      .from('notification_outbox')
      .select('payload_safe_json,provider_idempotency_key')
      .eq('recipient', email)
      .eq('kind', 'email_recovery_otp')
      .order('created_at', { ascending: false })
      .limit(1)
      .maybeSingle()
    if (!error && data) {
      try {
        return readEmailRecoveryOtp(email, data)
      } catch {
        // The row may not be fully committed yet; keep polling until timeout.
      }
    }
    await new Promise((resolve) => setTimeout(resolve, 100))
  }
  throw new Error('Disposable email recovery OTP was not created.')
}

export async function readAuthAccountState(accountId: string): Promise<{
  authzVersion: number
  activeFactors: number
  usedBackupCodes: number
}> {
  const client = createAuthE2EClient()
  const [account, factors, backupCodes] = await Promise.all([
    client
      .from('auth_accounts')
      .select('authz_version')
      .eq('id', accountId)
      .single(),
    client
      .from('auth_mfa_factors')
      .select('id', { count: 'exact', head: true })
      .eq('account_id', accountId)
      .eq('status', 'active'),
    client
      .from('auth_backup_codes')
      .select('id', { count: 'exact', head: true })
      .eq('account_id', accountId)
      .not('used_at', 'is', null),
  ])
  if (
    account.error ||
    factors.error ||
    backupCodes.error ||
    !Number.isInteger(account.data?.authz_version)
  ) {
    throw new Error('Disposable authentication state is unavailable.')
  }
  return {
    authzVersion: account.data.authz_version,
    activeFactors: factors.count ?? 0,
    usedBackupCodes: backupCodes.count ?? 0,
  }
}
