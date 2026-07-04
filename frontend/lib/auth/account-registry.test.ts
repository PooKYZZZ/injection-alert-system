import { afterEach, describe, expect, it } from 'vitest'

import { ROLES } from './roles'
import {
  findAccountByIdentifier,
  normalizeAccountIdentifier,
  parseAccountRegistry,
  readAccountRegistry,
} from './account-registry'

const originalRegistry = process.env.AUTH_USERS_JSON

function account(overrides: Record<string, unknown> = {}) {
  return {
    id: 'analyst-1',
    email: 'analyst@example.test',
    name: 'SOC Analyst',
    role: ROLES.ANALYST,
    authz_version: 1,
    password_hash: 'scrypt$v1$valid-for-registry-parsing',
    ...overrides,
  }
}

afterEach(() => {
  if (originalRegistry === undefined) {
    delete process.env.AUTH_USERS_JSON
  } else {
    process.env.AUTH_USERS_JSON = originalRegistry
  }
})

describe('account registry', () => {
  it('parses a valid registry and normalizes ids and emails', () => {
    const accounts = parseAccountRegistry(
      JSON.stringify([
        account({
          id: '  Analyst-1 ',
          email: ' Analyst@Example.Test ',
        }),
      ])
    )

    expect(accounts).toEqual([
      {
        id: 'analyst-1',
        email: 'analyst@example.test',
        name: 'SOC Analyst',
        role: ROLES.ANALYST,
        authzVersion: 1,
        passwordHash: 'scrypt$v1$valid-for-registry-parsing',
      },
    ])
  })

  it.each([
    ['missing registry', undefined],
    ['invalid JSON', '{not-json'],
    ['non-array JSON', '{}'],
    ['empty registry', '[]'],
  ])('fails closed for %s', (_label, rawRegistry) => {
    expect(() => parseAccountRegistry(rawRegistry)).toThrow(
      'Invalid account registry configuration.'
    )
  })

  it('rejects duplicate email case-insensitively', () => {
    const raw = JSON.stringify([
      account(),
      account({
        id: 'analyst-2',
        email: 'ANALYST@EXAMPLE.TEST',
      }),
    ])

    expect(() => parseAccountRegistry(raw)).toThrow(
      'Invalid account registry configuration.'
    )
  })

  it('rejects duplicate id after normalization', () => {
    const raw = JSON.stringify([
      account(),
      account({
        id: ' ANALYST-1 ',
        email: 'other@example.test',
      }),
    ])

    expect(() => parseAccountRegistry(raw)).toThrow(
      'Invalid account registry configuration.'
    )
  })

  it.each([
    ['invalid role', { role: 'OWNER' }],
    ['missing authz_version', { authz_version: undefined }],
    ['zero authz_version', { authz_version: 0 }],
    ['negative authz_version', { authz_version: -1 }],
    ['plaintext password', { password: 'secret' }],
    ['missing password_hash', { password_hash: undefined }],
    ['unknown field', { nickname: 'Analyst' }],
  ])('rejects %s', (_label, overrides) => {
    expect(() =>
      parseAccountRegistry(JSON.stringify([account(overrides)]))
    ).toThrow('Invalid account registry configuration.')
  })

  it('does not include raw registry data in errors', () => {
    const secret = 'must-not-appear-in-errors'
    const raw = JSON.stringify([account({ password: secret })])

    try {
      parseAccountRegistry(raw)
      throw new Error('expected parsing to fail')
    } catch (error) {
      expect(String(error)).not.toContain(secret)
      expect(String(error)).not.toContain(raw)
    }
  })

  it('uses the same normalization for validation and lookup', () => {
    const accounts = parseAccountRegistry(JSON.stringify([account()]))

    expect(normalizeAccountIdentifier(' ANALYST@EXAMPLE.TEST ')).toBe(
      'analyst@example.test'
    )
    expect(findAccountByIdentifier(accounts, ' ANALYST-1 ')).toBe(accounts[0])
    expect(findAccountByIdentifier(accounts, ' ANALYST@EXAMPLE.TEST ')).toBe(
      accounts[0]
    )
  })

  it('reads AUTH_USERS_JSON fresh on each call', () => {
    process.env.AUTH_USERS_JSON = JSON.stringify([account()])
    expect(readAccountRegistry()[0]?.role).toBe(ROLES.ANALYST)

    process.env.AUTH_USERS_JSON = JSON.stringify([
      account({ role: ROLES.VIEWER }),
    ])
    expect(readAccountRegistry()[0]?.role).toBe(ROLES.VIEWER)
  })
})
