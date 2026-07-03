import { randomBytes, scrypt } from 'node:crypto'
import { promisify } from 'node:util'

// Keep synchronized with frontend/lib/auth/password-hash.ts.
const SCRYPT_N = 131_072
const SCRYPT_R = 8
const SCRYPT_P = 1
const SCRYPT_KEYLEN = 64
const SCRYPT_SALT_BYTES = 32
const SCRYPT_MAXMEM = 268_435_456
const MAX_PASSWORD_LENGTH = 256

const password = process.argv[2]
if (!password || password.length > MAX_PASSWORD_LENGTH) {
  console.error(
    'Usage: node scripts/generate_auth_password_hash.mjs <password>\n' +
      'Warning: a CLI password may be saved in shell history.'
  )
  process.exitCode = 1
} else {
  console.error('Warning: a CLI password may be saved in shell history.')
  const salt = randomBytes(SCRYPT_SALT_BYTES)
  const derive = promisify(scrypt)
  const digest = await derive(password, salt, SCRYPT_KEYLEN, {
    N: SCRYPT_N,
    r: SCRYPT_R,
    p: SCRYPT_P,
    maxmem: SCRYPT_MAXMEM,
  })
  const params =
    `N=${SCRYPT_N},r=${SCRYPT_R},p=${SCRYPT_P},` +
    `keylen=${SCRYPT_KEYLEN},maxmem=${SCRYPT_MAXMEM}`

  console.log(
    [
      'scrypt',
      'v1',
      params,
      salt.toString('base64url'),
      digest.toString('base64url'),
    ].join('$')
  )
}
