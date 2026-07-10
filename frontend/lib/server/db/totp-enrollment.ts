import 'server-only'

import { randomUUID } from 'node:crypto'
import { z } from 'zod'

import {
  backupCodeLookupPrefix,
  generateBackupCodes,
  hashBackupCode,
} from '@/lib/auth/backup-codes'
import {
  decryptTotpSecret,
  encryptTotpSecret,
} from '@/lib/auth/mfa-crypto'
import {
  buildTotpProvisioningUri,
  generateTotpSecret,
  verifyTotpCode,
} from '@/lib/auth/totp'
import { getSupabaseServerClient } from './client'

const UUID = z.string().uuid()

export class TotpEnrollmentError extends Error {
  constructor(
    public readonly code: 'INVALID_REQUEST' | 'INVALID_CODE' | 'UNAVAILABLE'
  ) {
    super(code)
    this.name = 'TotpEnrollmentError'
  }
}

function validId(value: unknown): string {
  const result = UUID.safeParse(value)
  if (!result.success) throw new TotpEnrollmentError('INVALID_REQUEST')
  return result.data
}

function unavailable(error: { code?: string } | null): never {
  throw new TotpEnrollmentError(error?.code === '22P02' ? 'INVALID_REQUEST' : 'UNAVAILABLE')
}

export async function beginTotpEnrollment(accountId: string): Promise<{
  factor_id: string
  manual_key: string
  provisioning_uri: string
  expires_at: string
}> {
  const id = validId(accountId)
  const client = getSupabaseServerClient()
  const { data: account, error: accountError } = await client
    .from('auth_accounts')
    .select('email')
    .eq('id', id)
    .maybeSingle()
  if (accountError || !account || typeof account.email !== 'string') unavailable(accountError)

  const factorId = randomUUID()
  const secret = generateTotpSecret()
  const encrypted = encryptTotpSecret(secret, id, factorId)
  const expiresAt = new Date(Date.now() + 10 * 60 * 1_000).toISOString()
  const { error } = await client.rpc('begin_totp_enrollment', {
    p_account_id: id,
    p_factor_id: factorId,
    p_ciphertext: encrypted.ciphertext,
    p_nonce: encrypted.nonce,
    p_key_version: encrypted.key_version,
    p_expires_at: expiresAt,
  })
  if (error) unavailable(error)
  return {
    factor_id: factorId,
    manual_key: secret,
    provisioning_uri: buildTotpProvisioningUri(account.email, secret),
    expires_at: expiresAt,
  }
}

export async function completeTotpEnrollment(
  accountId: string,
  factorId: string,
  code: string
): Promise<{ backup_codes: string[] }> {
  const id = validId(accountId)
  const factor = validId(factorId)
  const client = getSupabaseServerClient()
  const { data, error } = await client
    .from('auth_mfa_factors')
    .select('id,account_id,status,secret_ciphertext,secret_nonce,secret_key_version')
    .eq('id', factor)
    .eq('account_id', id)
    .maybeSingle()
  if (error || !data || data.status !== 'pending') unavailable(error)
  let secret: string
  try {
    secret = decryptTotpSecret(
      {
        ciphertext: data.secret_ciphertext,
        nonce: data.secret_nonce,
        key_version: data.secret_key_version,
      },
      id,
      factor
    )
  } catch {
    throw new TotpEnrollmentError('UNAVAILABLE')
  }
  const verification = verifyTotpCode(secret, code)
  if (!verification.valid || verification.timeStep === undefined) {
    throw new TotpEnrollmentError('INVALID_CODE')
  }
  const backupCodes = generateBackupCodes()
  const backupRows = await Promise.all(
    backupCodes.map(async (backupCode) => ({
      lookup_prefix: backupCodeLookupPrefix(backupCode),
      code_hash: await hashBackupCode(backupCode),
    }))
  )
  const result = await client.rpc('activate_totp_factor', {
    p_account_id: id,
    p_factor_id: factor,
    p_time_step: verification.timeStep,
    p_backup_codes: backupRows,
  })
  if (result.error) unavailable(result.error)
  return { backup_codes: backupCodes }
}
