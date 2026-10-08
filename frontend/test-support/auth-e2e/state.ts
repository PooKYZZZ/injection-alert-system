import { z } from 'zod'

const disposableEmail = z
  .string()
  .email()
  .refine((value) => value.endsWith('@example.test'))

const identitySchema = z.object({
  id: z.string().uuid(),
  email: disposableEmail,
  password: z.string().min(6).max(256),
})

const totpIdentitySchema = identitySchema.extend({
  totpSecret: z.string().regex(/^[A-Z2-7]{16,128}$/),
})

const backupIdentitySchema = identitySchema.extend({
  backupCode: z
    .string()
    .regex(/^[2-9A-HJ-NP-Z]{4}(?:-[2-9A-HJ-NP-Z]{4}){2}$/),
})

const roleMatrixSchema = z.object({
  owner: totpIdentitySchema,
  admin: totpIdentitySchema,
  analyst: totpIdentitySchema,
  viewer: identitySchema,
})

const authE2EStateSchema = z
  .object({
    runId: z.string().uuid(),
    identities: z.object({
      enroll: identitySchema,
      login: totpIdentitySchema,
      backup: backupIdentitySchema,
      email: identitySchema,
      stepup: totpIdentitySchema,
      dashboard: totpIdentitySchema,
      managedTargets: z.array(identitySchema).length(2),
    }),
    roleMatrix: roleMatrixSchema,
  })
  .superRefine((state, context) => {
    const identities = [
      state.identities.enroll,
      state.identities.login,
      state.identities.backup,
      state.identities.email,
      state.identities.stepup,
      state.identities.dashboard,
      ...state.identities.managedTargets,
      ...Object.values(state.roleMatrix),
    ]
    if (new Set(identities.map(({ id }) => id)).size !== identities.length) {
      context.addIssue({ code: 'custom', message: 'Identity ids must be unique.' })
    }
    if (
      new Set(identities.map(({ email }) => email)).size !== identities.length
    ) {
      context.addIssue({
        code: 'custom',
        message: 'Identity emails must be unique.',
      })
    }
  })

export type AuthE2EState = z.infer<typeof authE2EStateSchema>
export type AuthE2EIdentity =
  | AuthE2EState['identities']['enroll']
  | AuthE2EState['identities']['login']
  | AuthE2EState['identities']['backup']
  | AuthE2EState['identities']['email']
  | AuthE2EState['identities']['stepup']
  | AuthE2EState['identities']['dashboard']
export type AuthE2ERole = keyof AuthE2EState['roleMatrix']
export type AuthE2ERoleIdentity = AuthE2EState['roleMatrix'][AuthE2ERole]

export function parseAuthE2EState(raw: string | undefined): AuthE2EState {
  try {
    const result = authE2EStateSchema.safeParse(JSON.parse(raw ?? ''))
    if (result.success) return result.data
  } catch {
    // Fall through to the fixed, non-secret-bearing error below.
  }
  throw new Error('Authentication E2E state is unavailable.')
}

export function requireAuthE2EState(): AuthE2EState {
  return parseAuthE2EState(process.env.CYBERTRACE_E2E_STATE)
}
