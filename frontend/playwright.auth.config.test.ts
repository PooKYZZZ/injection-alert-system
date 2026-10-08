import { describe, expect, it } from 'vitest'

import authConfig from './playwright.auth.config'

describe('authentication Playwright configuration', () => {
  it('runs the critical auth and theme regression files in Chromium', () => {
    expect(authConfig.testMatch).toEqual([
      'auth-journeys.spec.ts',
      'role-access.spec.ts',
      'theme-switch-performance.spec.ts',
    ])
    expect(authConfig.projects).toHaveLength(1)
    expect(authConfig.projects?.[0].name).toBe('auth-chromium')
  })

  it('uses deterministic setup and a non-reused production webpack server', () => {
    expect(authConfig.globalSetup).toBe('./e2e/auth-global-setup.ts')
    expect(authConfig.workers).toBe(2)
    expect(authConfig.expect?.timeout).toBe(30_000)
    expect(authConfig.webServer).toMatchObject({
      command: 'npm run build -- --webpack && node scripts/start-auth-e2e-standalone.mjs',
      reuseExistingServer: false,
      stdout: 'ignore',
      stderr: 'pipe',
      url: 'http://127.0.0.1:3000',
      timeout: 300_000,
    })
  })

  it('uses an HTML report without raw secret-bearing trace media or server-action stdout', () => {
    expect(authConfig.use).toMatchObject({
      baseURL: 'http://127.0.0.1:3000',
      trace: 'off',
      screenshot: 'off',
      video: 'off',
    })
    expect(authConfig.reporter).toEqual([
      ['html', { outputFolder: 'playwright-report/auth', open: 'never' }],
      ['list'],
    ])
  })
})
