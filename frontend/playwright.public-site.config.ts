import { defineConfig, devices } from '@playwright/test'

const publicSiteBaseUrl = process.env.PUBLIC_SITE_BASE_URL
const localBaseUrl = 'http://127.0.0.1:3102'

export default defineConfig({
  testDir: './e2e',
  testMatch: 'public-site-simulation.spec.ts',
  fullyParallel: false,
  forbidOnly: Boolean(process.env.CI),
  retries: 0,
  workers: 1,
  reporter: [['list']],
  outputDir: 'test-results/public-site-simulation',
  use: {
    baseURL: publicSiteBaseUrl ?? localBaseUrl,
    ...(publicSiteBaseUrl
      ? {}
      : { extraHTTPHeaders: { 'x-forwarded-host': 'cybertracesystems.com' } }),
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    {
      name: 'public-site-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  ...(publicSiteBaseUrl
    ? {}
    : {
        webServer: {
          command: 'npm run dev -- --webpack --hostname 127.0.0.1 --port 3102',
          url: localBaseUrl,
          reuseExistingServer: !process.env.CI,
          timeout: 300_000,
          stdout: 'ignore' as const,
          stderr: 'pipe' as const,
        },
      }),
  timeout: 30_000,
  expect: { timeout: 10_000 },
})
