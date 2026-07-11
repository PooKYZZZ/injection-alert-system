import { describe, expect, it } from 'vitest'

import baseConfig from './playwright.config'
import authConfig from './playwright.auth.config'

describe('authentication Playwright configuration', () => {
  it('keeps auth journeys out of the generic multi-browser suite', () => {
    expect(baseConfig.testIgnore).toEqual(['auth-journeys.spec.ts'])
  })

  it('runs only the critical auth file in the supported Chromium browser', () => {
    expect(authConfig.testMatch).toEqual(['auth-journeys.spec.ts'])
    expect(authConfig.projects).toHaveLength(1)
    expect(authConfig.projects?.[0].name).toBe('auth-chromium')
  })

  it('uses deterministic setup and a non-reused webpack application server', () => {
    expect(authConfig.globalSetup).toBe('./e2e/auth-global-setup.ts')
    expect(authConfig.workers).toBe(2)
    expect(authConfig.expect?.timeout).toBe(30_000)
    expect(authConfig.webServer).toMatchObject({
      command: 'npm run dev -- --webpack',
      reuseExistingServer: false,
      stdout: 'ignore',
      stderr: 'pipe',
      url: 'http://127.0.0.1:3000',
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
