import { expect, test } from '@playwright/test'

const reducedMotionViewports = [
  { width: 1440, height: 900, label: 'desktop' },
  { width: 1280, height: 720, label: 'laptop' },
  { width: 1024, height: 768, label: 'small desktop' },
  { width: 768, height: 1024, label: 'tablet' },
  { width: 390, height: 844, label: 'mobile' },
]

test('walks a prepared detection through details and analyst review without API traffic', async ({ page }, testInfo) => {
  const apiRequests: string[] = []
  const browserErrors: string[] = []
  const consoleErrors: string[] = []
  const hostedPolicyNotices: string[] = []
  page.on('request', (request) => {
    if (/\/api\//.test(new URL(request.url()).pathname)) apiRequests.push(request.url())
  })
  page.on('pageerror', (error) => browserErrors.push(error.message))
  page.on('console', (message) => {
    if (message.type() !== 'error') return
    const text = message.text()
    const blockedCloudflareBeacon = Boolean(process.env.PUBLIC_SITE_BASE_URL)
      && text.includes('static.cloudflareinsights.com/beacon.min.js')
      && text.includes('violates the following Content Security Policy directive')
    if (blockedCloudflareBeacon) hostedPolicyNotices.push(text)
    else consoleErrors.push(text)
  })

  await page.setViewportSize({ width: 1440, height: 900 })
  await page.goto('/how-it-works')

  await expect(page.getByRole('heading', { name: 'A clearer path from request to review.' })).toBeVisible()
  await expect(page.getByText('Nothing is sent or saved.')).toBeVisible()
  await expect(page.getByText('GET /catalog/search?q=%27%20OR%20%271%27%3D%271')).toBeVisible()

  await page.getByRole('button', { name: 'Start walkthrough' }).click()
  await expect(page.getByRole('status')).toContainText('Walkthrough complete', { timeout: 10_000 })
  await expect(page.getByText('Security detection', { exact: true })).toBeVisible()
  await page.evaluate(() => {
    if (document.activeElement instanceof HTMLElement) document.activeElement.blur()
  })
  await page.screenshot({ path: testInfo.outputPath('public-demo-desktop.png'), fullPage: true })

  await page.getByRole('button', { name: /Open Traffic Details/ }).click()
  const details = page.getByRole('dialog', { name: /GET \/catalog\/search/ })
  await expect(details).toBeVisible()
  await expect(details.getByRole('heading', { name: 'Firewall evidence' })).toBeVisible()
  await expect(details.getByText('A firewall rule match is included for the SQL injection pattern in this sample.')).toBeVisible()
  await expect(details.getByText('Sample HTTP response')).toBeVisible()
  await expect(details.getByText('403 Forbidden')).toBeVisible()

  await page.waitForTimeout(200)
  await page.screenshot({ path: testInfo.outputPath('public-demo-traffic-details.png') })
  const triage = details.getByRole('combobox', { name: 'Sample review state' })
  await expect(triage).toBeEnabled()
  await triage.selectOption('in_review')
  await expect(triage).toHaveValue('in_review')

  await page.keyboard.press('Escape')
  await expect(details).toBeHidden()
  await expect(page.getByRole('button', { name: /Open Traffic Details/ })).toBeFocused()

  expect(apiRequests).toEqual([])
  expect(browserErrors).toEqual([])
  expect(consoleErrors).toEqual([])
  if (hostedPolicyNotices.length > 0) {
    testInfo.annotations.push({
      type: 'note',
      description: 'Cloudflare Insights beacon is injected at the edge and denied by the site CSP; application console errors remain clear.',
    })
  }
})

test('fits at desktop, tablet, and mobile widths; supports keyboard use and reduced motion', async ({ page }, testInfo) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  for (const viewport of reducedMotionViewports) {
    await page.setViewportSize({ width: viewport.width, height: viewport.height })
    await page.goto('/how-it-works')
    await expect(page.getByText('Reduced motion is on. Move through one stage at a time.')).toBeVisible()

    const codeScenario = page.getByRole('button', { name: /Code injection pattern/ })
    await codeScenario.focus()
    await page.keyboard.press('Enter')
    await expect(page.getByText('POST /feedback')).toBeVisible()

    const wafStep = page.getByRole('button', { name: /WAF/ })
    await wafStep.focus()
    await page.keyboard.press('ArrowRight')
    const modelStep = page.getByRole('button', { name: /ML/ })
    await expect(modelStep).toBeFocused()
    await page.keyboard.press('ArrowLeft')
    await expect(wafStep).toBeFocused()

    await page.getByRole('button', { name: 'Start walkthrough' }).focus()
    await page.keyboard.press('Enter')
    for (let stage = 0; stage < 5; stage += 1) {
      await page.getByRole('button', { name: 'Next stage' }).focus()
      await page.keyboard.press('Enter')
    }

    await expect(page.getByRole('status')).toContainText('Walkthrough complete')
    if (viewport.label === 'mobile') {
      await page.screenshot({ path: testInfo.outputPath('public-demo-mobile.png'), fullPage: true })
    }
    await page.getByRole('button', { name: /Open Traffic Details/ }).click()
    const dialog = page.getByRole('dialog')
    await expect(dialog).toBeVisible()

    const dimensions = await page.evaluate(() => ({
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
    }))
    expect(dimensions.documentWidth, `${viewport.label} horizontal overflow`).toBeLessThanOrEqual(dimensions.viewportWidth)

    const box = await dialog.boundingBox()
    expect(box, `${viewport.label} dialog should have a layout box`).not.toBeNull()
    expect(box!.x).toBeGreaterThanOrEqual(0)
    expect(box!.y).toBeGreaterThanOrEqual(0)
    expect(box!.x + box!.width).toBeLessThanOrEqual(viewport.width + 1)
    expect(box!.y + box!.height).toBeLessThanOrEqual(viewport.height + 1)

    if (viewport.label === 'mobile') {
      await page.screenshot({ path: testInfo.outputPath('public-demo-mobile-details.png') })
    }
    await page.keyboard.press('Escape')
    await expect(dialog).toBeHidden()
  }
})

test('shows Normal as contextual traffic with no triage controls', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' })
  await page.setViewportSize({ width: 1280, height: 800 })
  await page.goto('/how-it-works')
  await page.getByRole('button', { name: /Ordinary search/ }).click()
  await page.getByRole('button', { name: 'Start walkthrough' }).click()
  for (let stage = 0; stage < 5; stage += 1) {
    await page.getByRole('button', { name: 'Next stage' }).click()
  }

  await expect(page.getByText('Normal traffic', { exact: true })).toBeVisible()
  await page.getByRole('button', { name: /Open Traffic Details/ }).click()
  const details = page.getByRole('dialog')
  await expect(details.getByText('Read-only sample')).toBeVisible()
  await expect(details.getByText('No firewall rule match is recorded for this routine catalog search.')).toBeVisible()
  await expect(details.getByText('200 OK')).toBeVisible()
  await expect(details.getByRole('combobox', { name: 'Sample review state' })).toHaveCount(0)
})
