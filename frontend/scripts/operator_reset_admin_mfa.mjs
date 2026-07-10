import { pathToFileURL } from 'node:url'

import { createSupabaseScriptClient } from '../lib/server/db/script-client.mjs'

export async function operatorResetAdminMfa(client, values) {
  if (values.confirmation !== 'CYBERTRACE_BREAK_GLASS') {
    throw new Error('Explicit break-glass confirmation is required.')
  }
  if (!values.id || !values.reason || values.reason.length > 128) {
    throw new Error('Specify --id and a bounded --reason.')
  }
  const { error } = await client.rpc('operator_reset_admin_mfa', {
    p_target_account_id: values.id,
    p_confirmation: values.confirmation,
    p_reason: values.reason,
  })
  if (error) throw new Error('Operator ADMIN recovery failed.')
  return { status: 'reset' }
}

function parseArgs(argv) {
  const values = {
    id: undefined,
    reason: undefined,
    confirmation: process.env.CYBERTRACE_OPERATOR_RECOVERY_CONFIRM,
  }
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index]
    const value = argv[index + 1]
    if (!['--id', '--reason'].includes(flag) || !value) {
      throw new Error('Usage: node scripts/operator_reset_admin_mfa.mjs --id <uuid> --reason <text>')
    }
    values[flag.slice(2)] = value
  }
  return values
}

async function main() {
  const result = await operatorResetAdminMfa(
    createSupabaseScriptClient(),
    parseArgs(process.argv.slice(2))
  )
  console.log(JSON.stringify(result))
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  main().catch((error) => {
    console.error(error instanceof Error ? error.message : 'Operator ADMIN recovery failed.')
    process.exitCode = 1
  })
}
