import type { UserRole } from './roles'

type FailureReason =
  | 'INVALID_CREDENTIALS'
  | 'IDENTIFIER_THROTTLED'
  | 'GLOBAL_THROTTLED'
  | 'PASSWORD_HASH_BUSY'
  | 'CONFIGURATION_INVALID'
  | 'ACCOUNT_LOOKUP_FAILED'

type LoginSuccessEvent = {
  event: 'auth.login_succeeded'
  level: 'info'
  outcome: 'success'
  userId: string
  role: UserRole
  authzVersion: number
}

type LoginFailureEvent = {
  event:
    | 'auth.login_failed'
    | 'auth.login_throttled'
    | 'auth.configuration_invalid'
    | 'auth.account_lookup_failed'
  level: 'warn' | 'error'
  outcome: 'failure' | 'throttled'
  identifierHash: string
  reasonCode: FailureReason
}

type AuthorizationEvent = {
  event:
    | 'auth.rbac_forbidden'
    | 'auth.session_stale'
    | 'auth.account_removed'
    | 'auth.account_disabled'
    | 'auth.account_lookup_failed'
    | 'auth.role_mismatch'
  level: 'warn'
  outcome: 'denied'
  userId: string
  role: UserRole
  authzVersion: number
  reasonCode:
    | 'PERMISSION_DENIED'
    | 'AUTHZ_VERSION_MISMATCH'
    | 'ACCOUNT_REMOVED'
    | 'ACCOUNT_DISABLED'
    | 'ACCOUNT_LOOKUP_FAILED'
    | 'ROLE_MISMATCH'
}

export type LoginAuditEvent =
  | LoginSuccessEvent
  | LoginFailureEvent
  | AuthorizationEvent

function sanitizeRawText(value: string): string {
  return Array.from(value)
    .filter((character) => {
      const code = character.charCodeAt(0)
      return code > 31 && code !== 127
    })
    .join('')
    .slice(0, 128)
}

export function writeLoginAudit(event: LoginAuditEvent): void {
  try {
    const base = {
      timestamp: new Date().toISOString(),
      level: event.level,
      event: event.event,
      component: 'auth',
      outcome: event.outcome,
    }

    let payload
    if (event.event === 'auth.login_succeeded') {
      payload = {
        ...base,
        user_id: sanitizeRawText(event.userId),
        role: event.role,
        authz_version: event.authzVersion,
      }
    } else if ('identifierHash' in event) {
      payload = {
        ...base,
        identifier_hash: event.identifierHash,
        reason_code: event.reasonCode,
      }
    } else {
      payload = {
        ...base,
        user_id: sanitizeRawText(event.userId),
        role: event.role,
        authz_version: event.authzVersion,
        reason_code: event.reasonCode,
      }
    }

    console.info(JSON.stringify(payload))
  } catch {
    // Authentication must not depend on the availability of the log sink.
  }
}
