import { expect, test, type Page } from '@playwright/test'

type JourneyCredentials = {
  email?: string
  password?: string
  totp?: string
  backup?: string
  emailOtp?: string
}

function credentials(prefix: string): JourneyCredentials {
  return {
    email: process.env[`CYBERTRACE_E2E_${prefix}_EMAIL`],
    password: process.env[`CYBERTRACE_E2E_${prefix}_PASSWORD`],
    totp: process.env[`CYBERTRACE_E2E_${prefix}_TOTP`],
    backup: process.env[`CYBERTRACE_E2E_${prefix}_BACKUP_CODE`],
    emailOtp: process.env[`CYBERTRACE_E2E_${prefix}_EMAIL_OTP`],
  }
}

function requireJourney(prefix: string, required: Array<keyof JourneyCredentials>): JourneyCredentials {
  const value = credentials(prefix)
  if (required.some((key) => !value[key])) {
    throw new Error(`missing disposable E2E seed variable for ${prefix}`)
  }
  return value
}

async function signIn(page: Page, value: JourneyCredentials) {
  await page.goto('/login')
  await page.getByLabel('Email or username').fill(value.email!)
  await page.getByLabel('Password').fill(value.password!)
  await page.getByRole('button', { name: 'Sign in' }).click()
}

async function expectSessionCookie(page: Page) {
  const cookies = await page.context().cookies()
  expect(cookies.some((cookie: { name: string }) => cookie.name.includes('authjs.session-token') || cookie.name.includes('next-auth.session-token'))).toBe(true)
}

const journeyDescribe =
  process.env.CYBERTRACE_E2E_ENABLED === 'true' &&
  process.env.CYBERTRACE_E2E_SEED_READY === 'true'
    ? test.describe
    : test.describe.skip

journeyDescribe('critical authentication journeys', () => {
test('first-time privileged-user MFA enrollment reaches an assured dashboard session', async ({ page }) => {
  const value = requireJourney('ENROLL', ['email', 'password', 'totp'])
  await signIn(page, value)
  await expect(page).toHaveURL(/\/mfa\/enroll$/)
  await page.getByRole('button', { name: /start authenticator setup/i }).click()
  await expect(page.locator('[data-qr-value]')).toBeVisible()
  await page.getByLabel('Enter the six-digit code').fill(value.totp!)
  await page.getByRole('button', { name: /verify authenticator/i }).click()
  await expect(page.getByRole('heading', { name: /save your backup codes/i })).toBeVisible()
  await page.getByRole('button', { name: /saved my backup codes/i }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expectSessionCookie(page)
  const cookies = await page.context().cookies()
  expect(cookies.some((cookie: { name: string }) => cookie.name.includes('cybertrace-preauth') || cookie.name.includes('mfa-completion'))).toBe(false)
})

test('normal login followed by MFA verification establishes the final session', async ({ page }) => {
  const value = requireJourney('LOGIN', ['email', 'password', 'totp'])
  await signIn(page, value)
  await expect(page).toHaveURL(/\/mfa\/verify$/)
  await page.getByLabel('Enter the six-digit code').fill(value.totp!)
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await expectSessionCookie(page)
})

test('backup-code recovery establishes a restricted session and forces re-enrollment', async ({ page }) => {
  const value = requireJourney('BACKUP', ['email', 'password', 'backup'])
  await signIn(page, value)
  await page.goto('/mfa/recover')
  await page.getByLabel('Backup code').fill(value.backup!)
  await page.getByRole('button', { name: /use backup code/i }).click()
  await expect(page).toHaveURL(/\/mfa\/enroll$/)
  await expectSessionCookie(page)
})

test('email recovery establishes a restricted session and forces re-enrollment', async ({ page }) => {
  const value = requireJourney('EMAIL', ['email', 'password', 'emailOtp'])
  await signIn(page, value)
  await page.goto('/mfa/recover')
  await page.getByRole('button', { name: /send a recovery code/i }).click()
  await page.getByLabel('Six-digit recovery code').fill(value.emailOtp!)
  await page.getByRole('button', { name: /verify recovery code/i }).click()
  await expect(page).toHaveURL(/\/mfa\/enroll$/)
  await expectSessionCookie(page)
})

test('recent-TOTP step-up returns to the requested sensitive-action path', async ({ page }) => {
  const value = requireJourney('STEPUP', ['email', 'password', 'totp'])
  await signIn(page, value)
  await expect(page).toHaveURL(/\/mfa\/verify$/)
  await page.getByLabel('Enter the six-digit code').fill(value.totp!)
  await page.getByRole('button', { name: 'Continue' }).click()
  await expect(page).toHaveURL(/\/dashboard$/)
  await page.goto('/mfa/step-up?returnTo=%2Fdashboard%3Fstep-up%3D1')
  await page.getByRole('button', { name: /start verification/i }).click()
  await page.getByLabel('Authenticator code').fill(value.totp!)
  await page.getByRole('button', { name: /verify and continue/i }).click()
  await expect(page).toHaveURL(/\/dashboard\?step-up=1$/)
  await expectSessionCookie(page)
})
})
