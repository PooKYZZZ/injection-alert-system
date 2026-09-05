import { expect, test, type Page } from '@playwright/test'

import {
  requireAuthE2EState,
  type AuthE2ERole,
} from '@/test-support/auth-e2e/state'
import { totpCodeAtTime } from '@/test-support/auth-e2e/totp'

const ROLES: readonly AuthE2ERole[] = ['owner', 'admin', 'analyst', 'viewer']

async function signInAsRole(page: Page, role: AuthE2ERole) {
  const identity = requireAuthE2EState().roleMatrix[role]
  await page.goto('/login')
  await page.getByLabel('Email or username').fill(identity.email)
  await page.getByLabel('Password').fill(identity.password)
  await page.getByRole('button', { name: 'Sign in' }).click()

  if ('totpSecret' in identity) {
    await expect(page).toHaveURL(/\/mfa\/verify$/)
    const codeInput = page.getByLabel('Authenticator code')
    await codeInput.fill('')
    await codeInput.pressSequentially(totpCodeAtTime(identity.totpSecret).code)
    const continueButton = page.getByRole('button', { name: 'Continue' })
    await expect(continueButton).toBeEnabled()
    await continueButton.click()
  }

  await expect(page).toHaveURL(/\/dashboard$/)
}

test.describe('role authorization matrix', () => {
  // Keep the MFA-backed role accounts in one browser worker. This avoids
  // crossing TOTP time steps while the shared development server recompiles.
  test.describe.configure({ mode: 'serial' })

  for (const role of ROLES) {
    test(`${role} has the expected ML navigation, page, and BFF access`, async ({
      page,
    }) => {
      await signInAsRole(page, role)
      const allowed = role === 'owner'

      const mlHealthLinks = page.getByRole('link', {
        name: 'ML Health',
        exact: true,
      })
      const mlDeploymentLinks = page.getByRole('link', {
        name: 'ML Deployment',
        exact: true,
      })
      await expect(mlHealthLinks).toHaveCount(allowed ? 1 : 0)
      await expect(mlDeploymentLinks).toHaveCount(allowed ? 1 : 0)

      const healthStatus = await page.evaluate(async () => {
        const response = await fetch('/api/ml-health')
        return response.status
      })
      expect(healthStatus).toBe(allowed ? 200 : 403)

      const deploymentStatus = await page.evaluate(async () => {
        const response = await fetch('/api/ml-model/summary')
        return response.status
      })
      // Mock mode deliberately returns 503 after authorization; a non-owner
      // must be rejected before the mock/upstream boundary is reached.
      expect(deploymentStatus).toBe(allowed ? 503 : 403)

      for (const route of ['/ml-health', '/ml-model']) {
        const routeStatus = await page.evaluate(async (pathname) => {
          const response = await fetch(pathname, { cache: 'no-store' })
          return response.status
        }, route)
        expect(routeStatus).toBe(allowed ? 200 : 403)
        await page.goto(route)
        if (allowed) {
          await expect(
            page.getByRole('heading', {
              name: route === '/ml-health' ? 'ML Health' : /ML Deployment/,
            })
          ).toBeVisible()
        } else {
          await expect(
            page.getByText('Your account is not authorized to access this section.')
          ).toBeVisible()
        }
      }
    })
  }
})
