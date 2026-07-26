import { createHmac } from 'node:crypto'
import { EventEmitter } from 'node:events'
import path from 'node:path'

import { describe, expect, it, vi } from 'vitest'

import {
  backendDatabaseUrl,
  buildBackendE2EEnvironment,
  buildAuthE2EEnvironment,
  buildMigrationEnvironment,
  createDisposableNames,
  createServiceRoleToken,
  DISPOSABLE_RESOURCE_LABEL,
  parsePublishedPort,
  playwrightInvocation,
  postgrestTargetUrl,
  processFailureMessage,
  pythonExecutable,
  redactChildOutput,
  withManagedSignalCleanup,
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

  it('supports an explicit real FastAPI boundary', () => {
    expect(
      buildAuthE2EEnvironment({
        supabaseUrl: 'http://127.0.0.1:54321',
        serviceRoleToken: 'test-jwt',
        authSecret: 'test-auth-secret',
        mfaEncryptionKey: 'test-mfa-key',
        emailOtpKey: 'test-email-otp-key',
        notificationPayloadKey: 'test-notification-payload-key',
        useMockApi: false,
        fastapiBaseUrl: 'http://127.0.0.1:49152',
        internalApiKey: 'generated-internal-key',
      })
    ).toMatchObject({
      USE_MOCK_API: 'false',
      FASTAPI_BASE_URL: 'http://127.0.0.1:49152',
      INTERNAL_API_KEY: 'generated-internal-key',
    })
  })

  it('supports an isolated loopback frontend origin', () => {
    expect(
      buildAuthE2EEnvironment({
        supabaseUrl: 'http://127.0.0.1:54321',
        serviceRoleToken: 'test-jwt',
        authSecret: 'test-auth-secret',
        mfaEncryptionKey: 'test-mfa-key',
        emailOtpKey: 'test-email-otp-key',
        notificationPayloadKey: 'test-notification-payload-key',
        frontendOrigin: 'http://127.0.0.1:49153',
      })
    ).toMatchObject({
      NEXTAUTH_URL: 'http://127.0.0.1:49153',
      AUTH_APP_ORIGIN: 'http://127.0.0.1:49153',
      PLAYWRIGHT_BASE_URL: 'http://127.0.0.1:49153',
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

  it('accepts a dedicated Playwright config', () => {
    const invocation = playwrightInvocation(
      'test-node',
      ['--grep', 'SSE'],
      'playwright.sse.config.ts'
    )

    expect(invocation.args.slice(1)).toEqual([
      'test',
      '--config=playwright.sse.config.ts',
      '--grep',
      'SSE',
    ])
    expect(invocation.args).not.toContain('--config=playwright.auth.config.ts')
  })

  it('uses setup-python on CI but still requires the local repository venv', () => {
    expect(
      pythonExecutable({
        ci: true,
        fileExists: () => false,
        platform: 'linux',
      })
    ).toBe('python')
    expect(() =>
      pythonExecutable({
        ci: false,
        fileExists: () => false,
        platform: 'linux',
      })
    ).toThrow('Repository Python virtual environment is unavailable.')
  })

  it('supplies every required backend setting to Alembic explicitly', () => {
    const environment = buildMigrationEnvironment({
      databaseUrl: 'postgresql+psycopg://disposable',
      baseEnvironment: {
        NODE_ENV: 'test',
        PATH: 'test-path',
        SUPABASE_SERVICE_ROLE_KEY: 'hosted-supabase-secret',
        RESEND_API_KEY: 'live-resend-secret',
        GROQ_API_KEY: 'live-groq-secret',
      },
    })

    expect(environment).toMatchObject({
      PATH: 'test-path',
      DATABASE_URL: 'postgresql+psycopg://disposable',
      CYBERTRACE_POSTGRES_TEST_URL: 'postgresql+psycopg://disposable',
      MODEL_PATH: expect.stringContaining('ml_model'),
      MODEL_REGISTRY_PATH: expect.stringContaining('ml_model'),
    })
    expect(environment).not.toHaveProperty('NODE_ENV')
    expect(environment).not.toHaveProperty('SUPABASE_SERVICE_ROLE_KEY')
    expect(environment).not.toHaveProperty('RESEND_API_KEY')
    expect(environment).not.toHaveProperty('GROQ_API_KEY')
  })

  it('converts only the disposable loopback psycopg URL for FastAPI', () => {
    expect(
      backendDatabaseUrl(
        'postgresql+psycopg://postgres:fake@127.0.0.1:49154/cybertrace'
      )
    ).toBe('postgresql://postgres:fake@127.0.0.1:49154/cybertrace')
    expect(() =>
      backendDatabaseUrl(
        'postgresql+psycopg://postgres:fake@db.example.test:5432/cybertrace'
      )
    ).toThrow('Disposable backend database URL is invalid.')
    expect(() =>
      backendDatabaseUrl(
        'postgresql+psycopg://postgres:fake@127.0.0.1:49154/production'
      )
    ).toThrow('Disposable backend database URL is invalid.')
  })

  it('allowlists safe FastAPI test settings without forwarding hosted secrets', () => {
    const repositoryDirectory = path.resolve('cybertrace-test-repo')
    const modelDirectory = path.resolve('cybertrace-missing-model')
    const environment = buildBackendE2EEnvironment({
      databaseUrl:
        'postgresql+psycopg://postgres:fake@127.0.0.1:49154/cybertrace',
      repositoryDirectory,
      modelDirectory,
      internalApiKey: 'i'.repeat(64),
      wafApiKey: 'w'.repeat(64),
      baseEnvironment: {
        NODE_ENV: 'test',
        PATH: 'test-path',
        SystemRoot: 'C:\\Windows',
        RESEND_API_KEY: 'live-resend-secret',
        GROQ_API_KEY: 'live-groq-secret',
      },
    })

    expect(environment).toMatchObject({
      PATH: 'test-path',
      SystemRoot: 'C:\\Windows',
      APP_ENV: 'testing',
      NOTIFICATION_WORKER_ENABLED: 'false',
      NOTIFICATION_WORKER_REQUIRED: 'false',
      EMAIL_PROVIDER: 'fake',
      API_SECRET_KEY: 'i'.repeat(64),
      WAF_INGEST_API_KEY: 'w'.repeat(64),
      DATABASE_URL:
        'postgresql://postgres:fake@127.0.0.1:49154/cybertrace',
      MODEL_PATH: modelDirectory,
      MODEL_REGISTRY_PATH: modelDirectory,
      PYTHONPATH: repositoryDirectory,
    })
    expect(environment).not.toHaveProperty('RESEND_API_KEY')
    expect(environment).not.toHaveProperty('GROQ_API_KEY')
  })

  it('redacts credentials from managed child output', () => {
    expect(
      redactChildOutput(
        'postgresql://postgres:db-password@127.0.0.1/db Authorization: Bearer bearer-secret API_SECRET_KEY=internal-secret'
      )
    ).toBe(
      'postgresql://[redacted]@127.0.0.1/db Authorization: Bearer [redacted] API_SECRET_KEY=[redacted]'
    )
  })

  it('preserves bounded redacted diagnostics for failed managed processes', () => {
    expect(
      processFailureMessage('Disposable PostgreSQL container', {
        code: 1,
        stdout: 'container output',
        stderr: 'password=secret API_SECRET_KEY=internal-secret',
      })
    ).toBe(
      'Disposable PostgreSQL container failed with exit code 1.\n' +
        'container output\npassword=secret API_SECRET_KEY=[redacted]'
    )
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

  it('aborts active work on a signal and cleans up only after it unwinds', async () => {
    const processObject = new EventEmitter() as EventEmitter & {
      exitCode?: number
    }
    const events: string[] = []
    const cleanup = vi.fn(async () => {
      events.push('cleanup')
    })
    let releaseExecution: (() => void) | undefined

    const running = withManagedSignalCleanup(
      async (signal: AbortSignal) => {
        events.push('execute')
        await new Promise<void>((resolve) => {
          releaseExecution = resolve
          signal.addEventListener('abort', () => events.push('aborted'), {
            once: true,
          })
        })
        events.push('unwound')
        throw signal.reason
      },
      cleanup,
      { processObject: processObject as unknown as NodeJS.Process }
    )

    processObject.emit('SIGINT')
    expect(events).toEqual(['execute', 'aborted'])
    expect(cleanup).not.toHaveBeenCalled()
    releaseExecution?.()

    await expect(running).rejects.toThrow('SIGINT')
    expect(events).toEqual(['execute', 'aborted', 'unwound', 'cleanup'])
    expect(cleanup).toHaveBeenCalledOnce()
    expect(processObject.exitCode).toBe(130)
    expect(processObject.listenerCount('SIGINT')).toBe(0)
    expect(processObject.listenerCount('SIGTERM')).toBe(0)
  })
})
