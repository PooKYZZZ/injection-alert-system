import { isUserRole, type UserRole } from './roles'

export type AccountRecord = {
  id: string
  email: string
  name: string
  role: UserRole
  authzVersion: number
  passwordHash: string
}

const ACCOUNT_FIELDS = new Set([
  'id',
  'email',
  'name',
  'role',
  'authz_version',
  'password_hash',
])

const INVALID_REGISTRY_MESSAGE = 'Invalid account registry configuration.'

function invalidRegistry(): never {
  throw new Error(INVALID_REGISTRY_MESSAGE)
}

export function normalizeAccountIdentifier(value: string): string {
  return value.trim().toLowerCase()
}

function requiredString(value: unknown): string {
  if (typeof value !== 'string' || value.trim().length === 0) {
    return invalidRegistry()
  }
  return value.trim()
}

export function parseAccountRegistry(
  rawRegistry: string | undefined
): AccountRecord[] {
  if (!rawRegistry) {
    return invalidRegistry()
  }

  let parsed: unknown
  try {
    parsed = JSON.parse(rawRegistry)
  } catch {
    return invalidRegistry()
  }

  if (!Array.isArray(parsed) || parsed.length === 0) {
    return invalidRegistry()
  }

  const ids = new Set<string>()
  const emails = new Set<string>()

  return parsed.map((value): AccountRecord => {
    if (
      typeof value !== 'object' ||
      value === null ||
      Array.isArray(value) ||
      Object.keys(value).some((key) => !ACCOUNT_FIELDS.has(key)) ||
      'password' in value
    ) {
      return invalidRegistry()
    }

    const id = normalizeAccountIdentifier(requiredString(
      'id' in value ? value.id : undefined
    ))
    const email = normalizeAccountIdentifier(requiredString(
      'email' in value ? value.email : undefined
    ))
    const name = requiredString('name' in value ? value.name : undefined)
    const role = 'role' in value ? value.role : undefined
    const authzVersion =
      'authz_version' in value ? value.authz_version : undefined
    const passwordHash = requiredString(
      'password_hash' in value ? value.password_hash : undefined
    )

    if (
      !isUserRole(role) ||
      !Number.isInteger(authzVersion) ||
      (authzVersion as number) < 1 ||
      ids.has(id) ||
      emails.has(email)
    ) {
      return invalidRegistry()
    }

    ids.add(id)
    emails.add(email)

    return {
      id,
      email,
      name,
      role,
      authzVersion: authzVersion as number,
      passwordHash,
    }
  })
}

export function readAccountRegistry(): AccountRecord[] {
  return parseAccountRegistry(process.env.AUTH_USERS_JSON)
}

export function findAccountByIdentifier(
  accounts: readonly AccountRecord[],
  identifier: string
): AccountRecord | undefined {
  const normalized = normalizeAccountIdentifier(identifier)
  return accounts.find(
    (account) => account.id === normalized || account.email === normalized
  )
}
