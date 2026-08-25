type LoginMfaPageSession = {
  user?: {
    auth_level?: unknown
    auth_method?: unknown
    mfa_challenge_purpose?: unknown
    mfa_challenge_expires_at?: unknown
  }
}

export function canRenderLoginMfaPage(
  session: unknown,
  preAuthHandle: string | null,
  nowMs = Date.now(),
): boolean {
  if (!preAuthHandle?.trim() || typeof session !== 'object' || session === null) {
    return false
  }

  const user = (session as LoginMfaPageSession).user
  if (!user) return false

  const expiresAt =
    typeof user.mfa_challenge_expires_at === 'string'
      ? Date.parse(user.mfa_challenge_expires_at)
      : Number.NaN

  return (
    user.auth_level === 'password' &&
    user.auth_method === 'password' &&
    user.mfa_challenge_purpose === 'login_mfa' &&
    Number.isFinite(expiresAt) &&
    expiresAt > nowMs
  )
}
