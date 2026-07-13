import { randomUUID } from 'node:crypto'

import type { FullConfig } from '@playwright/test'
import type { SupabaseClient } from '@supabase/supabase-js'

import { hashPassword } from '@/lib/auth/password-hash'
import {
  createAuthE2EClient,
  safeDatabaseErrorCode,
} from '@/test-support/auth-e2e/database'
import {
  backupCodeLookupPrefix,
  encryptTotpSecretForSeed,
  generateBackupCode,
  generateTestPassword,
  generateTotpSecret,
} from '@/test-support/auth-e2e/seed-material'
import {
  parseAuthE2EState,
  type AuthE2EState,
} from '@/test-support/auth-e2e/state'
import { prewarmAuthRoutes } from '@/test-support/auth-e2e/prewarm'

const JOURNEYS = ['enroll', 'login', 'backup', 'email', 'stepup'] as const
const ACTIVE_FACTOR_JOURNEYS = ['login', 'backup', 'email', 'stepup'] as const

function fixedSetupError(stage: string, databaseError?: unknown): Error {
  const diagnostic = databaseError
    ? ` (database code ${safeDatabaseErrorCode(databaseError)})`
    : ''
  return new Error(`Authentication E2E ${stage} failed${diagnostic}.`)
}

async function assertMutation(
  operation: PromiseLike<{ error: unknown }>,
  stage: string
): Promise<void> {
  const { error } = await operation
  if (error) throw fixedSetupError(stage, error)
}

function createJourneyState(): AuthE2EState {
  const runId = randomUUID()
  const suffix = runId.replaceAll('-', '').slice(0, 12)
  const baseIdentity = (journey: (typeof JOURNEYS)[number]) => ({
    id: randomUUID(),
    email: `cybertrace-${suffix}-${journey}@example.test`,
    password: generateTestPassword(),
  })
  return parseAuthE2EState(
    JSON.stringify({
      runId,
      identities: {
        enroll: baseIdentity('enroll'),
        login: { ...baseIdentity('login'), totpSecret: generateTotpSecret() },
        backup: { ...baseIdentity('backup'), backupCode: generateBackupCode() },
        email: baseIdentity('email'),
        stepup: { ...baseIdentity('stepup'), totpSecret: generateTotpSecret() },
      },
    })
  )
}

async function seedJourneyState(
  client: SupabaseClient,
  state: AuthE2EState
): Promise<void> {
  const createdAt = new Date().toISOString()
  const accountRows = []
  for (const journey of JOURNEYS) {
    const identity = state.identities[journey]
    accountRows.push({
      id: identity.id,
      email: identity.email,
      username: `e2e-${state.runId.slice(0, 8)}-${journey}`,
      name: `E2E ${journey}`,
      role: 'ADMIN',
      authz_version: 1,
      password_hash: await hashPassword(identity.password),
      password_set_at: createdAt,
      email_verified_at: createdAt,
      mfa_required: true,
    })
  }
  await assertMutation(
    client.from('auth_accounts').insert(accountRows),
    'account seed'
  )

  const encryptionKey = process.env.AUTH_MFA_ENCRYPTION_KEY
  if (!encryptionKey) throw fixedSetupError('factor seed')
  const factorRows = ACTIVE_FACTOR_JOURNEYS.map((journey) => {
    const identity = state.identities[journey]
    const factorId = randomUUID()
    const secret =
      'totpSecret' in identity ? identity.totpSecret : generateTotpSecret()
    const encrypted = encryptTotpSecretForSeed(
      secret,
      identity.id,
      factorId,
      encryptionKey
    )
    return {
      id: factorId,
      account_id: identity.id,
      factor_type: 'totp',
      status: 'active',
      secret_ciphertext: encrypted.ciphertext,
      secret_nonce: encrypted.nonce,
      secret_key_version: encrypted.key_version,
      activated_at: createdAt,
      verified_at: createdAt,
    }
  })
  await assertMutation(
    client.from('auth_mfa_factors').insert(factorRows),
    'factor seed'
  )

  const backupIdentity = state.identities.backup
  await assertMutation(
    client.from('auth_backup_codes').insert({
      account_id: backupIdentity.id,
      lookup_prefix: backupCodeLookupPrefix(backupIdentity.backupCode),
      code_hash: await hashPassword(backupIdentity.backupCode),
    }),
    'backup-code seed'
  )

  const { count, error } = await client
    .from('auth_accounts')
    .select('id', { count: 'exact', head: true })
    .in(
      'id',
      JOURNEYS.map((journey) => state.identities[journey].id)
    )
  if (error || count !== JOURNEYS.length) throw fixedSetupError('verification')
}

async function cleanupJourneyState(
  client: SupabaseClient,
  state: AuthE2EState,
  bestEffort = false
): Promise<void> {
  const accountIds = JOURNEYS.map((journey) => state.identities[journey].id)
  const recipients = JOURNEYS.map((journey) => state.identities[journey].email)
  const cleanup = async () => {
    await assertMutation(
      client.from('notification_outbox').delete().in('recipient', recipients),
      'outbox cleanup'
    )
    const events = await client
      .from('security_events')
      .select('id')
      .in('account_id', accountIds)
    if (events.error) throw fixedSetupError('event lookup')
    const eventIds = (events.data ?? []).map(({ id }) => id)
    if (eventIds.length > 0) {
      await assertMutation(
        client.from('notification_outbox').delete().in('event_id', eventIds),
        'event outbox cleanup'
      )
    }
    await assertMutation(
      client.from('security_events').delete().in('account_id', accountIds),
      'event cleanup'
    )
    await assertMutation(
      client.from('auth_accounts').delete().in('id', accountIds),
      'account cleanup'
    )
    const remaining = await client
      .from('auth_accounts')
      .select('id', { count: 'exact', head: true })
      .in('id', accountIds)
    if (remaining.error || remaining.count !== 0) {
      throw fixedSetupError('cleanup verification')
    }
  }
  if (bestEffort) {
    try {
      await cleanup()
    } catch {
      return
    }
  } else {
    await cleanup()
  }
}

export default async function authGlobalSetup(_config: FullConfig) {
  if (process.env.CYBERTRACE_E2E_MANAGED !== 'true') {
    throw new Error(
      'Use npm run test:e2e:auth to create the disposable authentication environment.'
    )
  }
  await prewarmAuthRoutes(
    process.env.PLAYWRIGHT_BASE_URL ?? 'http://127.0.0.1:3000'
  )
  const client = createAuthE2EClient()
  const state = createJourneyState()
  try {
    await seedJourneyState(client, state)
    process.env.CYBERTRACE_E2E_STATE = JSON.stringify(state)
  } catch (error) {
    await cleanupJourneyState(client, state, true)
    throw error
  }

  return async () => {
    try {
      await cleanupJourneyState(client, state)
    } finally {
      delete process.env.CYBERTRACE_E2E_STATE
    }
  }
}
