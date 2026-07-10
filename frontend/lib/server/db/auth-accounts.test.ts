import fs from 'node:fs'
import path from 'node:path'

import { beforeEach, describe, expect, it, vi } from 'vitest'

type QueryResponse = {
  data: unknown
  error: unknown
}

type QueryRecord = {
  table: string
  fields: string
  column?: string
  value?: string
}

const dbHarness = vi.hoisted(() => ({
  getClient: vi.fn(),
  queries: [] as QueryRecord[],
  responses: [] as QueryResponse[],
}))

vi.mock('server-only', () => ({}))
vi.mock('./client', () => ({
  getSupabaseServerClient: dbHarness.getClient,
}))

const loginRow = {
  id: '7a7bb9de-1dff-44b7-9a44-12efe8a6716f',
  email: 'admin@example.test',
  username: 'soc-admin',
  name: 'SOC Admin',
  role: 'ADMIN',
  authz_version: 4,
  password_hash: '$argon2id$v=19$m=19456,t=2,p=1$test$hash',
  mfa_required: false,
  disabled_at: null,
}

function queueResponse(data: unknown, error: unknown = null): void {
  dbHarness.responses.push({ data, error })
}

beforeEach(() => {
  dbHarness.queries.length = 0
  dbHarness.responses.length = 0
  dbHarness.getClient.mockReset()
  dbHarness.getClient.mockReturnValue({
    from(table: string) {
      const query: QueryRecord = { table, fields: '' }
      dbHarness.queries.push(query)
      return {
        select(fields: string) {
          query.fields = fields
          return {
            eq(column: string, value: string) {
              query.column = column
              query.value = value
              return {
                async maybeSingle() {
                  const response = dbHarness.responses.shift()
                  if (!response) {
                    throw new Error('Missing mocked database response.')
                  }
                  return response
                },
              }
            },
          }
        },
      }
    },
  })
})

describe('auth account database boundary', () => {
  it('exposes narrow login and session freshness lookups', async () => {
    const accountBoundary = await import('./auth-accounts')

    expect(typeof accountBoundary.findAuthAccountByIdentifier).toBe('function')
    expect(typeof accountBoundary.getAccountForSessionFreshness).toBe(
      'function'
    )
  })

  it('queries login accounts by normalized email and maps only allowed fields', async () => {
    queueResponse({
      ...loginRow,
      created_at: '2026-07-04T00:00:00Z',
      unexpected_secret: 'must-not-cross-boundary',
    })
    const { findAuthAccountByIdentifier } = await import('./auth-accounts')

    await expect(
      findAuthAccountByIdentifier('  ADMIN@EXAMPLE.TEST  ')
    ).resolves.toEqual({
      id: loginRow.id,
      email: loginRow.email,
      username: loginRow.username,
      name: loginRow.name,
      role: loginRow.role,
      authzVersion: 4,
      passwordHash: loginRow.password_hash,
      mfaRequired: false,
      disabledAt: null,
    })
    expect(dbHarness.queries).toEqual([
      expect.objectContaining({
        table: 'auth_accounts',
        column: 'email',
        value: 'admin@example.test',
      }),
    ])
  })

  it('queries UUID identifiers as account ids', async () => {
    queueResponse(loginRow)
    const { findAuthAccountByIdentifier } = await import('./auth-accounts')

    await findAuthAccountByIdentifier(`  ${loginRow.id.toUpperCase()}  `)

    expect(dbHarness.queries[0]).toMatchObject({
      table: 'auth_accounts',
      column: 'id',
      value: loginRow.id,
    })
  })

  it('falls back from email to normalized username', async () => {
    queueResponse(null)
    queueResponse(loginRow)
    const { findAuthAccountByIdentifier } = await import('./auth-accounts')

    await expect(
      findAuthAccountByIdentifier('  SOC-ADMIN  ')
    ).resolves.toMatchObject({ id: loginRow.id, username: 'soc-admin' })
    expect(dbHarness.queries.map(({ column, value }) => ({ column, value }))).toEqual([
      { column: 'email', value: 'soc-admin' },
      { column: 'username', value: 'soc-admin' },
    ])
  })

  it('rejects empty or oversized identifiers before querying', async () => {
    const { findAuthAccountByIdentifier } = await import('./auth-accounts')

    await expect(findAuthAccountByIdentifier('   ')).resolves.toBeUndefined()
    await expect(
      findAuthAccountByIdentifier('a'.repeat(321))
    ).resolves.toBeUndefined()
    expect(dbHarness.queries).toEqual([])
  })

  it('uses a password-free projection for session freshness', async () => {
    queueResponse({
      id: loginRow.id,
      role: loginRow.role,
      authz_version: loginRow.authz_version,
      mfa_required: true,
      disabled_at: null,
      password_hash: loginRow.password_hash,
    })
    const { getAccountForSessionFreshness } = await import('./auth-accounts')

    const account = await getAccountForSessionFreshness(loginRow.id)

    expect(account).toEqual({
      id: loginRow.id,
      role: 'ADMIN',
      authzVersion: 4,
      mfaRequired: true,
      disabledAt: null,
    })
    expect(dbHarness.queries[0].fields).not.toContain('password_hash')
    expect(dbHarness.queries[0].fields).toContain('mfa_required')
    expect(account).not.toHaveProperty('passwordHash')
  })

  it('throws a controlled failure without exposing database details', async () => {
    queueResponse(null, {
      message: 'connection secret and internal Supabase URL',
    })
    const { findAuthAccountByIdentifier } = await import('./auth-accounts')

    let message = ''
    try {
      await findAuthAccountByIdentifier('admin@example.test')
    } catch (error) {
      message = error instanceof Error ? error.message : String(error)
    }

    expect(message).toBe('Unable to read authentication account.')
    expect(message).not.toContain('Supabase')
    expect(message).not.toContain('secret')
  })

  it('converts client environment failure into the same controlled error', async () => {
    dbHarness.getClient.mockImplementation(() => {
      throw new Error('SUPABASE_SERVICE_ROLE_KEY contains a raw secret')
    })
    const { getAccountForSessionFreshness } = await import('./auth-accounts')

    await expect(
      getAccountForSessionFreshness(loginRow.id)
    ).rejects.toThrow('Unable to read authentication account.')
  })

  it('keeps runtime source free of wildcard selects and script-only imports', () => {
    const source = fs.readFileSync(
      path.resolve(__dirname, 'auth-accounts.ts'),
      'utf8'
    )

    expect(source).toMatch(/^import 'server-only'/)
    expect(source).not.toContain("select('*')")
    expect(source).not.toContain('select("*")')
    expect(source).not.toContain('script-client.mjs')
  })
})
