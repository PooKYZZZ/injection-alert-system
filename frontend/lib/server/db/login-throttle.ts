import 'server-only'

import { randomUUID } from 'node:crypto'
import { z } from 'zod'

import { readLoginThrottlePolicy } from '@/lib/auth/login-throttle-policy'
import { getSupabaseServerClient } from './client'

const UUID = z.string().uuid()
const beginRowSchema = z.object({
  allowed: z.boolean(),
  reason_code: z
    .enum(['VERIFICATION_REQUIRED', 'IDENTIFIER_THROTTLED'])
    .nullable(),
  failure_count: z.number().int().min(0),
  reservation_id: UUID.nullable(),
})
const completeRowSchema = z.object({
  completed: z.boolean(),
  failure_count: z.number().int().min(0),
  cooldown_active: z.boolean(),
})

export type LoginThrottleStartResult =
  | { allowed: true; failureCount: number; attemptId: string }
  | {
      allowed: false
      failureCount: number
      reasonCode: 'VERIFICATION_REQUIRED' | 'IDENTIFIER_THROTTLED'
    }

export type LoginThrottleCompletion = {
  completed: boolean
  failureCount: number
  cooldownActive: boolean
}

function unavailable(): Error {
  return new Error('Login throttle is unavailable.')
}

function parseSingleRow<T>(
  data: unknown,
  schema: z.ZodType<T>
): T {
  if (!Array.isArray(data) || data.length !== 1) throw unavailable()
  const parsed = schema.safeParse(data[0])
  if (!parsed.success) throw unavailable()
  return parsed.data
}

function accountId(value: string): string {
  const parsed = UUID.safeParse(value)
  if (!parsed.success) throw unavailable()
  return parsed.data
}

export async function beginLoginThrottleAttempt(
  accountIdInput: string,
  options: { turnstileEnabled: boolean; turnstileVerified: boolean }
): Promise<LoginThrottleStartResult> {
  const account = accountId(accountIdInput)
  const attemptId = randomUUID()
  const policy = readLoginThrottlePolicy()

  try {
    const { data, error } = await getSupabaseServerClient().rpc(
      'begin_auth_login_attempt_v1',
      {
        p_account_id: account,
        p_attempt_id: attemptId,
        p_turnstile_enabled: options.turnstileEnabled,
        p_turnstile_verified: options.turnstileVerified,
        p_challenge_threshold: policy.challengeThreshold,
        p_max_failures: policy.maxFailures,
        p_window_seconds: policy.windowSeconds,
        p_cooldown_seconds: policy.cooldownSeconds,
      }
    )
    if (error) throw unavailable()

    const row = parseSingleRow(data, beginRowSchema)
    if (row.allowed) {
      if (row.reason_code !== null || row.reservation_id !== attemptId) {
        throw unavailable()
      }
      return {
        allowed: true,
        failureCount: row.failure_count,
        attemptId,
      }
    }
    if (row.reason_code === null || row.reservation_id !== null) {
      throw unavailable()
    }
    return {
      allowed: false,
      failureCount: row.failure_count,
      reasonCode: row.reason_code,
    }
  } catch {
    throw unavailable()
  }
}

export async function completeLoginThrottleAttempt(
  accountIdInput: string,
  attemptIdInput: string,
  outcome: 'success' | 'failure' | 'abandoned'
): Promise<LoginThrottleCompletion> {
  const account = accountId(accountIdInput)
  const attempt = UUID.safeParse(attemptIdInput)
  if (!attempt.success) throw unavailable()
  const policy = readLoginThrottlePolicy()

  try {
    const { data, error } = await getSupabaseServerClient().rpc(
      'complete_auth_login_attempt_v1',
      {
        p_account_id: account,
        p_attempt_id: attempt.data,
        p_outcome: outcome,
        p_max_failures: policy.maxFailures,
        p_window_seconds: policy.windowSeconds,
        p_cooldown_seconds: policy.cooldownSeconds,
      }
    )
    if (error) throw unavailable()
    const row = parseSingleRow(data, completeRowSchema)
    return {
      completed: row.completed,
      failureCount: row.failure_count,
      cooldownActive: row.cooldown_active,
    }
  } catch {
    throw unavailable()
  }
}
