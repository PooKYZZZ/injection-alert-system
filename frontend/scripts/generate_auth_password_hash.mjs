import argon2 from 'argon2'
import { pathToFileURL } from 'node:url'

export const MAX_PASSWORD_LENGTH = 256
export const ARGON2_OPTIONS = {
  type: argon2.argon2id,
  memoryCost: 19_456,
  timeCost: 2,
  parallelism: 1,
}

export async function generatePasswordHash(password) {
  if (
    typeof password !== 'string' ||
    password.length === 0 ||
    password.length > MAX_PASSWORD_LENGTH
  ) {
    throw new Error('Password must contain 1 to 256 characters.')
  }
  return argon2.hash(password, ARGON2_OPTIONS)
}

async function main() {
  if (process.argv.length !== 3) {
    throw new Error('Usage: node scripts/generate_auth_password_hash.mjs <password>')
  }
  console.log(await generatePasswordHash(process.argv[2]))
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : 'Unable to generate hash.')
    process.exitCode = 1
  })
}
