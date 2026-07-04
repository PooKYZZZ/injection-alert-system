import 'server-only'

import { z } from 'zod'

import type { UserRole } from '@/lib/auth/roles'
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
  disabledAt: string | null
}

const LOGIN_FIELDS =
  'id,email,username,name,role,authz_version,password_hash,mfa_required,disabled_at'
const FRESHNESS_FIELDS = 'id,role,authz_version,disabled_at'
const LOOKUP_FAILURE_MESSAGE = 'Unable to read authentication account.'
const MAX_IDENTIFIER_LENGTH = 320

const loginAccountSchema = z.object({
  id: z.string().uuid(),
  email: z.string().trim().email(),
  username: z.string().trim().min(1).nullable(),
  name: z.string().trim().min(1),
  role: z.enum(['ADMIN', 'ANALYST', 'VIEWER']),
  authz_version: z.number().int().min(1),
  password_hash: z.string().nullable(),
  mfa_required: z.boolean(),
  disabled_at: z.string().min(1).nullable(),
})

const freshnessAccountSchema = z.object({
  id: z.string().uuid(),
  role: z.enum(['ADMIN', 'ANALYST', 'VIEWER']),
  authz_version: z.number().int().min(1),
  disabled_at: z.string().min(1).nullable(),
})

class AuthAccountLookupError extends Error {
  constructor() {
    super(LOOKUP_FAILURE_MESSAGE)
    this.name = 'AuthAccountLookupError'
  }
}

function normalizeIdentifier(identifier: string): string {
  return identifier.trim().toLowerCase()
}

async function selectAccount(
  fields: string,
  column: 'id' | 'email' | 'username',
  value: string
): Promise<unknown | undefined> {
  try {
    const { data, error } = await getSupabaseServerClient()
      .from('auth_accounts')
      .select(fields)
      .eq(column, value)
      .maybeSingle()

    if (error) {
      throw new AuthAccountLookupError()
    }
    return data ?? undefined
  } catch (error) {
    if (error instanceof AuthAccountLookupError) {
      throw error
    }
    throw new AuthAccountLookupError()
  }
}

function mapLoginAccount(value: unknown): AuthAccountForLogin {
  const account = loginAccountSchema.safeParse(value)
  if (!account.success) {
    throw new AuthAccountLookupError()
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
    const account = await selectAccount(LOGIN_FIELDS, 'id', normalized)
    return account === undefined ? undefined : mapLoginAccount(account)
  }

  const emailAccount = await selectAccount(LOGIN_FIELDS, 'email', normalized)
  if (emailAccount !== undefined) {
    return mapLoginAccount(emailAccount)
  }

  const usernameAccount = await selectAccount(
    LOGIN_FIELDS,
    'username',
    normalized
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

  const value = await selectAccount(FRESHNESS_FIELDS, 'id', normalized)
  if (value === undefined) {
    return undefined
  }

  const account = freshnessAccountSchema.safeParse(value)
  if (!account.success) {
    throw new AuthAccountLookupError()
  }
  return {
    id: account.data.id,
    role: account.data.role,
    authzVersion: account.data.authz_version,
    disabledAt: account.data.disabled_at,
  }
}
