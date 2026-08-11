import { expect, test, type APIResponse, type Page } from '@playwright/test'

import {
  readAuthAccountState,
  waitForEmailRecoveryOtp,
} from '@/test-support/auth-e2e/database'
import { SAFE_FAILURE_CONTEXT } from '@/test-support/auth-e2e/failure-artifacts'
import {
  parseTotpSecret,
  totpCodeAtStep,
  totpCodeAtTime,
  waitForTotpStepAfter,
} from '@/test-support/auth-e2e/totp'
import {
  requireAuthE2EState,
  type AuthE2EIdentity,
} from '@/test-support/auth-e2e/state'

type AuthSession = {
  user?: {
    id?: string
    auth_level?: 'password' | 'recovery' | 'mfa'
    auth_method?: 'password' | 'totp' | 'backup_code' | 'email_otp'
    auth_time?: number
    mfa_challenge_purpose?:
      | 'login_mfa'
      | 'mfa_enrollment'
      | 'recent_reauthentication'
      | 'mfa_recovery'
  }
}

async function signIn(page: Page, identity: AuthE2EIdentity): Promise<void> {
  await page.goto('/login')
  await page.getByLabel('Email or username').fill(identity.email)
  await page.getByLabel('Password').fill(identity.password)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

async function readSession(page: Page): Promise<AuthSession> {
  const response = await page.request.get('/api/auth/session')
  expect(response.ok()).toBe(true)
  return (await response.json()) as AuthSession
}

async function expectSession(
  page: Page,
  expected: {
    accountId: string
    level: NonNullable<AuthSession['user']>['auth_level']
    method: NonNullable<AuthSession['user']>['auth_method']
    purpose: NonNullable<AuthSession['user']>['mfa_challenge_purpose']
  }
): Promise<AuthSession> {
  const session = await readSession(page)
  expect(session.user).toMatchObject({
    id: expected.accountId,
    auth_level: expected.level,
    auth_method: expected.method,
    mfa_challenge_purpose: expected.purpose,
  })
  expect(session.user?.auth_time).toEqual(expect.any(Number))
  return session
}

async function expectFinalSessionCookie(page: Page): Promise<void> {
  const cookieNames = (await page.context().cookies()).map(({ name }) => name)
  expect(
    cookieNames.some(
      (name) =>
        name.includes('authjs.session-token') ||
        name.includes('next-auth.session-token')
    )
  ).toBe(true)
  expect(
    cookieNames.some(
      (name) =>
        name.includes('cybertrace-preauth') ||
        name.includes('mfa-completion') ||
        name.includes('cybertrace-recovery')
    )
  ).toBe(false)
}

async function expectRejectedReplay(response: APIResponse): Promise<void> {
  expect(response.ok()).toBe(false)
  expect(response.status()).toBeGreaterThanOrEqual(400)
  expect(response.status()).toBeLessThan(500)
}

test.describe('critical authentication journeys', () => {
  test.describe.configure({ mode: 'parallel' })

  test.afterEach(async ({ page }, testInfo) => {
    if (testInfo.status === testInfo.expectedStatus) return
    await testInfo.attach('error-context', {
      body: Buffer.from(SAFE_FAILURE_CONTEXT, 'utf8'),
      contentType: 'text/markdown',
    })
    try {
      const screenshot = await page.screenshot({
        fullPage: true,
        mask: [page.locator('input'), page.locator('[data-qr-value]')],
      })
      await testInfo.attach('masked-failure', {
        body: screenshot,
        contentType: 'image/png',
      })
    } catch {
      // Preserve the primary assertion when navigation races failure capture.
    }
  })

  test('first-time privileged-user MFA enrollment reaches an assured dashboard session', async ({
    page,
  }) => {
    const identity = requireAuthE2EState().identities.enroll
    await signIn(page, identity)
    await expect(page).toHaveURL(/\/mfa\/enroll$/)

    await page
      .getByRole('button', { name: /start authenticator setup/i })
      .click()
    const provisioningUri = await page
      .locator('[data-qr-value]')
      .getAttribute('data-qr-value')
    expect(provisioningUri).not.toBeNull()
    const secret = parseTotpSecret(provisioningUri!)
    await page
      .getByLabel('Enter the six-digit code')
      .fill(totpCodeAtTime(secret).code)
    const enrollmentResponse = page.waitForResponse(
      (response) =>
        response.url().endsWith('/api/auth/mfa/enroll/verify') &&
        response.request().method() === 'POST',
      { timeout: 60_000 }
    )
    await page
      .getByRole('button', { name: /verify authenticator/i })
      .click()
    const response = await enrollmentResponse
    expect(response.ok()).toBe(true)
    const enrollmentPayload = (await response.json()) as {
      backup_codes?: unknown
      status?: unknown
    }
    expect(enrollmentPayload).toMatchObject({
      status: 'pending_finalization',
      backup_codes: expect.any(Array),
    })
    expect(enrollmentPayload.backup_codes).toHaveLength(8)

    await expect(
      page.getByRole('heading', { name: /save your backup codes/i })
    ).toBeVisible()
    await expect(
      page.getByRole('status', { name: 'Backup codes' }).locator('span')
    ).toHaveCount(8)
    await page
      .getByRole('button', { name: /saved my backup codes/i })
      .click()

    await expect(page).toHaveURL(/\/dashboard$/)
    await expectSession(page, {
      accountId: identity.id,
      level: 'mfa',
      method: 'totp',
      purpose: 'mfa_enrollment',
    })
    await expectFinalSessionCookie(page)
    await expect(readAuthAccountState(identity.id)).resolves.toMatchObject({
      activeFactors: 1,
      usedBackupCodes: 0,
    })
  })

  test('normal login followed by fresh TOTP verification establishes the final session', async ({
    page,
  }) => {
    const identity = requireAuthE2EState().identities.login
    await signIn(page, identity)
    await expect(page).toHaveURL(/\/mfa\/verify$/)

    await page
      .getByLabel('Authenticator code')
      .fill(totpCodeAtTime(identity.totpSecret).code)
    await page.getByRole('button', { name: 'Continue' }).click()

    await expect(page).toHaveURL(/\/dashboard$/)
    await expectSession(page, {
      accountId: identity.id,
      level: 'mfa',
      method: 'totp',
      purpose: 'login_mfa',
    })
    await expectFinalSessionCookie(page)
  })

  test('backup-code recovery is one-time and forces authenticator re-enrollment', async ({
    page,
  }) => {
    const identity = requireAuthE2EState().identities.backup
    await signIn(page, identity)
    await expect(page).toHaveURL(/\/mfa\/verify$/)
    await page.goto('/mfa/recover')

    await page.getByLabel('Backup code').fill(identity.backupCode)
    await page.getByRole('button', { name: /use backup code/i }).click()

    await expect(page).toHaveURL(/\/mfa\/enroll$/)
    await expectSession(page, {
      accountId: identity.id,
      level: 'recovery',
      method: 'backup_code',
      purpose: 'mfa_recovery',
    })
    await expectFinalSessionCookie(page)
    await expect(readAuthAccountState(identity.id)).resolves.toMatchObject({
      activeFactors: 0,
      usedBackupCodes: 1,
    })

    await expectRejectedReplay(
      await page.request.post('/api/auth/mfa/recovery/backup', {
        headers: { origin: 'http://127.0.0.1:3000' },
        data: { code: identity.backupCode },
      })
    )
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/mfa\/enroll$/)
  })

  test('email recovery consumes the generated OTP once and forces re-enrollment', async ({
    page,
  }) => {
    const identity = requireAuthE2EState().identities.email
    await signIn(page, identity)
    await expect(page).toHaveURL(/\/mfa\/verify$/)
    await page.goto('/mfa/recover')

    await page
      .getByRole('button', { name: /send a recovery code/i })
      .click()
    await expect(
      page.getByText(/a code has been sent to your verified email/i)
    ).toBeVisible()
    const otp = await waitForEmailRecoveryOtp(identity.email)
    await page.getByLabel('Six-digit recovery code').fill(otp)
    await page
      .getByRole('button', { name: /verify recovery code/i })
      .click()

    await expect(page).toHaveURL(/\/mfa\/enroll$/)
    await expectSession(page, {
      accountId: identity.id,
      level: 'recovery',
      method: 'email_otp',
      purpose: 'mfa_recovery',
    })
    await expectFinalSessionCookie(page)
    await expect(readAuthAccountState(identity.id)).resolves.toMatchObject({
      activeFactors: 0,
    })

    await expectRejectedReplay(
      await page.request.post('/api/auth/mfa/recovery/email/verify', {
        headers: { origin: 'http://127.0.0.1:3000' },
        data: { code: otp },
      })
    )
    await page.goto('/dashboard')
    await expect(page).toHaveURL(/\/mfa\/enroll$/)
  })

  test('step-up rejects TOTP time-step reuse and returns to the requested path with fresh claims', async ({
    page,
  }) => {
    const identity = requireAuthE2EState().identities.stepup
    await signIn(page, identity)
    await expect(page).toHaveURL(/\/mfa\/verify$/)

    const loginTotp = totpCodeAtTime(identity.totpSecret)
    await page.getByLabel('Authenticator code').fill(loginTotp.code)
    await page.getByRole('button', { name: 'Continue' }).click()
    await expect(page).toHaveURL(/\/dashboard$/)
    const loginSession = await expectSession(page, {
      accountId: identity.id,
      level: 'mfa',
      method: 'totp',
      purpose: 'login_mfa',
    })

    await page.goto(
      '/mfa/step-up?returnTo=%2Fdashboard%3Fstep-up%3D1'
    )
    await page.getByRole('button', { name: /start verification/i }).click()
    await page.getByLabel('Authenticator code').fill(loginTotp.code)
    await page
      .getByRole('button', { name: /verify and continue/i })
      .click()
    await expect(
      page.getByText('That authenticator code is invalid or already used.', {
        exact: true,
      })
    ).toBeVisible()

    const freshStep = await waitForTotpStepAfter(loginTotp.step)
    await page
      .getByLabel('Authenticator code')
      .fill(totpCodeAtStep(identity.totpSecret, freshStep))
    await page
      .getByRole('button', { name: /verify and continue/i })
      .click()

    await expect(page).toHaveURL(/\/dashboard\?step-up=1$/)
    const stepUpSession = await expectSession(page, {
      accountId: identity.id,
      level: 'mfa',
      method: 'totp',
      purpose: 'recent_reauthentication',
    })
    expect(stepUpSession.user?.auth_time).toBeGreaterThan(
      loginSession.user?.auth_time ?? 0
    )
    await expectFinalSessionCookie(page)
  })
})
