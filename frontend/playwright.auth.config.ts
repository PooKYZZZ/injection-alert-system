import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  testMatch: ['auth-journeys.spec.ts'],
  globalSetup: './e2e/auth-global-setup.ts',
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: 2,
  reporter: [
    ['html', { outputFolder: 'playwright-report/auth', open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: 'http://127.0.0.1:3000',
    trace: 'off',
    screenshot: 'off',
    video: 'off',
  },
  projects: [
    {
      name: 'auth-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'npm run dev -- --webpack',
    url: 'http://127.0.0.1:3000',
    reuseExistingServer: false,
    stdout: 'ignore',
    stderr: 'pipe',
    timeout: 120_000,
  },
  outputDir: 'test-results/auth',
  timeout: 90_000,
  expect: {
    timeout: 30_000,
  },
})
