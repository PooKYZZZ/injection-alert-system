import { defineConfig, devices } from '@playwright/test'

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://127.0.0.1:3000'
const frontendPort = new URL(baseURL).port

export default defineConfig({
  testDir: './e2e',
  testMatch: ['sse-alert-flow.spec.ts'],
  globalSetup: './e2e/auth-global-setup.ts',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: 1,
  reporter: [
    ['html', { outputFolder: 'playwright-report/sse', open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'sse-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: `npm run dev -- --webpack --port ${frontendPort}`,
    url: baseURL,
    reuseExistingServer: false,
    stdout: 'ignore',
    stderr: 'pipe',
    timeout: 300_000,
  },
  outputDir: 'test-results/sse',
  timeout: 90_000,
  expect: {
    timeout: 30_000,
  },
})
