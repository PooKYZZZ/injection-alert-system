import { createHmac } from 'node:crypto'

import { describe, expect, it, vi } from 'vitest'

import {
  buildAuthE2EEnvironment,
  createDisposableNames,
  createServiceRoleToken,
  DISPOSABLE_RESOURCE_LABEL,
  parsePublishedPort,
  playwrightInvocation,
  postgrestTargetUrl,
  withDisposableCleanup,
} from './auth-e2e-environment.mjs'

function decodeJwtPart(value: string): Record<string, unknown> {
  return JSON.parse(Buffer.from(value, 'base64url').toString('utf8'))
}

describe('disposable authentication E2E environment', () => {
  it('uses one explicit label for CI cancellation cleanup', () => {
    expect(DISPOSABLE_RESOURCE_LABEL).toBe('cybertrace.auth-e2e=true')
  })

  it('creates bounded resource names with an unmistakable disposable prefix', () => {
    expect(createDisposableNames('12345678-1234-1234-1234-123456789abc')).toEqual({
      network: 'cybertrace-auth-e2e-123456781234-network',
      postgres: 'cybertrace-auth-e2e-123456781234-postgres',
      postgrest: 'cybertrace-auth-e2e-123456781234-postgrest',
    })
  })

  it('creates a short-lived service-role JWT with a valid HMAC signature', () => {
    const secret = 'a'.repeat(64)
    const token = createServiceRoleToken(secret, 1_000)
    const [encodedHeader, encodedPayload, encodedSignature] = token.split('.')

    expect(decodeJwtPart(encodedHeader)).toEqual({ alg: 'HS256', typ: 'JWT' })
    expect(decodeJwtPart(encodedPayload)).toEqual({
      role: 'service_role',
      iat: 1_000,
      exp: 4_600,
    })
    expect(encodedSignature).toBe(
      createHmac('sha256', secret)
        .update(`${encodedHeader}.${encodedPayload}`)
        .digest('base64url')
    )
  })

  it.each([
    ['127.0.0.1:49152', 49152],
    ['0.0.0.0:32780', 32780],
    ['[::1]:6543', 6543],
  ])('parses Docker published port %s', (output, expected) => {
    expect(parsePublishedPort(output)).toBe(expected)
  })

  it('rejects missing or privileged published ports', () => {
    expect(() => parsePublishedPort('not-a-port')).toThrow(
      'Docker did not publish a safe test port.'
    )
    expect(() => parsePublishedPort('127.0.0.1:443')).toThrow(
      'Docker did not publish a safe test port.'
    )
  })

  it('builds only explicit local test settings with every rollout gate enabled', () => {
    expect(
      buildAuthE2EEnvironment({
        supabaseUrl: 'http://127.0.0.1:54321',
        serviceRoleToken: 'test-jwt',
        authSecret: 'test-auth-secret',
        mfaEncryptionKey: 'test-mfa-key',
        emailOtpKey: 'test-email-otp-key',
        notificationPayloadKey: 'test-notification-payload-key',
      })
    ).toMatchObject({
      SUPABASE_URL: 'http://127.0.0.1:54321',
      SUPABASE_SERVICE_ROLE_KEY: 'test-jwt',
      AUTH_SECRET: 'test-auth-secret',
      AUTH_MFA_ENCRYPTION_KEY: 'test-mfa-key',
      AUTH_EMAIL_OTP_KEY: 'test-email-otp-key',
      NOTIFICATION_PAYLOAD_ENCRYPTION_KEY:
        'test-notification-payload-key',
      AUTH_ACCOUNT_MANAGEMENT_ENABLED: 'true',
      AUTH_MFA_ENROLLMENT_ENABLED: 'true',
      AUTH_EMAIL_RECOVERY_ENABLED: 'true',
      AUTH_PASSWORD_RESET_ENABLED: 'true',
      AUTH_TURNSTILE_ENABLED: 'false',
      USE_MOCK_API: 'true',
      CYBERTRACE_E2E_MANAGED: 'true',
    })
  })

  it('launches Playwright through Node instead of a platform shell shim', () => {
    const invocation = playwrightInvocation('test-node', [
      '--grep',
      'normal login',
    ])

    expect(invocation.command).toBe('test-node')
    expect(invocation.args[0].replaceAll('\\', '/')).toMatch(
      /node_modules\/playwright\/cli\.js$/
    )
    expect(invocation.args.slice(1)).toEqual([
      'test',
      '--config=playwright.auth.config.ts',
      '--grep',
      'normal login',
    ])
  })

  it('maps only the Supabase REST prefix to standalone PostgREST', () => {
    expect(
      postgrestTargetUrl(
        'http://127.0.0.1:49152',
        '/rest/v1/auth_accounts?select=id'
      )?.toString()
    ).toBe('http://127.0.0.1:49152/auth_accounts?select=id')
    expect(
      postgrestTargetUrl('http://127.0.0.1:49152', '/rest/v1/rpc/test')
        ?.toString()
    ).toBe('http://127.0.0.1:49152/rpc/test')
    expect(
      postgrestTargetUrl('http://127.0.0.1:49152', '/auth/v1/token')
    ).toBeNull()
  })

  it('always cleans up disposable resources after success or failure', async () => {
    const cleanup = vi.fn(async () => undefined)

    await expect(
      withDisposableCleanup(
        { id: 'success' },
        async () => 'passed',
        cleanup
      )
    ).resolves.toBe('passed')
    await expect(
      withDisposableCleanup(
        { id: 'failure' },
        async () => {
          throw new Error('test failed')
        },
        cleanup
      )
    ).rejects.toThrow('test failed')
    expect(cleanup).toHaveBeenNthCalledWith(1, { id: 'success' })
    expect(cleanup).toHaveBeenNthCalledWith(2, { id: 'failure' })
  })
})
