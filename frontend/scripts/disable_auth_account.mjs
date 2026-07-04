import { pathToFileURL } from 'node:url'

import { createSupabaseScriptClient } from '../lib/server/db/script-client.mjs'

function selector(query, values) {
  if (values.id) return query.eq('id', values.id)
  if (values.email) return query.eq('email', values.email.trim().toLowerCase())
  throw new Error('Specify --id or --email.')
}

export async function disableAuthAccount(client, values) {
  const lookup = selector(
    client.from('auth_accounts').select('id,email,authz_version'),
    values
  )
  const { data: account, error: lookupError } = await lookup.maybeSingle()
  if (lookupError) throw new Error('Unable to find account.')
  if (!account) throw new Error('Account not found.')

  const update = buildDisableUpdate(account.authz_version)
  const { data, error } = await client
    .from('auth_accounts')
    .update(update)
    .eq('id', account.id)
    .select('id,email,disabled_at,authz_version,updated_at')
    .single()
  if (error) throw new Error('Unable to disable account.')
  return data
}

export function buildDisableUpdate(authzVersion) {
  return {
    disabled_at: new Date().toISOString(),
    authz_version: authzVersion + 1,
  }
}

function parseSelector(argv) {
  if (argv.length !== 2 || !['--id', '--email'].includes(argv[0])) {
    throw new Error('Usage: node scripts/disable_auth_account.mjs --id|--email <value>')
  }
  return { [argv[0].slice(2)]: argv[1] }
}

async function main() {
  console.log(
    JSON.stringify(
      await disableAuthAccount(
        createSupabaseScriptClient(),
        parseSelector(process.argv.slice(2))
      )
    )
  )
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : 'Unable to disable account.')
    process.exitCode = 1
  })
}
