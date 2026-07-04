# CyberTrace Auth Hardening Implementation Plan — Revised After Codex + Claude Reviews

**Project:** CyberTrace / Injection Alert System  
**Version:** 4.0 — project-grade clean cutover with required email OTP fallback  
**Date:** 2026-07-04  
**Purpose:** AI-agent-ready implementation plan for account cutover, Argon2id, MFA/2FA, email OTP fallback, backup codes, password reset, security events, notifications, and demo-safe operations.  
**Scope philosophy:** capstone-grade and production-minded, but not enterprise IAM. No public sign-up, no Supabase Auth migration, no Redis/Kafka/Celery/SIEM/Kubernetes unless future production deployment requires it.

---

## 0. Executive Decision

The reviewed plan is strong enough to keep as the base, but it must be tightened before implementation. The changes from the Codex/Claude reviews that should be accepted are:

1. Add a threat model and risk-acceptance section before implementation.
2. Reword email OTP as a required but weaker fallback, not equivalent to TOTP.
3. Reorder phases so Argon2id and account provisioning happen before Supabase login cutover.
4. Add `auth_mfa_completion_tokens` for safe Auth.js handoff after MFA succeeds.
5. Require every protected route/action/BFF path to check current DB account state and `authz_version`.
6. Treat Supabase service-role access as privileged backend access; RLS is defense-in-depth, not the main boundary.
7. Add explicit atomic SQL patterns for TOTP replay prevention, email OTP use, backup-code use, MFA challenge pass, and completion-token consume.
8. Add outbox worker claiming with `FOR UPDATE SKIP LOCKED`, `dedupe_key`, retry/backoff, and stuck-job recovery.
9. Add degraded-mode/demo-failure behavior for Supabase, Resend, Telegram, and clock drift.
10. Add lightweight CI/secret scanning as a merge gate because AI-agent PRs need automatic guardrails.

The final implementation model is:

```text
Admin/operator-created accounts only
        ↓
Supabase/Postgres auth_accounts as source of truth
        ↓
Argon2id-only password hashes
        ↓
Auth.js Credentials session only after full auth
        ↓
MFA-required roles: ADMIN + ANALYST
        ↓
Primary MFA: TOTP authenticator / QR scan
Required fallback: email OTP, risk-accepted as weaker
Recovery: backup codes + admin-only MFA reset
        ↓
Security events + notification outbox
        ↓
Resend email + Telegram operator alerts
        ↓
Turnstile only on risky abuse flows
```

---

## 1. Non-Negotiable Security Invariants

These are the rules Codex/Claude/any developer must not break.

```text
1. No public sign-up.
2. No final Auth.js session before MFA passes for MFA-required accounts.
3. TOTP is primary MFA.
4. Email OTP is a required fallback, but weaker and risk-accepted.
5. Backup codes are recovery, not convenience login.
6. Supabase service role key never reaches client code, logs, public docs, screenshots, or bundle output.
7. JWT role alone is never enough for authorization; protected routes re-check DB account state.
8. One-time secrets must be single-use through atomic DB updates.
9. Email/Telegram failure must not crash login or WAF ingest.
10. Every phase must have tests, stop conditions, and rollback notes.
```

---

## 2. Threat Model and Risk Acceptance

CyberTrace must explicitly defend against these attacks and failure modes.

| Threat / Failure | Defense | Required test/evidence |
|---|---|---|
| Stolen password | MFA challenge required before final session for ADMIN/ANALYST | Password-only ADMIN/ANALYST login creates no dashboard session |
| Stolen email inbox | Email OTP is fallback only, not equivalent to TOTP; admin email OTP use is high-severity | Email OTP use emits `security_events`; ADMIN email OTP queues operator alert |
| Replayed TOTP | Store and atomically update `last_used_time_step` | Same TOTP time-step cannot be accepted twice, including parallel attempts |
| Reused email OTP | HMAC/pepper-stored OTP, expiry, max attempts, atomic single-use update | Parallel email OTP verification: only one succeeds |
| Reused backup code | Hash-only storage, atomic consume | Parallel backup-code verification: only one succeeds |
| Leaked DB contents | Argon2id password hashes, encrypted TOTP secrets, HMAC OTP hashes, hashed backup/reset tokens | No plaintext password/OTP/token/backup/TOTP secret appears in DB/log tests |
| Leaked Supabase service key | Server-only module, no client import, CI secret scan, no `NEXT_PUBLIC` service key | Build/test/secret scan fails on exposure |
| Disabled/downgraded user with valid JWT | Protected routes check DB account state and `authz_version` | Old JWT denied after `disabled_at`, role change, or `authz_version` bump |
| Account enumeration | Generic public responses and timing-safe dummy path | Login/reset/MFA public responses do not reveal account existence/status |
| Notification provider failure | Transactional outbox, retry/backoff, max attempts, stuck-job recovery | Provider failure does not crash auth/WAF flow |
| Bot abuse | Throttling first; Turnstile only on risky flows/thresholds | Turnstile server validation enforced only when required |
| Supabase outage during defense | Documented degraded mode and pre-demo recovery plan | Runbook includes fallback explanation and emergency access plan |
| Resend outage/rate limit | TOTP and backup codes remain usable; email OTP send failure has safe UI | UI says email code cannot be sent right now, not account broken |
| Clock drift | Pre-demo clock/NTP check | Runbook includes clock check before TOTP demo |

### Email OTP Risk Acceptance

Email OTP is implemented because CyberTrace has a project/product requirement for an email-code fallback. It is not treated as equivalent to TOTP and is not claimed to be phishing-resistant or NIST-grade out-of-band MFA.

Email OTP is a controlled fallback only:

```text
- available only after password success;
- available only for verified account email;
- short-lived;
- single-use;
- HMAC/pepper-stored, never plaintext;
- rate-limited;
- resend-limited;
- audited;
- alert-worthy for ADMIN accounts;
- disableable during incident response.
```

TOTP remains the primary MFA method. Backup codes remain the preferred recovery method. Email OTP is accepted for project/client usability with known security tradeoffs.

---

## 3. Final Phase Order

The previous cutover order was risky because it moved account source-of-truth before Argon2id/provisioning were ready. Use this order instead.

| Phase | Name | Purpose |
|---:|---|---|
| 0 | Baseline branch and test proof | Prove repo is healthy before auth changes |
| 1A | Auth-security migration only | Create DB schema only; no runtime code |
| 1B | Server-only DB client | Add Supabase/Postgres server-only client + env validation |
| 1C | Schema boundary tests/docs | Prove no client exposure; update docs honestly |
| 2 | Argon2id module + benchmark | Add Argon2id-only hashing and benchmark, no login cutover |
| 3 | Account provisioning scripts | Create/list/disable/set-password/setup-link scripts using Argon2id |
| 4 | Supabase account source-of-truth cutover | Replace `AUTH_USERS_JSON` runtime login/guard after DB accounts exist |
| 5 | Email provider + outbox foundation | Resend provider and notification outbox dispatcher, no OTP dependency yet |
| 6 | TOTP enrollment | QR/manual setup, encrypted TOTP secret, backup-code generation |
| 7 | MFA login challenge | TOTP primary + email OTP fallback + backup code recovery; no session before success |
| 8 | Backup-code hardening + admin MFA reset | Recovery hardening and admin-only reset path |
| 9 | Password setup/reset | Setup links, forgot password, anti-enumeration, `authz_version` bump |
| 10 | Telegram operator alerts | High-risk auth and attack alerts through outbox |
| 11 | Turnstile risky-flow protection | Bot friction for reset/abuse thresholds only |
| 12 | Optional Admin user-management UI | Admin-only UI after scripts and core auth work |
| 13 | Final docs/runbooks/demo proof | Defense-ready docs, smoke tests, rollback/degraded-mode proof |

---

## 4. Current Repo Constraints to Preserve

The repo currently has Auth.js Credentials login, env-backed account registry, Argon2id password hashes, local login throttling, JSON audit logs, role claims, `authz_version`, and BFF route guards. Preserve the good parts while replacing the weak source-of-truth and hash storage.

Do not implement public sign-up. CyberTrace is a restricted security dashboard. Accounts are provisioned by an authorized admin/operator.

---

## 5. Supabase/Postgres Security Boundary

### Preferred schema approach

Use a private schema where practical:

```sql
create schema if not exists auth_security;
```

Tables should live under `auth_security.*` if the project can comfortably support that in Supabase tooling.

### If using public schema

If tables remain in `public`, lock them down:

```text
- enable RLS on all auth/security tables;
- do not create broad anon/authenticated policies;
- revoke broad anon/authenticated privileges where practical;
- test anon/authenticated keys cannot read auth tables;
- keep all access through server-only modules.
```

### Service-role truth

The service role key is not an authorization boundary. It is a privileged backend credential. RLS is defense-in-depth against future accidental exposure/misuse, but all current authorization must be enforced in server code and tests.

Required tests/checks:

```text
- no NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY exists;
- service key is never imported by client components;
- frontend build output does not contain service key;
- secret scan runs in CI;
- server-only DB module import from client fails or is lint/test blocked;
- anon/authenticated keys cannot read auth-security tables if Data API is exposed.
```

---

## 6. Database Schema

Create these tables in Phase 1A.

### 6.1 `auth_accounts`

```sql
create table if not exists auth_accounts (
  id uuid primary key default gen_random_uuid(),
  email text not null,
  username text,
  name text not null,
  role text not null check (role in ('ADMIN', 'ANALYST', 'VIEWER')),
  authz_version integer not null default 1 check (authz_version >= 1),
  password_hash text,
  password_set_at timestamptz,
  email_verified_at timestamptz,
  mfa_required boolean not null default false,
  disabled_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists auth_accounts_email_unique
  on auth_accounts (lower(email));

create unique index if not exists auth_accounts_username_unique
  on auth_accounts (lower(username))
  where username is not null;
```

Rules:

```text
ADMIN and ANALYST default mfa_required=true.
VIEWER defaults mfa_required=false unless explicitly enabled.
password_hash may be null only before password setup is completed.
disabled_at blocks login and protected access.
authz_version increments on role change, disable, password reset, MFA reset, and emergency recovery.
```

### 6.2 `auth_mfa_factors`

```sql
create table if not exists auth_mfa_factors (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references auth_accounts(id) on delete cascade,
  factor_type text not null check (factor_type in ('totp')),
  status text not null check (status in ('pending', 'verified', 'disabled')),
  secret_ciphertext text not null,
  secret_key_version integer not null default 1,
  last_used_time_step bigint,
  created_at timestamptz not null default now(),
  verified_at timestamptz,
  disabled_at timestamptz
);

create index if not exists idx_auth_mfa_factors_account
  on auth_mfa_factors (account_id);

create unique index if not exists idx_auth_mfa_one_verified_totp
  on auth_mfa_factors(account_id)
  where factor_type = 'totp' and status = 'verified';
```

Rules:

```text
TOTP secret is encrypted, not hashed, because the server needs the original secret to verify future codes.
Never log or return secret_ciphertext after enrollment display.
secret_key_version exists for future manual rotation planning.
```

### 6.3 `auth_mfa_challenges`

```sql
create table if not exists auth_mfa_challenges (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references auth_accounts(id) on delete cascade,
  challenge_hash text not null unique,
  status text not null default 'pending'
    check (status in ('pending', 'passed', 'expired', 'locked', 'cancelled')),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  max_attempts integer not null default 5 check (max_attempts > 0),
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz
);

create index if not exists idx_auth_mfa_challenges_account
  on auth_mfa_challenges (account_id, created_at desc);

create index if not exists idx_auth_mfa_challenges_active
  on auth_mfa_challenges (expires_at)
  where status = 'pending' and used_at is null;
```

Rules:

```text
Created only after password succeeds.
Does not grant dashboard access.
Must be rate-limited per account/identifier; attacker with stolen password cannot mint unlimited fresh challenges.
```

### 6.4 `auth_mfa_completion_tokens`

This table fixes the Auth.js handoff gap.

```sql
create table if not exists auth_mfa_completion_tokens (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references auth_accounts(id) on delete cascade,
  mfa_challenge_id uuid not null references auth_mfa_challenges(id) on delete cascade,
  token_hash text not null unique,
  status text not null default 'pending'
    check (status in ('pending', 'used', 'expired')),
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_auth_mfa_completion_tokens_account
  on auth_mfa_completion_tokens (account_id);

create index if not exists idx_auth_mfa_completion_tokens_active
  on auth_mfa_completion_tokens (expires_at)
  where status = 'pending' and used_at is null;
```

Rules:

```text
Random 32+ bytes.
Stored hashed only.
Expires in 60–120 seconds.
Created only after MFA challenge passes.
Consumed exactly once by Auth.js authorize before final session is returned.
```

### 6.5 `auth_email_otp_challenges`

```sql
create table if not exists auth_email_otp_challenges (
  id uuid primary key default gen_random_uuid(),
  mfa_challenge_id uuid not null references auth_mfa_challenges(id) on delete cascade,
  account_id uuid not null references auth_accounts(id) on delete cascade,
  email_to text not null,
  code_hash text not null,
  status text not null default 'pending'
    check (status in ('pending', 'used', 'expired', 'locked')),
  attempt_count integer not null default 0 check (attempt_count >= 0),
  max_attempts integer not null default 5 check (max_attempts > 0),
  resend_count integer not null default 0 check (resend_count >= 0),
  last_sent_at timestamptz,
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  used_at timestamptz
);

create index if not exists idx_auth_email_otp_challenges_mfa
  on auth_email_otp_challenges (mfa_challenge_id);

create index if not exists idx_auth_email_otp_challenges_active
  on auth_email_otp_challenges (expires_at)
  where status = 'pending' and used_at is null;
```

Rules:

```text
Email OTP only after password success and pending MFA challenge.
Email must be verified.
6 digits minimum.
Expires in 10 minutes or less.
Generating/resending a new code must not reset total failed attempt count.
Code stored as HMAC/pepper hash only.
ADMIN email OTP success emits high-severity event and operator alert.
```

### 6.6 `auth_backup_codes`

```sql
create table if not exists auth_backup_codes (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references auth_accounts(id) on delete cascade,
  code_hash text not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);

create index if not exists idx_auth_backup_codes_account
  on auth_backup_codes (account_id);

create index if not exists idx_auth_backup_codes_unused
  on auth_backup_codes (account_id)
  where used_at is null;
```

Rules:

```text
Generate 8–10 codes.
Display once.
Store hash only.
Use once.
Never log.
```

### 6.7 `auth_reset_tokens`

```sql
create table if not exists auth_reset_tokens (
  id uuid primary key default gen_random_uuid(),
  account_id uuid not null references auth_accounts(id) on delete cascade,
  purpose text not null check (purpose in ('password_setup', 'password_reset', 'mfa_reset')),
  token_hash text not null unique,
  status text not null default 'pending'
    check (status in ('pending', 'used', 'expired', 'revoked')),
  expires_at timestamptz not null,
  used_at timestamptz,
  created_at timestamptz not null default now()
);
```

### 6.8 `security_events`

```sql
create table if not exists security_events (
  id uuid primary key default gen_random_uuid(),
  source text not null check (source in ('auth', 'waf', 'ml', 'bff', 'system')),
  event_type text not null,
  severity text not null check (severity in ('low', 'medium', 'high', 'critical')),
  outcome text,
  action_taken text,
  account_id uuid references auth_accounts(id) on delete set null,
  transaction_id text,
  request_id text,
  route text,
  safe_summary_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);
```

### 6.9 `notification_outbox`

```sql
create table if not exists notification_outbox (
  id uuid primary key default gen_random_uuid(),
  event_id uuid references security_events(id) on delete set null,
  dedupe_key text,
  channel text not null check (channel in ('email', 'telegram')),
  recipient text not null,
  status text not null default 'pending'
    check (status in ('pending', 'sending', 'sent', 'failed', 'skipped')),
  attempts integer not null default 0 check (attempts >= 0),
  max_attempts integer not null default 5 check (max_attempts > 0),
  next_attempt_at timestamptz not null default now(),
  payload_safe_json jsonb not null default '{}'::jsonb,
  last_error_code text,
  locked_at timestamptz,
  locked_by text,
  created_at timestamptz not null default now(),
  sent_at timestamptz
);

create unique index if not exists idx_notification_outbox_dedupe
  on notification_outbox (dedupe_key)
  where dedupe_key is not null;

create index if not exists idx_notification_outbox_pending
  on notification_outbox (status, next_attempt_at, created_at)
  where status = 'pending';
```

---

## 7. Atomic Verification Rules

All one-time secrets must be consumed with database-enforced atomic updates. Do not implement read-then-write verification.

### 7.1 TOTP replay prevention

After app-layer TOTP verification calculates the accepted time step:

```sql
update auth_mfa_factors
set last_used_time_step = :current_time_step
where id = :factor_id
  and status = 'verified'
  and (
    last_used_time_step is null
    or last_used_time_step < :current_time_step
  )
returning id;
```

### 7.2 Email OTP consume

```sql
update auth_email_otp_challenges
set status = 'used',
    used_at = now()
where id = :email_otp_challenge_id
  and status = 'pending'
  and used_at is null
  and expires_at > now()
  and code_hash = :submitted_code_hash
returning id;
```

### 7.3 Email OTP failed attempt

```sql
update auth_email_otp_challenges
set attempt_count = attempt_count + 1,
    status = case
      when attempt_count + 1 >= max_attempts then 'locked'
      else status
    end
where id = :email_otp_challenge_id
  and status = 'pending'
  and used_at is null
returning attempt_count, status;
```

### 7.4 Backup code consume

```sql
update auth_backup_codes
set used_at = now()
where account_id = :account_id
  and code_hash = :submitted_code_hash
  and used_at is null
returning id;
```

### 7.5 MFA challenge pass

```sql
update auth_mfa_challenges
set status = 'passed',
    used_at = now()
where id = :challenge_id
  and status = 'pending'
  and used_at is null
  and expires_at > now()
returning id;
```

### 7.6 MFA completion token consume

```sql
update auth_mfa_completion_tokens
set status = 'used',
    used_at = now()
where token_hash = :token_hash
  and status = 'pending'
  and used_at is null
  and expires_at > now()
returning account_id, mfa_challenge_id;
```

### Required race tests

```text
parallel email OTP verify: only one succeeds;
parallel backup code verify: only one succeeds;
parallel TOTP verify in same time-step: only one succeeds;
parallel completion-token consume: only one final session succeeds;
failed OTP increments attempt count;
locked OTP cannot later be used;
expired challenge cannot be passed;
passed challenge cannot be reused.
```

---

## 8. Auth.js MFA Flow

### 8.1 Login password step

```text
User enters identifier + password.
Server checks login throttle.
Server loads account from Supabase.
Server verifies Argon2id password.
If account disabled: generic failure.
If no MFA required: Auth.js returns final user session.
If MFA required: create pending auth_mfa_challenges row and pending cookie only.
No final Auth.js session exists yet.
```

### 8.2 MFA challenge methods

The MFA challenge UI must show:

```text
Primary: Authenticator app code
Clickable fallback: Use email code instead
Recovery: Use backup code
```

### 8.3 Final session handoff

To avoid manually minting sessions, use Auth.js Credentials with a `step` or separate provider ID:

```text
step=password
step=mfa_complete
```

After TOTP/email OTP/backup code succeeds:

```text
1. Mark MFA challenge passed atomically.
2. Create auth_mfa_completion_tokens row.
3. Server action calls signIn('credentials', { step: 'mfa_complete', completionToken }).
4. Auth.js authorize atomically consumes completion token.
5. Auth.js returns final user object.
6. JWT/session callback stores id, role, authz_version.
```

### 8.4 Session Freshness Rule

Every protected server-side route, BFF route, Server Action, and dashboard data access path must verify current DB account state before returning sensitive data.

Required checks:

```text
account exists;
disabled_at is null;
role still matches required permission;
session.authz_version equals auth_accounts.authz_version;
account identity still maps to the same account id.
```

Never trust JWT role alone for authorization.

Required tests:

```text
disabled account with valid JWT is denied;
role-downgraded account with valid JWT is denied;
authz_version mismatch denies access;
deleted account id denies access;
VIEWER cannot call analyst/admin routes;
ANALYST cannot call admin-only routes;
all protected paths use central route guard.
```

---

## 9. CSRF, Cookies, and Request-Origin Rules

All state-changing auth routes/actions must:

```text
reject non-POST state-changing requests;
validate Origin/Host where applicable;
use HttpOnly cookies for pending MFA challenge;
use Secure cookies outside local development;
use SameSite=Lax or Strict cookies;
never accept challenge token from URL query string;
never store final-session data inside pending MFA cookie;
expire pending MFA cookie when challenge passes, expires, is cancelled, or is locked.
```

Implementation decision:

```text
Prefer Next.js Server Actions for login/MFA form submissions where practical because they are POST-only and have built-in origin checks. If Route Handlers are used, implement explicit Origin/Host validation.
```

Tests:

```text
GET cannot trigger OTP send;
cross-origin POST to email OTP resend is rejected;
tampered pending MFA cookie is rejected;
expired pending MFA cookie is rejected;
final dashboard session is absent during pending MFA;
pending cookie cleared after MFA success.
```

---

## 10. Account Provisioning and Role Assignment

No public sign-up.

Initial project-grade implementation uses scripts:

```text
frontend/scripts/create_auth_account.mjs
frontend/scripts/list_auth_accounts.mjs
frontend/scripts/disable_auth_account.mjs
frontend/scripts/set_auth_account_password.mjs
frontend/scripts/create_password_setup_link.mjs
```

Rules:

```text
ADMIN/ANALYST default mfa_required=true.
VIEWER default mfa_required=false.
Panelists should get VIEWER.
Client reviewer gets VIEWER or ANALYST depending on demo.
Client system owner can get ADMIN if needed.
Temporary password accepted only through secure operator channel.
Password setup link preferred once email/outbox exists.
No password hash, DB URL, service key, reset token, or setup token is printed.
```

Cutover precondition:

```text
Do not replace AUTH_USERS_JSON runtime login until:
- at least one ADMIN account exists in auth_accounts;
- ADMIN password hash is Argon2id;
- ADMIN login is smoke-tested;
- emergency disable/reset scripts work;
- rollback instructions are written;
- old scrypt hashes are not required for runtime login.
```

---

## 11. Argon2id Password Hashing

Use `argon2` npm package.

Default parameters:

```dotenv
AUTH_ARGON2_MEMORY_COST_KIB=19456
AUTH_ARGON2_TIME_COST=2
AUTH_ARGON2_PARALLELISM=1
AUTH_PASSWORD_HASH_CONCURRENCY_LIMIT=2
```

Rules:

```text
Argon2id only.
No legacy scrypt support.
Old scrypt hashes rejected.
Dummy hash must be Argon2id.
Benchmark before runtime cutover.
```

Benchmark requirement:

```powershell
cd frontend
node scripts/benchmark_argon2id.mjs
```

Record:

```text
memoryCost, timeCost, parallelism;
p50 verify time;
p95 verify time;
concurrency limit behavior;
unknown-account dummy path timing shape.
```

---

## 12. Notification Outbox Dispatcher

### 12.1 Worker claim query

```sql
with next_jobs as (
  select id
  from notification_outbox
  where status = 'pending'
    and next_attempt_at <= now()
  order by created_at
  limit :limit
  for update skip locked
)
update notification_outbox n
set status = 'sending',
    locked_at = now(),
    locked_by = :worker_id,
    attempts = attempts + 1
from next_jobs
where n.id = next_jobs.id
returning n.*;
```

### 12.2 Dispatch rules

```text
Provider send success -> mark sent, set sent_at.
Provider failure -> status pending or failed depending attempts.
Use exponential backoff: 1m, 5m, 15m, 1h, 6h.
Stuck sending older than timeout -> reset to pending or mark failed.
Use dedupe_key for repeated system-generated messages.
Use provider idempotency key where supported; for Resend use outbox.id or event_id-derived key where supported by SDK/API.
```

### 12.3 Tests

```text
two dispatcher workers do not claim same row;
provider sends but DB update fails -> retry is duplicate-safe;
dedupe_key prevents duplicate MFA enabled email;
failed provider increments attempts;
max attempts marks failed;
old sending job is recovered;
email/Telegram failure does not crash auth flow.
```

---

## 13. Email OTP UI/UX Requirements

MFA page structure:

```text
Title: Verify your sign-in
Default tab/section: Authenticator app
Fallback link/button: Use email code instead
Recovery link/button: Use backup code
Masked destination: Send code to f***@example.com
```

Email OTP UI rules:

```text
single input field, not six inaccessible boxes;
inputmode=numeric;
autocomplete=one-time-code;
visible label, not placeholder-only label;
paste full code works;
resend countdown visible and screen-reader readable;
aria-live region for status/errors;
generic failures: Invalid or expired code;
do not reveal whether account exists;
do not display raw email for unknown/failed states;
email send failure says: Email code could not be sent right now. Use authenticator or backup code.
```

Accessibility acceptance:

```text
keyboard-only login works;
keyboard-only MFA works;
paste OTP works;
screen-reader status messages work;
resend countdown readable;
backup codes copy/download/print path exists;
error messages are not color-only.
```

---

## 14. MFA Reset Policy

MFA reset is admin-only for MVP. Do not build self-service email-only MFA reset yet.

Admin MFA reset must:

```text
require ADMIN role;
prefer recent re-auth if available;
increment authz_version;
disable existing verified TOTP factors;
invalidate active MFA challenges;
invalidate active sessions through authz_version;
record high-severity security_event;
send notification to account email;
send Telegram/operator alert if target is ADMIN;
never expose old TOTP secret or backup codes.
```

Tests:

```text
VIEWER cannot reset MFA;
ANALYST cannot reset MFA;
ADMIN can reset MFA;
MFA reset increments authz_version;
old session after MFA reset is denied;
MFA reset emits security_event.
```

---

## 15. Password Setup and Password Reset

Public response is always:

```text
If an account can use password reset, we sent instructions.
```

Same response for:

```text
existing account;
non-existing account;
disabled account;
account without verified email;
provider failure.
```

Implementation:

```text
generate random 32+ byte token;
store hash only;
expire in 15–30 minutes for reset;
single-use atomic consume;
Argon2id new password hash;
authz_version increment;
no auto-login after reset;
queue password-changed email.
```

---

## 16. Observability and Alert Conditions

Security event counters:

```text
auth.login.failed
auth.login.succeeded
auth.login.disabled_account_attempt
auth.mfa.challenge.created
auth.mfa.challenge.expired
auth.mfa.totp.failed
auth.mfa.totp.replay_rejected
auth.mfa.email_otp.sent
auth.mfa.email_otp.resend_blocked
auth.mfa.email_otp.used
auth.mfa.backup_code.used
auth.password_reset.requested
auth.password_reset.completed
notification.outbox.pending
notification.outbox.failed
notification.provider.failure
```

High/critical alert-worthy conditions:

```text
ADMIN email OTP fallback used;
ADMIN backup code used;
ADMIN MFA locked;
repeated failures for same account;
repeated failures from same IP/source hash;
service-role/env config invalid;
notification provider repeated failure;
outbox backlog above threshold;
disabled account access attempt.
```

Project-grade UI option:

```text
Add an admin-only security events table later, or at minimum document SQL queries/runbook commands for inspecting security_events and notification_outbox during demo.
```

---

## 17. Degraded Mode and Demo Runbook

### Supabase unreachable

```text
Login cannot proceed because Supabase auth_accounts is the account source of truth.
User-facing error: Unable to sign in right now.
Operator action: verify DATABASE_URL/SUPABASE env, Supabase status, network, and fallback emergency account recovery.
Accepted capstone risk: no offline AUTH_USERS_JSON fallback after clean cutover.
```

### Resend unreachable / rate limited

```text
TOTP and backup codes still work.
Email OTP fallback cannot send new codes.
User-facing error: Email code could not be sent right now. Use authenticator app or backup code.
Operator action: check Resend status/API key/domain/quota; use backup code for demo if needed.
```

### Telegram unreachable

```text
Auth/login should not fail.
Notification outbox records failure and retries.
Operator can inspect notification_outbox.
```

### Clock drift

```text
Before defense/demo, verify server time and timezone.
TOTP depends on server time; clock drift can break valid authenticator codes.
```

Pre-demo checklist:

```text
ADMIN login works.
ANALYST login works.
VIEWER login works.
TOTP works.
Email OTP sends at least once.
Backup code works and is available.
Password reset setup link works if demoed.
Outbox dispatcher can run.
Server clock correct.
No secrets printed in logs.
```

---

## 18. CI and Secret Scanning

Add lightweight GitHub Actions before merging auth cutover.

Minimum workflow:

```text
frontend lint
frontend typecheck
frontend vitest
frontend build
backend pytest
npm audit --audit-level=high or Dependabot alerts
secret scan with gitleaks/trufflehog or equivalent
```

This is project-grade, not enterprise overkill, because auth/security code written with AI agents needs automatic guardrails.

---

## 19. Secret Versioning and Rotation

Environment variables:

```dotenv
AUTH_TOTP_ENCRYPTION_KEY_BASE64=<32-byte-base64>
AUTH_OTP_PEPPER_BASE64=<32-byte-base64>
```

Rules:

```text
support current key version only for MVP;
store secret_key_version on TOTP factors;
document key owner, environment, creation date;
never commit secrets;
never print secrets;
rotation is manual runbook, not automated KMS.
```

If `AUTH_OTP_PEPPER_BASE64` rotates, outstanding email OTPs become invalid. That is acceptable; they are short-lived.

If `AUTH_TOTP_ENCRYPTION_KEY_BASE64` rotates, existing TOTP secrets require a migration/re-enrollment plan. For MVP, document manual re-enrollment.

---

## 20. Rollback and Emergency Lockout Recovery

Before cutover:

```text
export current AUTH_USERS_JSON securely;
create at least one Argon2id ADMIN account in auth_accounts;
verify ADMIN login locally/staging;
verify disable/reset scripts;
backup auth-security tables;
document emergency account creation command.
```

Rollback path:

```text
revert auth source-of-truth code;
restore AUTH_USERS_JSON env if needed;
keep new auth tables intact unless data corruption occurred;
do not drop auth tables during emergency rollback;
document which migrations are reversible and which are forward-only.
```

Emergency lockout recovery:

```text
run create_auth_account.mjs for new ADMIN;
or run set_auth_account_password.mjs for existing ADMIN;
increment authz_version;
log manual recovery in security_events.
```

---

## 21. Phase Details

### Phase 0 — Baseline branch and test proof

Commands:

```powershell
git status --short
git checkout -b feat/auth-hardening-clean-cutover
cd frontend
npm run lint
npm run typecheck
npx vitest run --pool=threads
npm run build
cd ..
.venv\Scripts\python.exe -m pytest -q
```

Done when tests pass before changes.

### Phase 1A — Auth-security migration only

Allowed:

```text
supabase/migrations/* or migrations/* depending repo convention
docs note listing tables only
```

Forbidden:

```text
no auth.ts
no login changes
no Supabase client
no UI
no email
no MFA logic
```

Done when migration creates all tables and indexes.

### Phase 1B — Server-only DB client

Allowed:

```text
frontend/lib/server/db/*
frontend/lib/server/db/*.test.ts
```

Requirements:

```text
import 'server-only';
validate SUPABASE_URL and server secret key;
no NEXT_PUBLIC service key;
no client import path.
```

### Phase 1C — Schema boundary tests/docs

Requirements:

```text
server-only boundary tests;
service key not exposed;
docs updated honestly;
tracker says schema exists, login not migrated.
```

### Phase 2 — Argon2id module and benchmark

Allowed:

```text
frontend/lib/auth/password-hash.ts
frontend/lib/auth/password-hash.test.ts
frontend/lib/auth/login-throttle.ts
frontend/lib/auth/login-throttle.test.ts
frontend/scripts/generate_auth_password_hash.mjs
frontend/scripts/benchmark_argon2id.mjs
```

No login cutover yet.

### Phase 3 — Account provisioning scripts

Scripts:

```text
create_auth_account.mjs
list_auth_accounts.mjs
disable_auth_account.mjs
set_auth_account_password.mjs
create_password_setup_link.mjs
```

Done when accounts can be seeded with Argon2id and at least one ADMIN exists.

### Phase 4 — Supabase account source-of-truth cutover

Replace runtime use of `AUTH_USERS_JSON` with Supabase account lookup.

Must preserve:

```text
Auth.js Credentials
JWT session strategy
authz_version invalidation
role checks
BFF route guard behavior
generic errors
throttling
safe audit logs
```

Done when login/guard use DB and old env registry is no longer runtime source.

### Phase 5 — Email provider and outbox foundation

Add Resend provider, safe templates, outbox insert/claim/update logic. No OTP dependency yet.

### Phase 6 — TOTP enrollment

Add QR/manual setup, encrypted secret, verification, backup code generation.

### Phase 7 — MFA login challenge

Add TOTP primary, email OTP fallback, backup-code recovery, completion-token Auth.js handoff.

### Phase 8 — Backup-code hardening and admin MFA reset

Add full recovery rules and admin-only MFA reset.

### Phase 9 — Password setup/reset

Add setup links and forgot-password flow with anti-enumeration.

### Phase 10 — Telegram alerts

Send only safe high-risk operator alerts through outbox.

### Phase 11 — Turnstile

Server-validate Turnstile only for reset/abuse thresholds.

### Phase 12 — Optional Admin UI

Admin-only user management UI after scripts are proven. Not required before core MFA.

### Phase 13 — Final docs/runbooks/demo proof

Update SETUP, architecture, client requirements, current state, status, checklist, tracker, ADR, MFA recovery runbook, notification runbook, screenshots/proof.

---

## 22. What Not to Build Yet

```text
public sign-up
self-service access request
Supabase Auth migration
WebAuthn/passkeys
SMS OTP
Telegram OTP
trusted devices / remember browser
Redis/distributed throttling
Kafka/Celery/Elasticsearch
Wazuh full SIEM
Kubernetes/Helm/Terraform
full enterprise IAM
```

---

## 23. AI Agent Prompt Rules

Every phase prompt must include:

```text
ROLE
TASK
STRICT SCOPE
FILES TO INSPECT
FILES ALLOWED TO CHANGE
FORBIDDEN CHANGES
IMPLEMENTATION STEPS
TESTS
STOP CONDITIONS
DONE CRITERIA
OUTPUT FORMAT
```

Split large phases into smaller prompts. Especially:

```text
Phase 1A migration only
Phase 1B server-only DB client
Phase 1C tests/docs
```

Stop conditions:

```text
needs broad rewrite;
needs unrelated file changes;
service key may enter client;
auth behavior changes outside phase;
tests require deleting/weakened assertions;
secrets appear in output/logs;
provider integration requires real tokens in tests.
```

---

## 24. Revised First Codex Prompt

```text
ROLE:
Act as a senior security-focused Next.js/Auth.js/Postgres engineer working on CyberTrace.

TASK:
Implement Phase 1A only: Supabase/Postgres auth-security migration.

STRICT SCOPE:
Create the database migration only. Do not change runtime login behavior.

ALLOWED FILES:
- supabase/migrations/* OR migrations/* depending existing repo convention
- docs/project-ops/STATUS.md only to note migration file was added, if required by repo practice

FORBIDDEN:
- Do not edit frontend/auth.ts.
- Do not edit password-hash.ts.
- Do not add Supabase client code.
- Do not add email/Telegram/Turnstile.
- Do not add MFA UI/routes.
- Do not remove AUTH_USERS_JSON runtime behavior.

CREATE TABLES:
- auth_accounts
- auth_mfa_factors
- auth_mfa_challenges
- auth_mfa_completion_tokens
- auth_email_otp_challenges
- auth_backup_codes
- auth_reset_tokens
- security_events
- notification_outbox

REQUIREMENTS:
- Include indexes described in the plan.
- Include lower(email)/lower(username) unique indexes.
- Include dedupe_key, locked_at, locked_by in notification_outbox.
- Include secret_key_version in auth_mfa_factors.
- Enable RLS if tables are in public schema, but document RLS as defense-in-depth only.
- Do not create broad anon/authenticated policies.

TESTS/VALIDATION:
- Do not run destructive production migration automatically.
- If local migration tooling exists, run local migration validation only.
- Otherwise report manual SQL validation instructions.

STOP CONDITIONS:
- Existing migration convention is unclear.
- Migration requires destructive changes to existing app tables.
- Any secret value is needed or printed.
- Any runtime auth file needs editing.

OUTPUT FORMAT:
- Summary
- Files changed
- Tables created
- Indexes created
- RLS/grants note
- Validation run
- Stop conditions
- Next recommended PR
```

---

## 25. Research Source Map

Use these sources in the implementation-plan documentation and defense notes.

1. OWASP Password Storage Cheat Sheet — Argon2id parameters, work factors, peppers.  
   https://cheatsheetseries.owasp.org/cheatsheets/Password_Storage_Cheat_Sheet.html
2. RFC 9106 — Argon2 specification.  
   https://datatracker.ietf.org/doc/html/rfc9106
3. NIST SP 800-63B — OTP, out-of-band auth, email prohibition, replay resistance, rate limiting.  
   https://pages.nist.gov/800-63-4/sp800-63b.html
4. RFC 6238 — TOTP standard.  
   https://datatracker.ietf.org/doc/html/rfc6238
5. RFC 4226 — HOTP standard and OTP throttling background.  
   https://datatracker.ietf.org/doc/html/rfc4226
6. OWASP MFA Cheat Sheet — MFA reset/recovery risks.  
   https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html
7. OWASP Authentication Cheat Sheet — generic auth responses and auth hardening.  
   https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
8. OWASP Authorization Cheat Sheet — least privilege and request-level authz.  
   https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
9. OWASP Forgot Password Cheat Sheet — reset token flow.  
   https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html
10. OWASP CSRF Cheat Sheet — state-changing request protection.  
    https://cheatsheetseries.owasp.org/cheatsheets/Cross-Site_Request_Forgery_Prevention_Cheat_Sheet.html
11. OWASP Logging Cheat Sheet — safe security logging.  
    https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
12. OWASP Secrets Management Cheat Sheet — secret handling and rotation.  
    https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
13. Auth.js Credentials docs — custom credential flow responsibility.  
    https://authjs.dev/getting-started/authentication/credentials
14. Auth.js Session Strategies — JWT/session tradeoffs.  
    https://authjs.dev/concepts/session-strategies
15. Next.js Authentication guide — auth/session/authorization split.  
    https://nextjs.org/docs/app/guides/authentication
16. Supabase API Keys — secret keys, service role, bypass RLS, handling rules.  
    https://supabase.com/docs/guides/getting-started/api-keys
17. Supabase RLS docs — RLS and exposed table policies.  
    https://supabase.com/docs/guides/database/postgres/row-level-security
18. Supabase Securing API docs — exposed schemas/grants/Data API.  
    https://supabase.com/docs/guides/api/securing-your-api
19. PostgreSQL SELECT docs — `FOR UPDATE SKIP LOCKED`.  
    https://www.postgresql.org/docs/current/sql-select.html
20. PostgreSQL transaction isolation docs — race-condition context.  
    https://www.postgresql.org/docs/current/transaction-iso.html
21. Transactional Outbox pattern — safe DB + notification dispatch.  
    https://microservices.io/patterns/data/transactional-outbox.html
22. Resend Next.js docs — email provider integration.  
    https://resend.com/docs/send-with-nextjs
23. Telegram Bot API — operator alerts.  
    https://core.telegram.org/bots/api
24. Cloudflare Turnstile server validation — tokens expire and must be validated server-side.  
    https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
25. WCAG 2.2 Accessible Authentication — auth UI accessibility.  
    https://www.w3.org/WAI/WCAG22/Understanding/accessible-authentication-minimum.html
26. NIST SSDF SP 800-218 — security integrated in SDLC.  
    https://csrc.nist.gov/publications/detail/sp/800-218/final
27. Google Engineering Practices Code Review — small reviewable changes.  
    https://google.github.io/eng-practices/review/
28. Abseil Software Engineering at Google — code review and sustainable practices.  
    https://abseil.io/resources/swe-book/html/ch09.html
29. OWASP Secure Coding with AI Cheat Sheet — AI agent guardrails.  
    https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html
30. OWASP AI Agent Security Cheat Sheet — least privilege, validation, monitoring.  
    https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html

---

## 26. Final Implementation Verdict

This revised plan accepts the useful Codex/Claude findings without turning CyberTrace into an enterprise IAM project. The main upgrades are database atomicity, session freshness, service-role containment, outbox idempotency, email OTP risk acceptance, degraded-mode planning, and AI-agent-sized implementation phases.

This is the right level for CyberTrace:

```text
Strong enough to defend.
Strict enough to avoid fake MFA.
Small enough to implement.
Not bloated with enterprise infrastructure.
```
