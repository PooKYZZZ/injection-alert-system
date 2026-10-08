import { expect, test, type Page } from '@playwright/test'

import type { DashboardStats } from '@/features/stats/types'
import { requireAuthE2EState } from '@/test-support/auth-e2e/state'
import { totpCodeAtTime } from '@/test-support/auth-e2e/totp'

const dashboardStats: DashboardStats = {
  actionable_alerts: 7,
  total_requests: 12,
  counts_by_confidence_tier: {
    critical: 2,
    high: 3,
    medium: 4,
    low: 2,
    informational: 1,
  },
  non_normal_counts_by_confidence_tier: {
    critical: 2,
    high: 3,
    medium: 4,
    low: 2,
    informational: 1,
  },
  avg_inference_latency_ms: 1,
  blocked_count: 4,
  allowed_count: 5,
  throttled_count: 3,
  avg_confidence: 0.91,
  false_positive_rate: 0,
  false_positive_count: 0,
  high_alert_count: 5,
  prev_high_alert_count: 4,
  prev_total_requests: 10,
  prev_blocked_count: 3,
  prev_allowed_count: 5,
  prev_throttled_count: 2,
  activity_buckets: [
    {
      bucket_index: 0,
      total_count: 12,
      blocked_count: 4,
      allowed_count: 5,
      throttled_count: 3,
      timestamp_start: '2026-10-08T09:00:00Z',
      timestamp_end: '2026-10-08T10:00:00Z',
      bucket_width_seconds: 3600,
    },
  ],
  attack_distribution: {
    'SQL Injection': 4,
    'Code Injection': 3,
  },
  top_source_ips: [{ ip: '192.0.2.20', count: 4, action: 'BLOCKED' }],
  top_targeted_paths: [{ path: '/records/search', hits: 5 }],
}

async function installReadOnlyPageFixtures(page: Page): Promise<void> {
  await page.route('**/api/stats**', (route) =>
    route.fulfill({
      status: 200,
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(dashboardStats),
    })
  )
  await page.route('**/api/alerts**', async (route) => {
    const pathname = new URL(route.request().url()).pathname
    if (pathname.endsWith('/stream')) {
      await route.abort()
      return
    }
    if (pathname === '/api/alerts') {
      await route.fulfill({
        status: 200,
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ items: [], total: 0, page: 1, pageSize: 20 }),
      })
      return
    }
    await route.continue()
  })
}

async function signIn(page: Page): Promise<void> {
  const identity = requireAuthE2EState().identities.dashboard
  await page.goto('/login')
  await page.getByLabel('Email or username').fill(identity.email)
  await page.getByLabel('Password').fill(identity.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/mfa\/verify$/)
  await page.getByLabel('Authenticator code').fill(totpCodeAtTime(identity.totpSecret).code)
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

async function toggleTheme(page: Page): Promise<string> {
  const root = page.locator('html')
  const previousTheme = await root.getAttribute('data-theme')
  await page.getByRole('button', { name: /Switch to .* theme/ }).click()
  await expect.poll(() => root.getAttribute('data-theme')).not.toBe(previousTheme)
  await expect(root).not.toHaveClass(/theme-transitioning/)
  return (await root.getAttribute('data-theme')) ?? ''
}

test('theme, dashboard breakdown, and secondary actions stay responsive across navigation', async ({ page }) => {
  await installReadOnlyPageFixtures(page)
  await signIn(page)
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()

  const firstTheme = await toggleTheme(page)
  const secondTheme = await toggleTheme(page)
  expect(secondTheme).not.toBe(firstTheme)

  const breakdown = page.locator('details').filter({ hasText: 'Attack and model breakdown' })
  await expect(breakdown.locator('h2', { hasText: 'Traffic patterns' })).toHaveCount(0)
  await breakdown.locator('summary').click()
  await expect(breakdown.getByRole('heading', { name: 'Traffic patterns' })).toBeVisible()
  await expect(breakdown.getByRole('heading', { name: 'Model and policy context' })).toBeVisible()
  await expect(breakdown.getByRole('heading', { name: 'Confidence by tier' })).toBeVisible()
  await expect(breakdown.getByRole('heading', { name: 'Policy by confidence tier' })).toBeVisible()

  await breakdown.getByRole('button', { name: 'Pie chart', exact: true }).click()
  const pieChart = breakdown.getByRole('img', { name: /Attack type distribution pie chart/ })
  await expect(pieChart.locator('path')).toHaveCount(2, { timeout: 1500 })
  await breakdown.getByRole('button', { name: 'Bar chart', exact: true }).click()
  await expect(breakdown.getByText('SQL Injection')).toBeVisible()

  await page.getByRole('button', { name: '7 days' }).click()
  await expect(page.getByRole('button', { name: '7 days' })).toHaveAttribute('aria-pressed', 'true')

  const trafficHistoryLink = page.locator('nav[aria-label="Dashboard navigation"] a[href="/traffic-history"]').first()
  await expect(trafficHistoryLink).toBeVisible()
  await trafficHistoryLink.click()
  await expect(page.getByRole('button', { name: 'Export CSV', exact: true })).toBeVisible()
  const exportButton = page.getByRole('button', { name: 'Export CSV', exact: true })
  await expect(exportButton).toHaveClass(/border-surface-border/)
  await expect(exportButton).not.toHaveClass(/bg-action-accent/)
  await toggleTheme(page)

  const userManagementLink = page.locator('nav[aria-label="Dashboard navigation"] a[href="/user-management"]').first()
  await expect(userManagementLink).toBeVisible()
  await userManagementLink.click()
  await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible()
  const inviteButton = page.getByRole('button', { name: 'Invite user', exact: true })
  await expect(inviteButton).toHaveClass(/border-border-light/)
  await expect(inviteButton).not.toHaveClass(/bg-accent-action/)
  const themeAfterUserManagement = await toggleTheme(page)

  const dashboardLink = page.locator('nav[aria-label="Dashboard navigation"] a[href="/dashboard"]').first()
  await expect(dashboardLink).toBeVisible()
  await dashboardLink.click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', themeAfterUserManagement)
})
