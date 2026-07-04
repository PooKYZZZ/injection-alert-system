import argon2 from 'argon2'
import { pathToFileURL } from 'node:url'

import { createSupabaseScriptClient } from '../lib/server/db/script-client.mjs'

const ROLES = new Set(['ADMIN', 'ANALYST', 'VIEWER'])
const MAX_PASSWORD_LENGTH = 256

function readArgs(argv) {
  const result = {}
  for (let index = 0; index < argv.length; index += 2) {
    const key = argv[index]
    if (!key?.startsWith('--') || argv[index + 1] === undefined) {
      throw new Error('Use --email, --name, --role, and optional value flags.')
    }
    result[key.slice(2)] = argv[index + 1]
  }
  return result
}

function parseBoolean(value, name) {
  if (value === undefined) return undefined
  if (value === 'true') return true
  if (value === 'false') return false
  throw new Error(`${name} must be true or false.`)
}

export async function buildCreateAccountPayload(values) {
  const email = values.email?.trim().toLowerCase()
  const name = values.name?.trim()
  const role = values.role?.trim()
  const username = values.username?.trim().toLowerCase() || null
  if (!email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    throw new Error('A valid email is required.')
  }
  if (!name) throw new Error('Name is required.')
  if (!ROLES.has(role)) throw new Error('Role must be ADMIN, ANALYST, or VIEWER.')

  const password = values.password
  if (
    password !== undefined &&
    (password.length === 0 || password.length > MAX_PASSWORD_LENGTH)
  ) {
    throw new Error('Password must contain 1 to 256 characters.')
  }
  const now = new Date().toISOString()
  const mfaOverride = parseBoolean(values['mfa-required'], 'mfa-required')
  const emailVerified = parseBoolean(values['email-verified'], 'email-verified')
  const passwordHash = password
    ? await argon2.hash(password, {
        type: argon2.argon2id,
        memoryCost: 19_456,
        timeCost: 2,
        parallelism: 1,
      })
    : null

  return {
    email,
    username,
    name,
    role,
    authz_version: 1,
    password_hash: passwordHash,
    password_set_at: passwordHash ? now : null,
    email_verified_at: emailVerified ? now : null,
    mfa_required: mfaOverride ?? role !== 'VIEWER',
  }
}

export async function createAuthAccount(client, values) {
  const payload = await buildCreateAccountPayload(values)
  const { data, error } = await client
    .from('auth_accounts')
    .insert(payload)
    .select(
      'id,email,username,name,role,mfa_required,email_verified_at,created_at'
    )
    .single()
  if (error) {
    if (error.code === '23505') throw new Error('Email or username already exists.')
    throw new Error('Unable to create account.')
  }
  return {
    ...data,
    email_verified_at: data.email_verified_at ? 'present' : 'not present',
  }
}

async function main() {
  const result = await createAuthAccount(
    createSupabaseScriptClient(),
    readArgs(process.argv.slice(2))
  )
  console.log(JSON.stringify({ status: 'created account', ...result }))
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : 'Unable to create account.')
    process.exitCode = 1
  })
}
