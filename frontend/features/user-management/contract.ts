import { z } from 'zod'

import { ROLE_VALUES, roleRequiresMfa, type UserRole } from '@/lib/auth/roles'

const normalizedEmail = z
  .string()
  .trim()
  .max(320)
  .email()
  .transform((value) => value.toLowerCase())

export const createAccountSchema = z.object({
  email: normalizedEmail,
  display_name: z.string().trim().min(1).max(120),
  role: z.enum(ROLE_VALUES),
}).strict()

export const managedEmailSchema = z.object({
  email: normalizedEmail,
})

export const accountRoleSchema = z.object({
  role: z.enum(ROLE_VALUES),
})

export const accountEnabledSchema = z.object({ enabled: z.boolean() })

export const safeManagedAccountSchema = z.object({
  id: z.string().uuid(),
  display_name: z.string().min(1),
  email: z.string().email(),
  pending_email: z.string().email().nullable(),
  role: z.enum(ROLE_VALUES),
  enabled: z.boolean(),
  email_verified: z.boolean(),
  mfa_status: z.enum(['not_required', 'enrollment_required', 'active']),
  setup_status: z.enum(['pending', 'complete']),
  created_at: z.string().datetime({ offset: true }),
}).strict()

export const managedAccountsResponseSchema = z.object({
  accounts: z.array(safeManagedAccountSchema),
}).strict()

export type SafeManagedAccount = z.infer<typeof safeManagedAccountSchema>

export function mfaRequiredForRole(role: UserRole): boolean {
  return roleRequiresMfa(role)
}
