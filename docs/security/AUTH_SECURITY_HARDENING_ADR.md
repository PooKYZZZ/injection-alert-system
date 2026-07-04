# Auth Security Hardening Foundation

**Status:** Accepted and implemented through the PR 3 account cutover
**Date:** 2026-07-04

## Decision

CyberTrace uses the PostgreSQL auth/security schema and isolated server-only
Supabase client for Auth.js Credentials login and request-time session
freshness. `auth_accounts` is the runtime source of truth. Password hashes are
Argon2id PHC strings; null, old scrypt, malformed, and unsupported hashes are
rejected. `AUTH_USERS_JSON` is not a runtime fallback.

The tables use the existing Alembic and `public` schema convention. Row-level
security is enabled on every new table, privileges are revoked from `PUBLIC`,
`anon`, and `authenticated`, and no RLS policies are created. A private schema
may be revisited if deployment hardening requires it.

RLS is defense-in-depth only. Supabase documents that exposed `public` tables
should use RLS, but the service-role credential has elevated access and bypasses
RLS. The actual current boundary is keeping `SUPABASE_SERVICE_ROLE_KEY` inside
server-only code and authorizing every privileged database operation.

References:

- [Supabase API keys](https://supabase.com/docs/guides/getting-started/api-keys)
- [Supabase Row Level Security](https://supabase.com/docs/guides/database/postgres/row-level-security)
- [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html)
- [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)

## Boundaries

- `frontend/lib/server/db/` is the only service-role client location.
- `import 'server-only'` prevents browser imports of the client module.
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` fail closed when absent.
- `NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY` is forbidden.
- Validation errors identify variable names without values and do not log.
- No signup, Supabase Auth migration, MFA runtime, notification provider, bot
  defense, password reset, or administrator UI is part of the PR 3 cutover.

## Threat model

| Threat | Foundation decision or later control |
| --- | --- |
| Stolen password | Current throttling remains; later MFA must prevent a password alone from producing a final session. |
| Stolen email inbox | Email OTP is a weaker fallback; TOTP remains primary and backup codes are preferred recovery. |
| Replayed TOTP | `last_used_time_step` supports atomic replay rejection later. |
| Reused email OTP | Status, expiry, attempts, and `used_at` support atomic single-use consumption later. |
| Reused backup code | Hash-only storage and `used_at` support atomic single-use consumption later. |
| Leaked DB contents | Passwords, tokens, and codes are designed for hash-only storage; TOTP secrets require encryption and key versioning later. |
| Leaked Supabase service key | Rotate immediately and audit access. RLS does not contain service-role access. |
| Disabled/downgraded user with valid JWT | Every protected BFF request loads the current DB row and denies missing, disabled, role-mismatched, or stale `authz_version` sessions. |
| Account enumeration | Keep generic login/reset responses and no public signup. |
| Provider outage | TOTP and backup-code paths must remain independent of notification providers. |
| Bot abuse | Existing local throttling remains; server-validated Turnstile is deferred. |
| Supabase outage during defense | Login and protected BFF access fail closed; there is no hidden env fallback. |
| Resend outage | Future email OTP sending fails without breaking TOTP or backup codes. |
| Server clock drift | Verify server time operationally before TOTP is enabled or demonstrated. |

## Email OTP risk acceptance

Email OTP is required as a project fallback but is weaker than TOTP. CyberTrace
does not claim it is phishing-resistant or NIST-grade out-of-band MFA. TOTP
remains primary and backup codes remain the preferred recovery method. Later
ADMIN email-OTP use must create a high-severity audited event and operator alert.

## Schema and rollback

The migration creates account, MFA factor/challenge/completion, email OTP,
backup/reset token, security-event, and notification-outbox tables. The outbox
includes lock, retry, deduplication, status, safe-payload, and error-code fields.

Rollback drops only these new foundation tables. Once later PRs store account or
security data, destructive downgrade requires a backup and explicit operator
approval. This PR does not apply the migration to live Supabase.

PR 3 rollback is code-first: revert the account-source cutover, then restore a
secure pre-cutover `AUTH_USERS_JSON` value if required. Restoring the env value
without reverting code has no effect. Keep the auth tables intact during normal
rollback.

The migration has offline DDL and migration-test coverage. It was also verified
against a disposable PostgreSQL 17.6 database: the full migration chain upgraded
from an empty database to `20260704_000008`, the PR 1 schema and controls passed
direct assertions, downgrade to `20260324_000007` removed only PR 1 objects, and
re-upgrade to head succeeded. No migration was applied to live Supabase.

## Deferred work

Argon2id account provisioning and Supabase account login are implemented in
repo. Reviewed migration application and account creation remain manual
environment operations. Until MFA is implemented, `mfa_required=true` accounts
fail closed; temporary PR 3 demo accounts must explicitly use
`mfa_required=false`.

MFA enforcement, email OTP, Resend, Telegram, Turnstile, password reset, and
administrator UI remain planned for later PRs.
