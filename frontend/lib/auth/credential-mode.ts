export const AUTH_CREDENTIAL_FIELDS = {
  identifier: {
    label: 'Email or username',
    type: 'text',
    placeholder: '',
  },
  password: { label: 'Password', type: 'password', placeholder: '' },
  mfa_completion_token: {
    label: 'MFA completion token',
    type: 'password',
    placeholder: '',
  },
  recovery_completion_token: {
    label: 'Recovery completion token',
    type: 'password',
    placeholder: '',
  },
} as const

export type CredentialMode =
  | { kind: 'password'; identifier: string; password: string }
  | { kind: 'mfa_completion'; token: string }
  | { kind: 'recovery_completion'; token: string }

const CREDENTIAL_KEYS = [
  'identifier',
  'password',
  'mfa_completion_token',
  'recovery_completion_token',
] as const

type CredentialKey = (typeof CREDENTIAL_KEYS)[number]

function credentialValue(
  credentials: Record<string, unknown>,
  key: CredentialKey
): string | null | undefined {
  const value = credentials[key]
  if (value === undefined || value === null || value === '') return null
  return typeof value === 'string' ? value : undefined
}

export function parseCredentialMode(
  input: Record<string, unknown> | undefined
): CredentialMode | null {
  if (!input) return null

  const values = Object.fromEntries(
    CREDENTIAL_KEYS.map((key) => [key, credentialValue(input, key)])
  ) as Record<CredentialKey, string | null | undefined>

  if (CREDENTIAL_KEYS.some((key) => values[key] === undefined)) return null

  const passwordModeRequested =
    values.identifier !== null || values.password !== null
  const mfaModeRequested = values.mfa_completion_token !== null
  const recoveryModeRequested = values.recovery_completion_token !== null
  const requestedModeCount = [
    passwordModeRequested,
    mfaModeRequested,
    recoveryModeRequested,
  ].filter(Boolean).length

  if (requestedModeCount !== 1) return null

  if (passwordModeRequested) {
    const identifier = values.identifier
    const password = values.password
    if (typeof identifier !== 'string' || typeof password !== 'string') {
      return null
    }
    return {
      kind: 'password',
      identifier,
      password,
    }
  }
  if (mfaModeRequested) {
    const token = values.mfa_completion_token
    return typeof token === 'string'
      ? { kind: 'mfa_completion', token }
      : null
  }
  const token = values.recovery_completion_token
  return typeof token === 'string'
    ? { kind: 'recovery_completion', token }
    : null
}
