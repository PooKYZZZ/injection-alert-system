# Auth Security Hardening Foundation

**Status:** Accepted and implemented for the PR 1 foundation
**Date:** 2026-07-04

## Decision

CyberTrace adds an auth/security schema foundation in PostgreSQL and an isolated
server-only Supabase client. This is additive infrastructure for later account
provisioning and MFA work. Current Auth.js Credentials login remains
`AUTH_USERS_JSON`-backed with scrypt and is unchanged.

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
- No signup, Supabase Auth migration, provisioning, MFA runtime, notification
  provider, bot defense, or login cutover is part of this change.

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
| Disabled/downgraded user with valid JWT | Existing `authz_version` freshness checks remain and must survive DB cutover. |
| Account enumeration | Keep generic login/reset responses and no public signup. |
| Provider outage | TOTP and backup-code paths must remain independent of notification providers. |
| Bot abuse | Existing local throttling remains; server-validated Turnstile is deferred. |
| Supabase outage during defense | Future DB-backed login fails closed; there is no hidden env fallback after cutover. |
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

The migration has offline DDL and migration-test coverage. It was also verified
against a disposable PostgreSQL 17.6 database: the full migration chain upgraded
from an empty database to `20260704_000008`, the PR 1 schema and controls passed
direct assertions, downgrade to `20260324_000007` removed only PR 1 objects, and
re-upgrade to head succeeded. No migration was applied to live Supabase.

## Deferred work

Argon2id, account provisioning, login cutover, MFA enforcement, email OTP,
Resend, Telegram, Turnstile, and administrator UI remain planned.
