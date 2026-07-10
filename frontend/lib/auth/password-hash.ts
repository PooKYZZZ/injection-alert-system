import * as argon2 from 'argon2'

export const ARGON2_MEMORY_COST = 19_456
export const ARGON2_TIME_COST = 2
export const ARGON2_PARALLELISM = 1
export const MAX_PASSWORD_LENGTH = 256
export const PASSWORD_HASH_CONCURRENCY_LIMIT = 2
export const DUMMY_PASSWORD_HASH =
  '$argon2id$v=19$m=19456,t=2,p=1$bN0r/SKG56J5Ob9MOsU6/g$9XJz/v+ujBicSJlqn5EsoyP5yRugqmFdYl3xjxEH5ko'

const ARGON2ID_PHC_PATTERN =
  /^\$argon2id\$v=(\d+)\$m=(\d+),t=(\d+),p=(\d+)\$[A-Za-z0-9+/]+={0,2}\$[A-Za-z0-9+/]+={0,2}$/

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

export function hasApprovedArgon2Parameters(hash: unknown): hash is string {
  if (typeof hash !== 'string') {
    return false
  }
  const match = ARGON2ID_PHC_PATTERN.exec(hash)
  if (!match) {
    return false
  }
  const [, version, memoryCost, timeCost, parallelism] = match
  return (
    Number(version) === 19 &&
    Number(memoryCost) >= ARGON2_MEMORY_COST &&
    Number(timeCost) >= ARGON2_TIME_COST &&
    Number(parallelism) >= ARGON2_PARALLELISM
  )
}

export async function hashPassword(password: string): Promise<string> {
  if (!passwordIsWithinBounds(password)) {
    throw new Error('Password input is invalid.')
  }

  const hash = await argon2.hash(password, ARGON2_OPTIONS)
  if (!hasApprovedArgon2Parameters(hash)) {
    throw new Error('Password hashing failed.')
  }
  return hash
}

export async function verifyPasswordHash(
  hash: string,
  password: string
): Promise<boolean> {
  if (
    !hasApprovedArgon2Parameters(hash) ||
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

export async function verifyPasswordForUnknownAccount(
  password: string
): Promise<void> {
  if (!passwordIsWithinBounds(password)) {
    return
  }
  await verifyPasswordHash(DUMMY_PASSWORD_HASH, password)
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
