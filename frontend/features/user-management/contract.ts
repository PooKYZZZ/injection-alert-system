import { z } from 'zod'

import type { UserRole } from '@/lib/auth/roles'

const normalizedEmail = z
  .string()
  .trim()
  .max(320)
  .email()
  .transform((value) => value.toLowerCase())

export const createAccountSchema = z.object({
  email: normalizedEmail,
  display_name: z.string().trim().min(1).max(120),
  role: z.enum(['ADMIN', 'ANALYST', 'VIEWER']),
}).strict()

export const managedEmailSchema = z.object({
  email: normalizedEmail,
})

export const accountRoleSchema = z.object({
  role: z.enum(['ADMIN', 'ANALYST', 'VIEWER']),
})

export const accountEnabledSchema = z.object({ enabled: z.boolean() })

export type SafeManagedAccount = {
  id: string
  display_name: string
  email: string
  pending_email: string | null
  role: UserRole
  enabled: boolean
  email_verified: boolean
  mfa_status: 'not_required' | 'enrollment_required' | 'active'
  created_at: string
}

export function mfaRequiredForRole(role: UserRole): boolean {
  return role !== 'VIEWER'
}
