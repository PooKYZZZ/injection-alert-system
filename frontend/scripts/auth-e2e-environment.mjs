import { spawn } from 'node:child_process'
import { createHmac, randomBytes, randomUUID } from 'node:crypto'
import { existsSync } from 'node:fs'
import { createServer, request as createHttpRequest } from 'node:http'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const DISPOSABLE_PREFIX = 'cybertrace-auth-e2e-'
const POSTGRES_IMAGE = 'postgres:17.6'
const POSTGREST_IMAGE = 'postgrest/postgrest:v14.14'
const DATABASE_NAME = 'cybertrace'
const POSTGRES_USER = 'postgres'
const FRONTEND_ORIGIN = 'http://127.0.0.1:3000'

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
}) {
  return {
    SUPABASE_URL: supabaseUrl,
    SUPABASE_SERVICE_ROLE_KEY: serviceRoleToken,
    AUTH_SECRET: authSecret,
    NEXTAUTH_URL: FRONTEND_ORIGIN,
    AUTH_TRUST_HOST: 'true',
    AUTH_APP_ORIGIN: FRONTEND_ORIGIN,
    AUTH_MFA_ENCRYPTION_KEY: mfaEncryptionKey,
    AUTH_EMAIL_OTP_KEY: emailOtpKey,
    NOTIFICATION_PAYLOAD_ENCRYPTION_KEY: notificationPayloadKey,
    AUTH_ACCOUNT_MANAGEMENT_ENABLED: 'true',
    AUTH_MFA_ENROLLMENT_ENABLED: 'true',
    AUTH_EMAIL_RECOVERY_ENABLED: 'true',
    AUTH_PASSWORD_RESET_ENABLED: 'true',
    AUTH_TURNSTILE_ENABLED: 'false',
    USE_MOCK_API: 'true',
    PLAYWRIGHT_BASE_URL: FRONTEND_ORIGIN,
    CYBERTRACE_E2E_MANAGED: 'true',
  }
}

export function playwrightInvocation(
  nodeExecutable = process.execPath,
  playwrightArgs = []
) {
  return {
    command: nodeExecutable,
    args: [
      path.join(frontendDirectory, 'node_modules', 'playwright', 'cli.js'),
      'test',
      '--config=playwright.auth.config.ts',
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
  return {
    url: `http://127.0.0.1:${address.port}`,
    close: () =>
      new Promise((resolve, reject) => {
        server.close((error) => (error ? reject(error) : resolve()))
      }),
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
  } = {}
) {
  return new Promise((resolve, reject) => {
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
      reject(new Error(`${label} could not start.`))
    })
    child.on('close', (code) => {
      const result = { code: code ?? 1, stdout, stderr }
      if (result.code === 0 || allowFailure) {
        resolve(result)
      } else {
        reject(new Error(`${label} failed.`))
      }
    })
  })
}

async function waitFor(description, probe, timeoutMs = 60_000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await probe()) return
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  throw new Error(`${description} did not become ready.`)
}

async function dockerPublishedPort(container, containerPort) {
  const result = await runProcess(
    'docker',
    ['port', container, `${containerPort}/tcp`],
    { capture: true, label: 'Docker port lookup' }
  )
  return parsePublishedPort(result.stdout)
}

async function runPsql(container, sql) {
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
    { input: sql, label: 'Disposable PostgreSQL setup' }
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

function pythonExecutable() {
  const candidate =
    process.platform === 'win32'
      ? path.join(repositoryDirectory, '.venv', 'Scripts', 'python.exe')
      : path.join(repositoryDirectory, '.venv', 'bin', 'python')
  if (!existsSync(candidate)) {
    throw new Error('Repository Python virtual environment is unavailable.')
  }
  return candidate
}

async function provisionAndRun(names, playwrightArgs) {
  const postgresPassword = randomHex(24)
  const authenticatorPassword = randomHex(24)
  const jwtSecret = randomHex(32)
  const serviceRoleToken = createServiceRoleToken(jwtSecret)

  console.log('AUTH_E2E: creating disposable PostgreSQL and PostgREST')
  await runProcess('docker', ['version'], {
    capture: true,
    label: 'Docker availability check',
  })
  await runProcess('docker', ['network', 'create', names.network], {
    capture: true,
    label: 'Docker network creation',
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
      { capture: true, allowFailure: true }
    )
    return result.code === 0 && result.stdout.trim() === '1'
  })

  await runPsql(
    names.postgres,
    `
CREATE ROLE anon NOLOGIN;
CREATE ROLE authenticated NOLOGIN;
CREATE ROLE service_role NOLOGIN BYPASSRLS;
CREATE ROLE authenticator NOINHERIT LOGIN PASSWORD '${authenticatorPassword}';
GRANT anon, authenticated, service_role TO authenticator;
`
  )

  const postgresPort = await dockerPublishedPort(names.postgres, 5432)
  const databaseUrl = `postgresql+psycopg://${POSTGRES_USER}:${postgresPassword}@127.0.0.1:${postgresPort}/${DATABASE_NAME}`
  console.log('AUTH_E2E: applying the real Alembic migration chain')
  await runProcess(pythonExecutable(), ['-m', 'alembic', 'upgrade', 'head'], {
    env: {
      ...process.env,
      DATABASE_URL: databaseUrl,
      CYBERTRACE_POSTGRES_TEST_URL: databaseUrl,
    },
    label: 'Alembic upgrade',
  })
  await runPsql(
    names.postgres,
    `
GRANT USAGE ON SCHEMA public TO service_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO service_role;
GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO service_role;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO service_role;
`
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
    }
  )

  const postgrestPort = await dockerPublishedPort(names.postgrest, 3000)
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
  })

  const restProxy = await startSupabaseRestProxy(supabaseUrl)
  try {
    const authEnvironment = buildAuthE2EEnvironment({
      supabaseUrl: restProxy.url,
      serviceRoleToken,
      authSecret: randomHex(32),
      mfaEncryptionKey: randomBytes(32).toString('base64'),
      emailOtpKey: randomHex(32),
      notificationPayloadKey: randomBytes(32).toString('base64'),
    })
    console.log('AUTH_E2E: running critical Chromium authentication journeys')
    const playwright = playwrightInvocation(process.execPath, playwrightArgs)
    await runProcess(playwright.command, playwright.args, {
      cwd: frontendDirectory,
      env: { ...process.env, ...authEnvironment },
      label: 'Authentication Playwright suite',
    })
  } finally {
    await restProxy.close()
  }
}

export async function runManagedAuthE2E(playwrightArgs = []) {
  const names = createDisposableNames()
  return withDisposableCleanup(
    names,
    (resources) => provisionAndRun(resources, playwrightArgs),
    removeDisposableResources
  )
}
