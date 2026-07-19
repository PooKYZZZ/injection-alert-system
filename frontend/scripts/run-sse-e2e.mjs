import { runManagedAuthE2E } from './auth-e2e-environment.mjs'

try {
  await runManagedAuthE2E([], {
    realApi: true,
    playwrightConfig: 'playwright.sse.config.ts',
  })
  console.log('SSE_E2E: PASS')
} catch {
  console.error('SSE_E2E: FAIL')
  process.exitCode ||= 1
}
