import 'server-only'

import { z } from 'zod'

import { ROLE_VALUES, type UserRole } from '@/lib/auth/roles'
import { getSupabaseServerClient } from './client'

export type AuthAccountForLogin = {
  id: string
  email: string
  username: string | null
  name: string
  role: UserRole
  authzVersion: number
  passwordHash: string | null
  mfaRequired: boolean
  disabledAt: string | null
}

export type AuthAccountForSessionFreshness = {
  id: string
  role: UserRole
  authzVersion: number
  mfaRequired: boolean
  disabledAt: string | null
}

const LOGIN_FIELDS =
  'id,email,username,name,role,authz_version,password_hash,mfa_required,disabled_at'
const FRESHNESS_FIELDS = 'id,role,authz_version,mfa_required,disabled_at'
const LOOKUP_FAILURE_MESSAGE = 'Unable to read authentication account.'
const MAX_IDENTIFIER_LENGTH = 320

type AuthAccountLookupSource = 'login' | 'session_freshness'
type AuthAccountLookupFailureClass =
  | 'client_setup'
  | 'request_timeout'
  | 'transport_error'
  | 'data_api_error'
  | 'invalid_account_record'
  | 'unexpected'

type AuthAccountLookupDiagnostic = {
  failureClass: AuthAccountLookupFailureClass
  upstreamErrorCode?: string
  upstreamStatus?: number
}

const loginAccountSchema = z.object({
  id: z.string().uuid(),
  email: z.string().trim().email(),
  username: z.string().trim().min(1).nullable(),
  name: z.string().trim().min(1),
  role: z.enum(ROLE_VALUES),
  authz_version: z.number().int().min(1),
  password_hash: z.string().nullable(),
  mfa_required: z.boolean(),
  disabled_at: z.string().min(1).nullable(),
})

const freshnessAccountSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(ROLE_VALUES),
  authz_version: z.number().int().min(1),
  mfa_required: z.boolean(),
  disabled_at: z.string().min(1).nullable(),
})

class AuthAccountLookupError extends Error {
  constructor() {
    super(LOOKUP_FAILURE_MESSAGE)
    this.name = 'AuthAccountLookupError'
  }
}

function safeUpstreamErrorCode(error: unknown): string | undefined {
  if (typeof error !== 'object' || error === null || !('code' in error)) {
    return undefined
  }

  const code = error.code
  return typeof code === 'string' && /^(?:PGRST\d{3}|[A-Z0-9]{5})$/.test(code)
    ? code
    : undefined
}

function safeUpstreamStatus(status: unknown): number | undefined {
  return typeof status === 'number' && Number.isInteger(status) && status >= 400 && status <= 599
    ? status
    : undefined
}

function reportLookupFailure(
  source: AuthAccountLookupSource,
  diagnostic: AuthAccountLookupDiagnostic
): AuthAccountLookupError {
  try {
    console.warn(
      JSON.stringify({
        timestamp: new Date().toISOString(),
        level: 'warn',
        event: 'auth.account_lookup_diagnostic',
        component: 'auth',
        lookup_source: source,
        failure_class: diagnostic.failureClass,
        ...(diagnostic.upstreamErrorCode
          ? { upstream_error_code: diagnostic.upstreamErrorCode }
          : {}),
        ...(diagnostic.upstreamStatus
          ? { upstream_status: diagnostic.upstreamStatus }
          : {}),
      })
    )
  } catch {
    // Authentication must not depend on the availability of the log sink.
  }

  return new AuthAccountLookupError()
}

function classifyRequestFailure(error: unknown): AuthAccountLookupDiagnostic {
  const errorName =
    error instanceof Error
      ? error.name
      : typeof error === 'object' && error !== null && 'message' in error &&
          typeof error.message === 'string'
        ? /^(AbortError|TimeoutError|TypeError):/.exec(error.message)?.[1]
        : undefined

  if (errorName === 'TimeoutError' || errorName === 'AbortError') {
    return { failureClass: 'request_timeout' }
  }
  if (error instanceof TypeError || errorName === 'TypeError') {
    return { failureClass: 'transport_error' }
  }
  return { failureClass: 'unexpected' }
}

function classifyDataApiFailure(
  error: unknown,
  responseStatus: number
): AuthAccountLookupDiagnostic {
  if (responseStatus === 0) {
    const requestFailure = classifyRequestFailure(error)
    return requestFailure.failureClass === 'unexpected'
      ? { failureClass: 'transport_error' }
      : requestFailure
  }

  const upstreamErrorCode = safeUpstreamErrorCode(error)
  const upstreamStatus = safeUpstreamStatus(responseStatus)

  return {
    failureClass: 'data_api_error',
    ...(upstreamErrorCode ? { upstreamErrorCode } : {}),
    ...(upstreamStatus ? { upstreamStatus } : {}),
  }
}

function normalizeIdentifier(identifier: string): string {
  return identifier.trim().toLowerCase()
}

async function selectAccount(
  fields: string,
  column: 'id' | 'email' | 'username',
  value: string,
  source: AuthAccountLookupSource
): Promise<unknown | undefined> {
  let supabaseClient: ReturnType<typeof getSupabaseServerClient>
  try {
    supabaseClient = getSupabaseServerClient()
  } catch {
    throw reportLookupFailure(source, { failureClass: 'client_setup' })
  }

  try {
    const response = await supabaseClient
      .from('auth_accounts')
      .select(fields)
      .eq(column, value)
      .maybeSingle()

    if (response.error) {
      throw reportLookupFailure(
        source,
        classifyDataApiFailure(response.error, response.status)
      )
    }
    return response.data ?? undefined
  } catch (error) {
    if (error instanceof AuthAccountLookupError) {
      throw error
    }
    throw reportLookupFailure(source, classifyRequestFailure(error))
  }
}

function mapLoginAccount(value: unknown): AuthAccountForLogin {
  const account = loginAccountSchema.safeParse(value)
  if (!account.success) {
    throw reportLookupFailure('login', {
      failureClass: 'invalid_account_record',
    })
  }
  return {
    id: account.data.id,
    email: account.data.email,
    username: account.data.username,
    name: account.data.name,
    role: account.data.role,
    authzVersion: account.data.authz_version,
    passwordHash: account.data.password_hash,
    mfaRequired: account.data.mfa_required,
    disabledAt: account.data.disabled_at,
  }
}

export async function findAuthAccountByIdentifier(
  identifier: string
): Promise<AuthAccountForLogin | undefined> {
  const normalized = normalizeIdentifier(identifier)
  if (!normalized || normalized.length > MAX_IDENTIFIER_LENGTH) {
    return undefined
  }

  if (z.string().uuid().safeParse(normalized).success) {
    const account = await selectAccount(LOGIN_FIELDS, 'id', normalized, 'login')
    return account === undefined ? undefined : mapLoginAccount(account)
  }

  const emailAccount = await selectAccount(
    LOGIN_FIELDS,
    'email',
    normalized,
    'login'
  )
  if (emailAccount !== undefined) {
    return mapLoginAccount(emailAccount)
  }

  const usernameAccount = await selectAccount(
    LOGIN_FIELDS,
    'username',
    normalized,
    'login'
  )
  return usernameAccount === undefined
    ? undefined
    : mapLoginAccount(usernameAccount)
}

export async function getAccountForSessionFreshness(
  id: string
): Promise<AuthAccountForSessionFreshness | undefined> {
  const normalized = normalizeIdentifier(id)
  if (!z.string().uuid().safeParse(normalized).success) {
    return undefined
  }

  const value = await selectAccount(
    FRESHNESS_FIELDS,
    'id',
    normalized,
    'session_freshness'
  )
  if (value === undefined) {
    return undefined
  }

  const account = freshnessAccountSchema.safeParse(value)
  if (!account.success) {
    throw reportLookupFailure('session_freshness', {
      failureClass: 'invalid_account_record',
    })
  }
  return {
    id: account.data.id,
    role: account.data.role,
    authzVersion: account.data.authz_version,
    mfaRequired: account.data.mfa_required,
    disabledAt: account.data.disabled_at,
  }
}
