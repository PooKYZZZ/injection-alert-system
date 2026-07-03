import * as crypto from 'node:crypto'

export const SCRYPT_N = 131_072
export const SCRYPT_R = 8
export const SCRYPT_P = 1
export const SCRYPT_KEYLEN = 64
export const SCRYPT_SALT_BYTES = 32
export const SCRYPT_MAXMEM = 268_435_456
export const SCRYPT_CONCURRENCY_LIMIT = 2
export const MAX_PASSWORD_LENGTH = 256

const SCRYPT_VERSION = 'v1'
const SCRYPT_PARAMS =
  `N=${SCRYPT_N},r=${SCRYPT_R},p=${SCRYPT_P},` +
  `keylen=${SCRYPT_KEYLEN},maxmem=${SCRYPT_MAXMEM}`

export const DUMMY_PASSWORD_HASH =
  'scrypt$v1$N=131072,r=8,p=1,keylen=64,maxmem=268435456$' +
  'cGhhc2UyLWR1bW15LXNhbHQtMzItYnl0ZS12YWx1ZSE$' +
  'zb4dxl8edJC0zJ8H5aa6A7Bh9pP01oQjiwhlHhiZFHtkGSuhdTFFABQArJmq6DfIx4lJVaa2UXrFgfst__5YAQ'

type ParsedHash = {
  salt: Buffer
  digest: Buffer
}

function isBase64Url(value: string): boolean {
  return value.length > 0 && /^[A-Za-z0-9_-]+$/.test(value)
}

function parsePasswordHash(encoded: string): ParsedHash | null {
  const parts = encoded.split('$')
  if (
    parts.length !== 5 ||
    parts[0] !== 'scrypt' ||
    parts[1] !== SCRYPT_VERSION ||
    parts[2] !== SCRYPT_PARAMS ||
    !isBase64Url(parts[3]) ||
    !isBase64Url(parts[4])
  ) {
    return null
  }

  const salt = Buffer.from(parts[3], 'base64url')
  const digest = Buffer.from(parts[4], 'base64url')
  if (
    salt.length < 16 ||
    digest.length !== SCRYPT_KEYLEN ||
    salt.toString('base64url') !== parts[3] ||
    digest.toString('base64url') !== parts[4]
  ) {
    return null
  }

  return { salt, digest }
}

function deriveKey(password: string, salt: Buffer): Promise<Buffer> {
  return new Promise((resolve, reject) => {
    crypto.scrypt(
      password,
      salt,
      SCRYPT_KEYLEN,
      {
        N: SCRYPT_N,
        r: SCRYPT_R,
        p: SCRYPT_P,
        maxmem: SCRYPT_MAXMEM,
      },
      (error, derivedKey) => {
        if (error) {
          reject(error)
        } else {
          resolve(derivedKey)
        }
      }
    )
  })
}

function passwordIsWithinBounds(password: unknown): password is string {
  return typeof password === 'string' && password.length <= MAX_PASSWORD_LENGTH
}

export async function hashPassword(password: string): Promise<string> {
  if (!passwordIsWithinBounds(password)) {
    throw new Error('Password input is invalid.')
  }

  const salt = crypto.randomBytes(SCRYPT_SALT_BYTES)
  const digest = await deriveKey(password, salt)
  return [
    'scrypt',
    SCRYPT_VERSION,
    SCRYPT_PARAMS,
    salt.toString('base64url'),
    digest.toString('base64url'),
  ].join('$')
}

export async function verifyPasswordHash(
  password: string,
  encodedHash: string
): Promise<boolean> {
  if (!passwordIsWithinBounds(password)) {
    return false
  }

  const parsed = parsePasswordHash(encodedHash)
  if (!parsed) {
    return false
  }

  try {
    const actual = await deriveKey(password, parsed.salt)
    return crypto.timingSafeEqual(actual, parsed.digest)
  } catch {
    return false
  }
}

export async function verifyPasswordForAccount(
  password: string,
  accountPasswordHash: string | null | undefined
): Promise<boolean> {
  const verified = await verifyPasswordHash(
    password,
    accountPasswordHash ?? DUMMY_PASSWORD_HASH
  )
  return accountPasswordHash ? verified : false
}
