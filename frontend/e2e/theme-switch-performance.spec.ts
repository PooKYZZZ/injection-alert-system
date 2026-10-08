import { expect, test, type Locator, type Page } from '@playwright/test'

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
  const identity = requireAuthE2EState().identities.login
  await page.goto('/login')
  await page.getByLabel('Email or username').fill(identity.email)
  await page.getByLabel('Password').fill(identity.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/mfa\/verify$/)
  await page.getByLabel('Authenticator code').fill(totpCodeAtTime(identity.totpSecret).code)
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

async function startThemeTransitionRecording(page: Page): Promise<void> {
  await page.evaluate(() => {
    const root = document.documentElement
    root.dataset.themeTestTransitions = ''
    document.addEventListener(
      'transitionrun',
      (event) => {
        const property = (event as TransitionEvent).propertyName
        root.dataset.themeTestTransitions = [
          root.dataset.themeTestTransitions,
          property,
        ]
          .filter(Boolean)
          .join(',')
      },
      true
    )
    document.addEventListener(
      'click',
      (event) => {
        const target = event.target
        if (!(target instanceof Element) || !target.closest('button[aria-label^="Switch to "]')) return
        root.dataset.themeTestClickAt = String(performance.now())
        root.dataset.themeTestCommitMs = ''
      },
      true
    )
    new MutationObserver((records) => {
      if (
        records.some((record) => record.attributeName === 'data-theme') &&
        root.dataset.themeTestClickAt
      ) {
        root.dataset.themeTestCommitMs = String(
          performance.now() - Number(root.dataset.themeTestClickAt)
        )
        root.dataset.themeTestClickAt = ''
      }
    }).observe(root, { attributes: true, attributeFilter: ['data-theme'] })
  })
}

async function toggleThemeAndMeasure(
  page: Page,
  clickMode: 'pointer' | 'programmatic' = 'pointer'
): Promise<{ theme: string; handlerMs: number }> {
  const root = page.locator('html')
  const previousTheme = await root.getAttribute('data-theme')
  const themeButton = page.getByRole('button', { name: /Switch to .* theme/ })
  await expect(themeButton).toBeVisible()
  if (clickMode === 'pointer') {
    await themeButton.hover()
    await page.waitForTimeout(180)
  }
  await page.evaluate(() => {
    document.documentElement.dataset.themeTestTransitions = ''
    document.documentElement.dataset.themeTestCommitMs = ''
  })

  if (clickMode === 'programmatic') {
    await themeButton.evaluate((element) => {
      // Activate the React click handler without moving the pointer or focus
      // away from an open, hover-triggered information disclosure.
      element.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }))
    })
  } else {
    await themeButton.click()
  }
  await expect.poll(() => root.getAttribute('data-theme')).not.toBe(previousTheme)
  await expect(root).not.toHaveClass(/theme-switching/)
  await page.waitForTimeout(180)
  expect(await root.getAttribute('data-theme-test-transitions')).toBe('')
  const theme = (await root.getAttribute('data-theme')) ?? ''
  const handlerMs = Number(await root.getAttribute('data-theme-test-commit-ms'))
  expect(Number.isFinite(handlerMs)).toBe(true)
  expect(handlerMs).toBeLessThan(100)
  return { theme, handlerMs }
}

async function expectOpenDisclosureToUseCurrentTheme(
  trigger: Locator,
  requireHover = false
): Promise<void> {
  const colors = await trigger.evaluate((element) => {
    const root = document.documentElement
    const popover = document.getElementById(element.getAttribute('aria-controls') ?? '')
    const icon = element.querySelector('svg circle')
    const title = popover?.querySelector('p')
    if (!(popover instanceof HTMLElement) || !(icon instanceof SVGElement) || !(title instanceof HTMLElement)) {
      throw new Error('Expected an open information disclosure with its icon and title.')
    }

    const resolveToken = (property: string, kind: 'color' | 'backgroundColor') => {
      const probe = document.createElement('span')
      const token = getComputedStyle(root).getPropertyValue(property).trim()
      probe.style[kind] = token
      document.body.appendChild(probe)
      const resolved = getComputedStyle(probe)[kind]
      probe.remove()
      return resolved
    }

    return {
      theme: root.getAttribute('data-theme'),
      panel: getComputedStyle(popover).backgroundColor,
      expectedPanel: resolveToken('--theme-bg-panel', 'backgroundColor'),
      popoverBorder: getComputedStyle(popover).borderTopColor,
      expectedBorder: resolveToken('--theme-border-default', 'color'),
      popoverText: getComputedStyle(popover).color,
      expectedSecondary: resolveToken('--theme-text-secondary', 'color'),
      titleText: getComputedStyle(title).color,
      expectedPrimary: resolveToken('--theme-text-primary', 'color'),
      triggerBorder: getComputedStyle(element).borderTopColor,
      expectedTriggerBorders: [
        resolveToken('--theme-border-default', 'color'),
        resolveToken('--theme-accent-action', 'color'),
      ],
      triggerText: getComputedStyle(element).color,
      expectedTriggerTexts: [
        resolveToken('--theme-text-secondary', 'color'),
        resolveToken('--theme-text-primary', 'color'),
      ],
      iconStroke: getComputedStyle(icon).stroke,
      hovered: element.matches(':hover'),
    }
  })

  expect(colors.theme).toMatch(/^(light|dark)$/)
  expect(colors.panel).toBe(colors.expectedPanel)
  expect(colors.popoverBorder).toBe(colors.expectedBorder)
  expect(colors.popoverText).toBe(colors.expectedSecondary)
  expect(colors.titleText).toBe(colors.expectedPrimary)
  expect(colors.expectedTriggerBorders).toContain(colors.triggerBorder)
  expect(colors.expectedTriggerTexts).toContain(colors.triggerText)
  expect(colors.iconStroke).toBe(colors.triggerText)
  if (requireHover) {
    expect(colors.hovered).toBe(true)
    expect(colors.triggerBorder).toBe(colors.expectedTriggerBorders[1])
    expect(colors.triggerText).toBe(colors.expectedTriggerTexts[1])
  }
}

async function expectEveryDisclosureToUseCurrentTheme(page: Page): Promise<number> {
  const triggers = page.locator('button[aria-label^="About "]')
  const count = await triggers.count()

  for (let index = 0; index < count; index += 1) {
    const trigger = triggers.nth(index)
    await trigger.scrollIntoViewIfNeeded()
    await trigger.click()
    await expect(trigger).toHaveAttribute('aria-expanded', 'true')
    await expectOpenDisclosureToUseCurrentTheme(trigger)
    await trigger.press('Escape')
    await expect(trigger).toHaveAttribute('aria-expanded', 'false')
  }

  return count
}

test('theme changes and dashboard charts stay immediate across affected pages', async ({ page }) => {
  await installReadOnlyPageFixtures(page)
  await signIn(page)
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await startThemeTransitionRecording(page)

  const disclosure = page.getByRole('button', { name: 'About Recorded actions' })
  await disclosure.hover()
  await page.waitForTimeout(180)
  // Hover opens the disclosure; leave the pointer over it while the theme
  // button's click handler is activated without moving focus or the pointer.
  await expect(page.getByRole('region', { name: 'Recorded actions explanation' })).toBeVisible()

  const themeHandlerTimes: number[] = []
  const firstDashboardTheme = await toggleThemeAndMeasure(page, 'programmatic')
  themeHandlerTimes.push(firstDashboardTheme.handlerMs)
  await expectOpenDisclosureToUseCurrentTheme(disclosure, true)
  await disclosure.press('Escape')
  expect(await expectEveryDisclosureToUseCurrentTheme(page)).toBeGreaterThan(0)
  await disclosure.click()
  await expect(page.getByRole('region', { name: 'Recorded actions explanation' })).toBeVisible()
  const secondDashboardTheme = await toggleThemeAndMeasure(page, 'programmatic')
  themeHandlerTimes.push(secondDashboardTheme.handlerMs)
  await expectOpenDisclosureToUseCurrentTheme(disclosure, true)
  await disclosure.press('Escape')
  expect(await expectEveryDisclosureToUseCurrentTheme(page)).toBeGreaterThan(0)
  expect(secondDashboardTheme.theme).not.toBe(firstDashboardTheme.theme)

  // Also exercise a real pointer activation. Moving the pointer to the theme
  // button naturally dismisses the hover disclosure, so reopen it afterward
  // to verify its tokens in the resulting theme.
  const pointerTheme = await toggleThemeAndMeasure(page)
  themeHandlerTimes.push(pointerTheme.handlerMs)
  await disclosure.hover()
  await page.waitForTimeout(180)
  await expectOpenDisclosureToUseCurrentTheme(disclosure, true)

  const breakdown = page.locator('details').filter({ hasText: 'Attack and model breakdown' })
  await expect(breakdown.locator('h2', { hasText: 'Traffic patterns' })).toHaveCount(0)
  await breakdown.locator('summary').click()
  await expect(breakdown.getByRole('heading', { name: 'Traffic patterns' })).toBeVisible()
  await expect(breakdown.getByRole('heading', { name: 'Model and policy context' })).toBeVisible()
  await expect(breakdown.getByRole('heading', { name: 'Confidence by tier' })).toBeVisible()
  await expect(breakdown.getByRole('heading', { name: 'Policy by confidence tier' })).toBeVisible()
  expect(await expectEveryDisclosureToUseCurrentTheme(page)).toBeGreaterThan(0)

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

  const trafficDisclosure = page.getByRole('button', { name: /^About / }).first()
  const trafficDisclosureName = (await trafficDisclosure.getAttribute('aria-label')) ?? 'About Triage'
  await trafficDisclosure.hover()
  await page.waitForTimeout(180)
  await trafficDisclosure.click()
  await expect(
    page.getByRole('region', {
      name: `${trafficDisclosureName?.replace(/^About\s+/, '')} explanation`,
    })
  ).toBeVisible()
  const trafficTheme = await toggleThemeAndMeasure(page, 'programmatic')
  themeHandlerTimes.push(trafficTheme.handlerMs)
  await expectOpenDisclosureToUseCurrentTheme(trafficDisclosure, true)
  await trafficDisclosure.press('Escape')
  expect(await expectEveryDisclosureToUseCurrentTheme(page)).toBeGreaterThan(0)

  const userManagementLink = page.locator('nav[aria-label="Dashboard navigation"] a[href="/user-management"]').first()
  await expect(userManagementLink).toBeVisible()
  await userManagementLink.click()
  await expect(page.getByRole('heading', { name: 'User Management' })).toBeVisible()
  await expect(page.getByRole('button', { name: 'Invite user', exact: true })).toBeVisible()
  expect(await expectEveryDisclosureToUseCurrentTheme(page)).toBe(0)
  const userManagementTheme = await toggleThemeAndMeasure(page)
  themeHandlerTimes.push(userManagementTheme.handlerMs)

  const dashboardLink = page.locator('nav[aria-label="Dashboard navigation"] a[href="/dashboard"]').first()
  await expect(dashboardLink).toBeVisible()
  await dashboardLink.click()
  await expect(page.getByRole('heading', { name: 'Dashboard' })).toBeVisible()
  await expect(page.locator('html')).toHaveAttribute('data-theme', userManagementTheme.theme)

  expect(Math.max(...themeHandlerTimes)).toBeLessThan(100)
})
