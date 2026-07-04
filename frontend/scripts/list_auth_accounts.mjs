import { pathToFileURL } from 'node:url'

import { createSupabaseScriptClient } from '../lib/server/db/script-client.mjs'

export const SAFE_ACCOUNT_FIELDS =
  'id,email,username,name,role,mfa_required,email_verified_at,disabled_at,created_at,updated_at'

export async function listAuthAccounts(client) {
  const { data, error } = await client
    .from('auth_accounts')
    .select(SAFE_ACCOUNT_FIELDS)
    .order('created_at', { ascending: true })
  if (error) throw new Error('Unable to list accounts.')
  return data.map((account) => ({
    ...account,
    email_verified_at: account.email_verified_at ? 'present' : 'not present',
  }))
}

async function main() {
  console.log(JSON.stringify(await listAuthAccounts(createSupabaseScriptClient())))
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : 'Unable to list accounts.')
    process.exitCode = 1
  })
}
