import {
  expect,
  test,
  type Page,
  type Response,
} from '@playwright/test'

import { totpCodeAtTime } from '@/test-support/auth-e2e/totp'
import { requireAuthE2EState } from '@/test-support/auth-e2e/state'

type AlertsPayload = {
  items?: Array<{ request_path?: string | null }>
}

function isAlertsResponse(response: Response): boolean {
  const url = new URL(response.url())
  return url.pathname === '/api/alerts' && response.status() === 200
}

async function signInWithMfa(page: Page): Promise<void> {
  const identity = requireAuthE2EState().identities.login
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
  let streamResponseObserved = false
  const alertResponsesAfterStream: Response[] = []
  page.on('request', (request) => {
    if (
      request.frame() === page.mainFrame() &&
      request.isNavigationRequest()
    ) {
      navigationRequestUrls.push(request.url())
    }
  })
  page.on('response', (response) => {
    const url = new URL(response.url())
    if (url.pathname === '/api/alerts/stream' && response.status() === 200) {
      streamResponseObserved = true
    } else if (streamResponseObserved && isAlertsResponse(response)) {
      alertResponsesAfterStream.push(response)
    }
  })
  const initialAlertsPromise = page.waitForResponse(isAlertsResponse)
  const streamPromise = page.waitForResponse((response) => {
    const url = new URL(response.url())
    return url.pathname === '/api/alerts/stream' && response.status() === 200
  })

  await page.goto('/alerts')
  await expect(page).toHaveURL(/\/alerts$/)
  expect(navigationRequestUrls).toEqual([
    `${process.env.PLAYWRIGHT_BASE_URL}/alerts`,
  ])
  const navigationRequestBaseline = navigationRequestUrls.length

  const initialAlertsResponse = await initialAlertsPromise
  const initialAlerts = (await initialAlertsResponse.json()) as AlertsPayload
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

  const alreadyObservedCatchup = alertResponsesAfterStream.find(
    (response) => response.request() !== initialAlertsResponse.request()
  )
  const openCatchupResponse =
    alreadyObservedCatchup ??
    (await page.waitForResponse(
      (response) =>
        streamResponseObserved &&
        isAlertsResponse(response) &&
        response.request() !== initialAlertsResponse.request()
    ))
  const openCatchup = (await openCatchupResponse.json()) as AlertsPayload
  expect(openCatchup.items ?? []).not.toContainEqual(
    expect.objectContaining({ request_path: uniquePath })
  )

  const updatedAlertsPromise = page.waitForResponse(async (response) => {
    if (!isAlertsResponse(response)) return false
    try {
      const payload = (await response.json()) as AlertsPayload
      return (payload.items ?? []).some(
        (item) => item.request_path === uniquePath
      )
    } catch {
      return false
    }
  })

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

  await updatedAlertsPromise
  await expect(page.getByText(`POST ${uniquePath}`, { exact: true })).toBeVisible()
  expect(navigationRequestUrls).toHaveLength(navigationRequestBaseline)
})
