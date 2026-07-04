import * as argon2 from 'argon2'

export const ARGON2_MEMORY_COST = 19_456
export const ARGON2_TIME_COST = 2
export const ARGON2_PARALLELISM = 1
export const MAX_PASSWORD_LENGTH = 256
export const PASSWORD_HASH_CONCURRENCY_LIMIT = 2

const ARGON2_OPTIONS = {
  type: argon2.argon2id,
  memoryCost: ARGON2_MEMORY_COST,
  timeCost: ARGON2_TIME_COST,
  parallelism: ARGON2_PARALLELISM,
} as const

function passwordIsWithinBounds(password: unknown): password is string {
  return (
    typeof password === 'string' &&
    password.length > 0 &&
    password.length <= MAX_PASSWORD_LENGTH
  )
}

export async function hashPassword(password: string): Promise<string> {
  if (!passwordIsWithinBounds(password)) {
    throw new Error('Password input is invalid.')
  }

  const hash = await argon2.hash(password, ARGON2_OPTIONS)
  if (!hash.startsWith('$argon2id$')) {
    throw new Error('Password hashing failed.')
  }
  return hash
}

export async function verifyPasswordHash(
  hash: string,
  password: string
): Promise<boolean> {
  if (
    typeof hash !== 'string' ||
    !hash.startsWith('$argon2id$') ||
    !passwordIsWithinBounds(password)
  ) {
    return false
  }

  try {
    return await argon2.verify(hash, password)
  } catch {
    return false
  }
}

const dummyPasswordHash = hashPassword(
  'CyberTrace fixed dummy password used only for timing equalization'
)

export async function verifyPasswordForUnknownAccount(
  password: string
): Promise<void> {
  if (!passwordIsWithinBounds(password)) {
    return
  }
  await verifyPasswordHash(await dummyPasswordHash, password)
}

export async function verifyPasswordForAccount(
  password: string,
  accountPasswordHash: string | null | undefined
): Promise<boolean> {
  if (!accountPasswordHash) {
    await verifyPasswordForUnknownAccount(password)
    return false
  }
  return verifyPasswordHash(accountPasswordHash, password)
}
