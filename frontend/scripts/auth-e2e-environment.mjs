import { spawn } from 'node:child_process'
import { createHmac, randomBytes, randomUUID } from 'node:crypto'
import { existsSync } from 'node:fs'
import { mkdtemp, rm } from 'node:fs/promises'
import { createServer, request as createHttpRequest } from 'node:http'
import os from 'node:os'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const DISPOSABLE_PREFIX = 'cybertrace-auth-e2e-'
const POSTGRES_IMAGE = 'postgres:17.6'
const POSTGREST_IMAGE = 'postgrest/postgrest:v14.14'
const DATABASE_NAME = 'cybertrace'
const POSTGRES_USER = 'postgres'
const FRONTEND_ORIGIN = 'http://127.0.0.1:3000'
export const DISPOSABLE_RESOURCE_LABEL = 'cybertrace.auth-e2e=true'

const scriptDirectory = path.dirname(fileURLToPath(import.meta.url))
const frontendDirectory = path.resolve(scriptDirectory, '..')
const repositoryDirectory = path.resolve(frontendDirectory, '..')

function randomHex(bytes) {
  return randomBytes(bytes).toString('hex')
}

function encodeJwtPart(value) {
  return Buffer.from(JSON.stringify(value), 'utf8').toString('base64url')
}

export function createDisposableNames(runId = randomUUID()) {
  const suffix = runId.toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 12)
  if (suffix.length !== 12) {
    throw new Error('Disposable E2E run id is invalid.')
  }
  const root = `${DISPOSABLE_PREFIX}${suffix}`
  return {
    network: `${root}-network`,
    postgres: `${root}-postgres`,
    postgrest: `${root}-postgrest`,
  }
}

function assertDisposableNames(names) {
  for (const value of Object.values(names)) {
    if (
      typeof value !== 'string' ||
      !value.startsWith(DISPOSABLE_PREFIX) ||
      !/^[a-z0-9-]+$/.test(value)
    ) {
      throw new Error('Refusing to clean up a non-disposable Docker resource.')
    }
  }
}

export function createServiceRoleToken(
  secret,
  issuedAt = Math.floor(Date.now() / 1_000)
) {
  if (typeof secret !== 'string' || secret.length < 32) {
    throw new Error('PostgREST JWT secret is invalid.')
  }
  const header = encodeJwtPart({ alg: 'HS256', typ: 'JWT' })
  const payload = encodeJwtPart({
    role: 'service_role',
    iat: issuedAt,
    exp: issuedAt + 60 * 60,
  })
  const signingInput = `${header}.${payload}`
  const signature = createHmac('sha256', secret)
    .update(signingInput)
    .digest('base64url')
  return `${signingInput}.${signature}`
}

export function parsePublishedPort(output) {
  const match = String(output).trim().match(/:(\d+)$/)
  const port = match ? Number(match[1]) : Number.NaN
  if (!Number.isInteger(port) || port < 1_024 || port > 65_535) {
    throw new Error('Docker did not publish a safe test port.')
  }
  return port
}

export function buildAuthE2EEnvironment({
  supabaseUrl,
  serviceRoleToken,
  authSecret,
  mfaEncryptionKey,
  emailOtpKey,
  notificationPayloadKey,
  useMockApi = true,
  fastapiBaseUrl = '',
  internalApiKey = '',
  frontendOrigin = FRONTEND_ORIGIN,
}) {
  if (!useMockApi && (!fastapiBaseUrl || !internalApiKey)) {
    throw new Error('Real API E2E configuration is incomplete.')
  }
  const environment = {
    SUPABASE_URL: supabaseUrl,
    SUPABASE_SERVICE_ROLE_KEY: serviceRoleToken,
    AUTH_SECRET: authSecret,
    NEXTAUTH_URL: frontendOrigin,
    AUTH_TRUST_HOST: 'true',
    AUTH_APP_ORIGIN: frontendOrigin,
    AUTH_MFA_ENCRYPTION_KEY: mfaEncryptionKey,
    AUTH_EMAIL_OTP_KEY: emailOtpKey,
    NOTIFICATION_PAYLOAD_ENCRYPTION_KEY: notificationPayloadKey,
    AUTH_ACCOUNT_MANAGEMENT_ENABLED: 'true',
    AUTH_MFA_ENROLLMENT_ENABLED: 'true',
    AUTH_EMAIL_RECOVERY_ENABLED: 'true',
    AUTH_PASSWORD_RESET_ENABLED: 'true',
    AUTH_TURNSTILE_ENABLED: 'false',
    USE_MOCK_API: useMockApi ? 'true' : 'false',
    PLAYWRIGHT_BASE_URL: frontendOrigin,
    CYBERTRACE_E2E_MANAGED: 'true',
  }
  if (!useMockApi) {
    environment.FASTAPI_BASE_URL = fastapiBaseUrl
    environment.INTERNAL_API_KEY = internalApiKey
  }
  return environment
}

export function buildMigrationEnvironment({
  databaseUrl,
  baseEnvironment = process.env,
}) {
  const modelPath = path.join(
    repositoryDirectory,
    'ml_model',
    'model_registry'
  )
  return {
    ...allowlistedChildEnvironment(baseEnvironment),
    DATABASE_URL: databaseUrl,
    CYBERTRACE_POSTGRES_TEST_URL: databaseUrl,
    MODEL_PATH: modelPath,
    MODEL_REGISTRY_PATH: modelPath,
  }
}

const CHILD_ENVIRONMENT_KEYS = [
  'PATH',
  'Path',
  'SystemRoot',
  'ComSpec',
  'PATHEXT',
  'TEMP',
  'TMP',
  'CI',
  'FORCE_COLOR',
  'NO_COLOR',
]

function allowlistedChildEnvironment(baseEnvironment = process.env) {
  const environment = {}
  for (const key of CHILD_ENVIRONMENT_KEYS) {
    const value = baseEnvironment[key]
    if (typeof value === 'string' && value.length > 0) {
      environment[key] = value
    }
  }
  return environment
}

export function backendDatabaseUrl(databaseUrl) {
  let parsed
  try {
    parsed = new URL(databaseUrl)
  } catch {
    throw new Error('Disposable backend database URL is invalid.')
  }
  if (
    parsed.protocol !== 'postgresql+psycopg:' ||
    parsed.hostname !== '127.0.0.1' ||
    parsed.pathname !== '/cybertrace' ||
    !Number.isInteger(Number(parsed.port)) ||
    Number(parsed.port) < 1_024
  ) {
    throw new Error('Disposable backend database URL is invalid.')
  }
  return databaseUrl.replace(/^postgresql\+psycopg:/, 'postgresql:')
}

export function buildBackendE2EEnvironment({
  databaseUrl,
  repositoryDirectory: repositoryPath,
  modelDirectory,
  internalApiKey,
  wafApiKey,
  baseEnvironment = process.env,
}) {
  if (!path.isAbsolute(repositoryPath) || !path.isAbsolute(modelDirectory)) {
    throw new Error('Disposable backend paths must be absolute.')
  }
  if (
    typeof internalApiKey !== 'string' ||
    typeof wafApiKey !== 'string' ||
    internalApiKey.length < 32 ||
    wafApiKey.length < 32 ||
    internalApiKey === wafApiKey
  ) {
    throw new Error('Disposable backend keys are invalid.')
  }
  return {
    ...allowlistedChildEnvironment(baseEnvironment),
    APP_ENV: 'testing',
    DATABASE_URL: backendDatabaseUrl(databaseUrl),
    MODEL_PATH: modelDirectory,
    MODEL_REGISTRY_PATH: modelDirectory,
    API_SECRET_KEY: internalApiKey,
    WAF_INGEST_API_KEY: wafApiKey,
    WAF_SOURCE_VERIFICATION_MODE: 'unverified',
    NOTIFICATION_WORKER_ENABLED: 'false',
    NOTIFICATION_WORKER_REQUIRED: 'false',
    EMAIL_PROVIDER: 'fake',
    THREAT_EMAIL_ENABLED: 'false',
    PYTHONPATH: repositoryPath,
    PYTHONUNBUFFERED: '1',
  }
}

export function redactChildOutput(output) {
  return String(output)
    .replace(/:\/\/[^:@/\s]+:[^@/\s]+@/g, '://[redacted]@')
    .replace(/(Authorization:\s*Bearer\s+)[^\s]+/gi, '$1[redacted]')
    .replace(/((?:API_SECRET_KEY|WAF_INGEST_API_KEY)\s*=\s*)[^\s]+/gi, '$1[redacted]')
}

export function playwrightInvocation(
  nodeExecutable = process.execPath,
  playwrightArgs = [],
  configFile = 'playwright.auth.config.ts'
) {
  return {
    command: nodeExecutable,
    args: [
      path.join(frontendDirectory, 'node_modules', 'playwright', 'cli.js'),
      'test',
      `--config=${configFile}`,
      ...playwrightArgs,
    ],
  }
}

export function postgrestTargetUrl(postgrestUrl, requestUrl) {
  if (
    typeof requestUrl !== 'string' ||
    (requestUrl !== '/rest/v1' && !requestUrl.startsWith('/rest/v1/'))
  ) {
    return null
  }
  const incoming = new URL(requestUrl, 'http://localhost')
  const target = new URL(postgrestUrl)
  target.pathname = incoming.pathname.slice('/rest/v1'.length) || '/'
  target.search = incoming.search
  return target
}

async function startSupabaseRestProxy(postgrestUrl) {
  const server = createServer((incoming, outgoing) => {
    const target = postgrestTargetUrl(postgrestUrl, incoming.url)
    if (!target) {
      outgoing.writeHead(404, { 'content-type': 'text/plain' })
      outgoing.end('Not found.')
      return
    }

    const headers = { ...incoming.headers, host: target.host }
    delete headers.connection
    const proxyRequest = createHttpRequest(
      target,
      { method: incoming.method, headers },
      (proxyResponse) => {
        outgoing.writeHead(proxyResponse.statusCode ?? 502, proxyResponse.headers)
        proxyResponse.pipe(outgoing)
      }
    )
    proxyRequest.on('error', () => {
      if (!outgoing.headersSent) outgoing.writeHead(502)
      outgoing.end()
    })
    incoming.pipe(proxyRequest)
  })

  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  if (!address || typeof address === 'string') {
    server.close()
    throw new Error('Supabase REST compatibility proxy did not start.')
  }
  let closed = false
  return {
    url: `http://127.0.0.1:${address.port}`,
    close: () => {
      if (closed) return Promise.resolve()
      closed = true
      return new Promise((resolve, reject) => {
        server.close((error) => (error ? reject(error) : resolve()))
      })
    },
  }
}

async function allocateLoopbackPort() {
  const server = createServer()
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const address = server.address()
  if (!address || typeof address === 'string') {
    server.close()
    throw new Error('Disposable loopback port allocation failed.')
  }
  const port = address.port
  await new Promise((resolve, reject) => {
    server.close((error) => (error ? reject(error) : resolve()))
  })
  return port
}

function appendBoundedTail(current, chunk, limit = 32 * 1_024) {
  return `${current}${String(chunk)}`.slice(-limit)
}

async function startManagedFastApi(databaseUrl, signal) {
  const port = await allocateLoopbackPort()
  const temporaryDirectory = await mkdtemp(
    path.join(os.tmpdir(), 'cybertrace-sse-e2e-')
  )
  let child = null
  let stdoutTail = ''
  let stderrTail = ''
  let spawnError = null
  let stopped = false
  const close = async () => {
    if (stopped) return
    stopped = true
    signal?.removeEventListener('abort', abortListener)
    if (child && child.exitCode === null && child.signalCode === null) {
      child.kill()
      await Promise.race([
        new Promise((resolve) => child.once('close', resolve)),
        new Promise((resolve) => setTimeout(resolve, 5_000)),
      ])
    }
    if (
      process.platform === 'win32' &&
      child &&
      child.exitCode === null &&
      child.signalCode === null &&
      Number.isInteger(child.pid)
    ) {
      await runProcess(
        'taskkill',
        ['/PID', String(child.pid), '/T', '/F'],
        { capture: true, allowFailure: true, label: 'FastAPI tree cleanup' }
      )
    }
    await rm(temporaryDirectory, { recursive: true, force: true })
  }
  const abortListener = () => {
    void close()
  }

  const url = `http://127.0.0.1:${port}`
  try {
    signal?.throwIfAborted()
    const internalApiKey = randomHex(32)
    const wafApiKey = randomHex(32)
    const environment = buildBackendE2EEnvironment({
      databaseUrl,
      repositoryDirectory,
      modelDirectory: path.join(temporaryDirectory, 'missing-model'),
      internalApiKey,
      wafApiKey,
    })
    child = spawn(
      pythonExecutable(),
      [
        '-m',
        'uvicorn',
        'web_app.presentation.app:create_app',
        '--host',
        '127.0.0.1',
        '--port',
        String(port),
      ],
      {
        cwd: temporaryDirectory,
        env: environment,
        windowsHide: true,
        stdio: ['ignore', 'pipe', 'pipe'],
      }
    )
    child.stdout.setEncoding('utf8')
    child.stderr.setEncoding('utf8')
    child.stdout.on('data', (chunk) => {
      stdoutTail = appendBoundedTail(stdoutTail, chunk)
    })
    child.stderr.on('data', (chunk) => {
      stderrTail = appendBoundedTail(stderrTail, chunk)
    })
    child.once('error', (error) => {
      spawnError = error
    })
    signal?.addEventListener('abort', abortListener, { once: true })
    await waitFor('Disposable FastAPI', async () => {
      if (spawnError || child.exitCode !== null || child.signalCode !== null) {
        const output = redactChildOutput(`${stdoutTail}\n${stderrTail}`).trim()
        throw new Error(
          `Disposable FastAPI exited before readiness${output ? `:\n${output}` : '.'}`
        )
      }
      try {
        const response = await fetch(`${url}/api/health`)
        return response.ok
      } catch {
        return false
      }
    }, 60_000, signal)
    return { url, internalApiKey, wafApiKey, close }
  } catch (error) {
    await close()
    throw error
  }
}

export async function withDisposableCleanup(resources, execute, cleanup) {
  try {
    return await execute(resources)
  } finally {
    await cleanup(resources)
  }
}

function runProcess(
  command,
  args,
  {
    cwd = repositoryDirectory,
    env = process.env,
    input,
    capture = false,
    allowFailure = false,
    label = command,
    signal,
  } = {}
) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason)
      return
    }
    let child
    try {
      child = spawn(command, args, {
        cwd,
        env,
        windowsHide: true,
        stdio: [
          input === undefined ? 'ignore' : 'pipe',
          capture ? 'pipe' : 'inherit',
          capture ? 'pipe' : 'inherit',
        ],
      })
    } catch {
      reject(new Error(`${label} could not start.`))
      return
    }
    let stdout = ''
    let stderr = ''
    let settled = false
    const settle = (callback, value) => {
      if (settled) return
      settled = true
      signal?.removeEventListener('abort', abortListener)
      callback(value)
    }
    const abortListener = () => {
      if (child.exitCode !== null || child.signalCode !== null) return
      if (process.platform === 'win32' && Number.isInteger(child.pid)) {
        try {
          spawn('taskkill', ['/PID', String(child.pid), '/T', '/F'], {
            windowsHide: true,
            stdio: 'ignore',
          })
        } catch {
          child.kill()
        }
      } else {
        child.kill()
      }
    }
    signal?.addEventListener('abort', abortListener, { once: true })
    if (capture) {
      child.stdout.setEncoding('utf8')
      child.stderr.setEncoding('utf8')
      child.stdout.on('data', (chunk) => {
        stdout += chunk
      })
      child.stderr.on('data', (chunk) => {
        stderr += chunk
      })
    }
    if (input !== undefined) {
      child.stdin.end(input)
    }
    child.on('error', () => {
      settle(reject, new Error(`${label} could not start.`))
    })
    child.on('close', (code) => {
      if (signal?.aborted) {
        settle(reject, signal.reason)
        return
      }
      const result = { code: code ?? 1, stdout, stderr }
      if (result.code === 0 || allowFailure) {
        settle(resolve, result)
      } else {
        settle(reject, new Error(`${label} failed.`))
      }
    })
  })
}

async function waitFor(description, probe, timeoutMs = 60_000, signal) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    signal?.throwIfAborted()
    if (await probe()) return
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`${description} did not become ready.`)
}

async function dockerPublishedPort(container, containerPort, signal) {
  const result = await runProcess(
    'docker',
    ['port', container, `${containerPort}/tcp`],
    { capture: true, label: 'Docker port lookup', signal }
  )
  return parsePublishedPort(result.stdout)
}

async function runPsql(container, sql, signal) {
  await runProcess(
    'docker',
    [
      'exec',
      '-i',
      container,
      'psql',
      '-U',
      POSTGRES_USER,
      '-d',
      DATABASE_NAME,
      '-v',
      'ON_ERROR_STOP=1',
    ],
    { input: sql, label: 'Disposable PostgreSQL setup', signal }
  )
}

async function removeDisposableResources(names) {
  assertDisposableNames(names)
  await runProcess(
    'docker',
    ['rm', '-f', names.postgrest, names.postgres],
    { capture: true, allowFailure: true, label: 'Docker container cleanup' }
  )
  await runProcess('docker', ['network', 'rm', names.network], {
    capture: true,
    allowFailure: true,
    label: 'Docker network cleanup',
  })
  console.log('AUTH_E2E: disposable environment removed')
}

export function pythonExecutable({
  ci = process.env.CI === 'true',
  fileExists = existsSync,
  platform = process.platform,
} = {}) {
  const candidate =
    platform === 'win32'
      ? path.join(repositoryDirectory, '.venv', 'Scripts', 'python.exe')
      : path.join(repositoryDirectory, '.venv', 'bin', 'python')
  if (fileExists(candidate)) return candidate
  if (ci) return platform === 'win32' ? 'python.exe' : 'python'
  throw new Error('Repository Python virtual environment is unavailable.')
}

async function provisionAndRun(
  names,
  playwrightArgs,
  options = {},
  registerCleanup = () => () => undefined,
  signal
) {
  signal?.throwIfAborted()
  const postgresPassword = randomHex(24)
  const authenticatorPassword = randomHex(24)
  const jwtSecret = randomHex(32)
  const serviceRoleToken = createServiceRoleToken(jwtSecret)

  console.log('AUTH_E2E: creating disposable PostgreSQL and PostgREST')
  await runProcess('docker', ['version'], {
    capture: true,
    label: 'Docker availability check',
    signal,
  })
  await runProcess('docker', [
    'network',
    'create',
    '--label',
    DISPOSABLE_RESOURCE_LABEL,
    names.network,
  ], {
    capture: true,
    label: 'Docker network creation',
    signal,
  })
  await runProcess(
    'docker',
    [
      'run',
      '--detach',
      '--name',
      names.postgres,
      '--network',
      names.network,
      '--network-alias',
      'postgres',
      '--label',
      DISPOSABLE_RESOURCE_LABEL,
      // This database is disposable. A tmpfs avoids Docker Desktop disk stalls
      // and ensures no authentication fixture data survives container removal.
      '--tmpfs',
      '/var/lib/postgresql/data:rw',
      '--publish',
      '127.0.0.1::5432',
      '--env',
      'POSTGRES_DB',
      '--env',
      'POSTGRES_USER',
      '--env',
      'POSTGRES_PASSWORD',
      POSTGRES_IMAGE,
    ],
    {
      capture: true,
      env: {
        ...process.env,
        POSTGRES_DB: DATABASE_NAME,
        POSTGRES_USER,
        POSTGRES_PASSWORD: postgresPassword,
      },
      label: 'Disposable PostgreSQL container',
      signal,
    }
  )
  await waitFor('Disposable PostgreSQL', async () => {
    const result = await runProcess(
      'docker',
      [
        'exec',
        names.postgres,
        'psql',
        '-U',
        POSTGRES_USER,
        '-d',
        DATABASE_NAME,
        '-tAc',
        'SELECT 1',
      ],
      { capture: true, allowFailure: true, signal }
    )
    return result.code === 0 && result.stdout.trim() === '1'
  }, 60_000, signal)

  await runPsql(
    names.postgres,
    `
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
CREATE ROLE authenticator NOINHERIT LOGIN PASSWORD '${authenticatorPassword}';
GRANT anon, authenticated, service_role TO authenticator;
`,
    signal
  )

  const postgresPort = await dockerPublishedPort(names.postgres, 5432, signal)
  const databaseUrl = `postgresql+psycopg://${POSTGRES_USER}:${postgresPassword}@127.0.0.1:${postgresPort}/${DATABASE_NAME}`
  console.log('AUTH_E2E: applying the real Alembic migration chain')
  await runProcess(pythonExecutable(), ['-m', 'alembic', 'upgrade', 'head'], {
    env: buildMigrationEnvironment({ databaseUrl }),
    label: 'Alembic upgrade',
    signal,
  })
  await runPsql(
    names.postgres,
    `
GRANT USAGE ON SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;
`,
    signal
  )

  const postgrestDbUri = `postgres://authenticator:${authenticatorPassword}@postgres:5432/${DATABASE_NAME}`
  await runProcess(
    'docker',
    [
      'run',
      '--detach',
      '--name',
      names.postgrest,
      '--network',
      names.network,
      '--label',
      DISPOSABLE_RESOURCE_LABEL,
      '--publish',
      '127.0.0.1::3000',
      '--env',
      'PGRST_DB_URI',
      '--env',
      'PGRST_DB_SCHEMAS=public',
      '--env',
      'PGRST_DB_ANON_ROLE=anon',
      '--env',
      'PGRST_JWT_SECRET',
      POSTGREST_IMAGE,
    ],
    {
      capture: true,
      env: {
        ...process.env,
        PGRST_DB_URI: postgrestDbUri,
        PGRST_JWT_SECRET: jwtSecret,
      },
      label: 'Disposable PostgREST container',
      signal,
    }
  )

  const postgrestPort = await dockerPublishedPort(names.postgrest, 3000, signal)
  const supabaseUrl = `http://127.0.0.1:${postgrestPort}`
  await waitFor('Disposable PostgREST', async () => {
    try {
      const response = await fetch(
        `${supabaseUrl}/auth_accounts?select=id&limit=0`,
        {
          headers: {
            apikey: serviceRoleToken,
            Authorization: `Bearer ${serviceRoleToken}`,
          },
        }
      )
      return response.ok
    } catch {
      return false
    }
  }, 60_000, signal)

  signal?.throwIfAborted()
  const restProxy = await startSupabaseRestProxy(supabaseUrl)
  const unregisterRestProxy = registerCleanup(() => restProxy.close())
  let backend = null
  let unregisterBackend = () => undefined
  try {
    if (options.realApi) {
      backend = await startManagedFastApi(databaseUrl, signal)
      unregisterBackend = registerCleanup(() => backend.close())
    }
    const frontendOrigin = options.realApi
      ? `http://127.0.0.1:${await allocateLoopbackPort()}`
      : FRONTEND_ORIGIN
    const authEnvironment = buildAuthE2EEnvironment({
      supabaseUrl: restProxy.url,
      serviceRoleToken,
      authSecret: randomHex(32),
      mfaEncryptionKey: randomBytes(32).toString('base64'),
      emailOtpKey: randomHex(32),
      notificationPayloadKey: randomBytes(32).toString('base64'),
      frontendOrigin,
      useMockApi: !backend,
      fastapiBaseUrl: backend?.url,
      internalApiKey: backend?.internalApiKey,
    })
    console.log('AUTH_E2E: running critical Chromium authentication journeys')
    const playwright = playwrightInvocation(
      process.execPath,
      playwrightArgs,
      options.playwrightConfig
    )
    await runProcess(playwright.command, playwright.args, {
      cwd: frontendDirectory,
      env: {
        ...(options.realApi
          ? allowlistedChildEnvironment(process.env)
          : process.env),
        ...authEnvironment,
        ...(backend
          ? {
              CYBERTRACE_E2E_FASTAPI_URL: backend.url,
              CYBERTRACE_E2E_WAF_KEY: backend.wafApiKey,
            }
          : {}),
      },
      label: 'Authentication Playwright suite',
      signal,
    })
  } finally {
    if (backend) await backend.close()
    unregisterBackend()
    await restProxy.close()
    unregisterRestProxy()
  }
}

export async function runManagedAuthE2E(playwrightArgs = [], options = {}) {
  const names = createDisposableNames()
  const cleanupEntries = []
  let cleanupPromise = null
  const registerCleanup = (callback) => {
    const entry = { active: true, callback }
    cleanupEntries.push(entry)
    return () => {
      entry.active = false
    }
  }
  registerCleanup(() => removeDisposableResources(names))
  const cleanup = () => {
    if (cleanupPromise) return cleanupPromise
    cleanupPromise = (async () => {
      let firstError = null
      for (const entry of cleanupEntries.toReversed()) {
        if (!entry.active) continue
        entry.active = false
        try {
          await entry.callback()
        } catch (error) {
          firstError ??= error
        }
      }
      if (firstError) throw firstError
    })()
    return cleanupPromise
  }
  return withManagedSignalCleanup(
    (signal) =>
      provisionAndRun(
        names,
        playwrightArgs,
        options,
        registerCleanup,
        signal
      ),
    cleanup
  )
}

export async function withManagedSignalCleanup(
  execute,
  cleanup,
  {
    processObject = process,
    abortController = new AbortController(),
  } = {}
) {
  let receivedSignal = null
  const handleSignal = (signal) => {
    if (receivedSignal) return
    receivedSignal = signal
    processObject.exitCode = signal === 'SIGINT' ? 130 : 143
    abortController.abort(new Error(`Managed E2E interrupted by ${signal}.`))
  }
  const onSigint = () => handleSignal('SIGINT')
  const onSigterm = () => handleSignal('SIGTERM')
  processObject.once('SIGINT', onSigint)
  processObject.once('SIGTERM', onSigterm)
  try {
    return await execute(abortController.signal)
  } finally {
    await cleanup()
    processObject.off('SIGINT', onSigint)
    processObject.off('SIGTERM', onSigterm)
  }
}
