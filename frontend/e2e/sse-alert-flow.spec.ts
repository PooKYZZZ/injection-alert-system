import {
  expect,
  test,
  type Page,
} from '@playwright/test'
import { readFile } from 'node:fs/promises'

import { totpCodeAtTime } from '@/test-support/auth-e2e/totp'
import { requireAuthE2EState } from '@/test-support/auth-e2e/state'

type AlertsPayload = {
  items?: Array<{ request_path?: string | null }>
}

async function signInWithMfa(page: Page): Promise<void> {
  const identity = requireAuthE2EState().roleMatrix.analyst
  await page.goto('/login')
  await page.getByLabel('Email or username').fill(identity.email)
  await page.getByLabel('Password').fill(identity.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
  await expect(page).toHaveURL(/\/mfa\/verify$/)
  await page
    .getByLabel('Authenticator code')
    .fill(totpCodeAtTime(identity.totpSecret).code)
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
}

test('a committed WAF alert appears through authenticated SSE without reload', async ({
  page,
}) => {
  const state = requireAuthE2EState()
  const uniquePath = `/e2e-sse-${state.runId}`
  await signInWithMfa(page)

  const navigationRequestUrls: string[] = []
  page.on('request', (request) => {
    if (
      request.frame() === page.mainFrame() &&
      request.isNavigationRequest()
    ) {
      navigationRequestUrls.push(request.url())
    }
  })
  const streamPromise = page.waitForResponse((response) => {
    const url = new URL(response.url())
    return url.pathname === '/api/alerts/stream' && response.status() === 200
  })

  const historyUrl = `/traffic-history?include_normal=true&search=${encodeURIComponent(uniquePath)}`
  await page.goto(historyUrl)
  await expect(page).toHaveURL(`${process.env.PLAYWRIGHT_BASE_URL}${historyUrl}`)
  expect(navigationRequestUrls).toEqual([
    `${process.env.PLAYWRIGHT_BASE_URL}${historyUrl}`,
  ])
  const navigationRequestBaseline = navigationRequestUrls.length
  const initialAlerts = await page.evaluate(async (filters) => {
    const response = await fetch(`/api/alerts?${filters}`, { cache: 'no-store' })
    if (!response.ok) throw new Error('Initial Traffic History request failed.')
    return (await response.json()) as AlertsPayload
  }, new URLSearchParams({ include_normal: 'true', search: uniquePath }).toString())
  expect(initialAlerts.items ?? []).not.toContainEqual(
    expect.objectContaining({ request_path: uniquePath })
  )
  await expect(page.getByText(`POST ${uniquePath}`, { exact: true })).toHaveCount(0)

  const stream = await streamPromise
  const streamHeaders = stream.headers()
  expect(streamHeaders['content-type']?.split(';', 1)[0]).toBe(
    'text/event-stream'
  )
  expect(streamHeaders['cache-control']).toContain('private')
  expect(streamHeaders['cache-control']).toContain('no-store')
  expect(streamHeaders['cache-control']).toContain('no-transform')
  expect(streamHeaders['x-accel-buffering']).toBe('no')
  expect(streamHeaders['x-content-type-options']).toBe('nosniff')

  const openCatchup = await page.evaluate(async (filters) => {
    const response = await fetch(`/api/alerts?${filters}`, { cache: 'no-store' })
    if (!response.ok) throw new Error('Traffic History catchup request failed.')
    return (await response.json()) as AlertsPayload
  }, new URLSearchParams({ include_normal: 'true', search: uniquePath }).toString())
  expect(openCatchup.items ?? []).not.toContainEqual(
    expect.objectContaining({ request_path: uniquePath })
  )

  const fastapiUrl = process.env.CYBERTRACE_E2E_FASTAPI_URL
  const wafKey = process.env.CYBERTRACE_E2E_WAF_KEY
  if (!fastapiUrl || !wafKey) {
    throw new Error('Managed SSE E2E backend configuration is unavailable.')
  }
  const ingest = await page.request.post(
    `${fastapiUrl}/api/internal/waf-events`,
    {
      headers: { Authorization: `Bearer ${wafKey}` },
      data: {
        ingest_source: 'modsec_audit_bridge',
        transaction_id: `e2e-sse-${state.runId}`,
        timestamp: new Date().toISOString(),
        source_ip: '203.0.113.77',
        source_provenance: 'DIRECT_REMOTE_ADDR',
        request_method: 'POST',
        request_path: uniquePath,
        query_string: 'id=1%20OR%201%3D1',
        request_headers: { 'user-agent': 'cybertrace-e2e' },
        sanitized_body: "' OR 1=1 --",
        crs_score: 8,
        crs_rule_ids: ['942100'],
        matched_rule_messages: ['SQL Injection Attack Detected'],
        matched_rule_tags: ['attack-sqli'],
      },
    }
  )
  expect(ingest.status()).toBe(200)

  await expect(page.getByText(`POST ${uniquePath}`, { exact: true })).toBeVisible()
  const updatedAlerts = await page.evaluate(async (filters) => {
    const response = await fetch(`/api/alerts?${filters}`, { cache: 'no-store' })
    if (!response.ok) throw new Error('Updated Traffic History request failed.')
    return (await response.json()) as AlertsPayload
  }, new URLSearchParams({ include_normal: 'true', search: uniquePath }).toString())
  expect(updatedAlerts.items ?? []).toContainEqual(
    expect.objectContaining({ request_path: uniquePath })
  )

  await page.getByRole('button', { name: 'Export CSV', exact: true }).click()
  const exportResponsePromise = page.waitForResponse((response) => {
    const url = new URL(response.url())
    return url.pathname === '/api/traffic-history/export'
  })
  await page.getByRole('button', { name: 'Prepare CSV' }).click()
  const exportResponse = await exportResponsePromise
  expect(exportResponse.status()).toBe(200)
  expect(exportResponse.headers()['content-type']).toContain('text/csv')
  expect(exportResponse.headers()['cache-control']).toContain('no-store')

  await expect(page.getByRole('status')).toHaveText('CSV export is ready to download.')
  const downloadPromise = page.waitForEvent('download')
  await page.getByRole('link', { name: /Download traffic-history_/ }).click()
  const download = await downloadPromise
  expect(download.suggestedFilename()).toMatch(
    /^traffic-history_\d{4}-\d{2}-\d{2}_to_\d{4}-\d{2}-\d{2}\.csv$/
  )
  const downloadPath = await download.path()
  expect(downloadPath).toBeTruthy()
  const exportedCsv = await readFile(downloadPath!, 'utf8')
  expect(exportedCsv).toContain(
    'traffic_log_id,timestamp_utc,request_method,classification'
  )
  expect(exportedCsv).toContain(',POST,')
  expect(exportedCsv).not.toContain(uniquePath)
  expect(exportedCsv).not.toContain("' OR 1=1 --")
  expect(exportedCsv).not.toContain('source_ip')
  expect(navigationRequestUrls).toHaveLength(navigationRequestBaseline)
})
