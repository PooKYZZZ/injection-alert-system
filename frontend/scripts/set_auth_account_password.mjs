import argon2 from 'argon2'
import { pathToFileURL } from 'node:url'

import { createSupabaseScriptClient } from '../lib/server/db/script-client.mjs'

export async function buildPasswordUpdate(password, authzVersion) {
  if (
    typeof password !== 'string' ||
    password.length === 0 ||
    password.length > 256
  ) {
    throw new Error('Password must contain 1 to 256 characters.')
  }
  return {
    password_hash: await argon2.hash(password, {
      type: argon2.argon2id,
      memoryCost: 19_456,
      timeCost: 2,
      parallelism: 1,
    }),
    password_set_at: new Date().toISOString(),
    authz_version: authzVersion + 1,
  }
}

export async function setAuthAccountPassword(client, values) {
  let lookup = client.from('auth_accounts').select('id,email,authz_version')
  if (values.id) lookup = lookup.eq('id', values.id)
  else if (values.email) lookup = lookup.eq('email', values.email.toLowerCase())
  else throw new Error('Specify --id or --email.')
  const { data: account, error: lookupError } = await lookup.maybeSingle()
  if (lookupError) throw new Error('Unable to find account.')
  if (!account) throw new Error('Account not found.')

  const update = await buildPasswordUpdate(values.password, account.authz_version)
  const { data, error } = await client
    .from('auth_accounts')
    .update(update)
    .eq('id', account.id)
    .select('id,email,password_set_at,authz_version,updated_at')
    .single()
  if (error) throw new Error('Unable to set account password.')
  return data
}

function parseArgs(argv) {
  const values = {}
  for (let index = 0; index < argv.length; index += 2) {
    if (!argv[index]?.startsWith('--') || argv[index + 1] === undefined) {
      throw new Error('Use --id or --email together with --password.')
    }
    values[argv[index].slice(2)] = argv[index + 1]
  }
  if (!values.password || (!values.id && !values.email)) {
    throw new Error('Use --id or --email together with --password.')
  }
  return values
}

async function main() {
  console.log(
    JSON.stringify(
      await setAuthAccountPassword(
        createSupabaseScriptClient(),
        parseArgs(process.argv.slice(2))
      )
    )
  )
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : 'Unable to set password.')
    process.exitCode = 1
  })
}
