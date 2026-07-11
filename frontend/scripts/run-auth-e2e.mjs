import { runManagedAuthE2E } from './auth-e2e-environment.mjs'

try {
  await runManagedAuthE2E(process.argv.slice(2))
} catch (error) {
  const message = error instanceof Error ? error.message : 'Unknown E2E failure.'
  console.error(`AUTH_E2E: FAIL — ${message}`)
  process.exitCode = 1
}
