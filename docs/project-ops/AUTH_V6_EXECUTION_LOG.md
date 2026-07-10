# CyberTrace Auth V6.1 Execution Log

Status labels: `Implemented`, `Partial`, `Blocked`, `Planned`, `Deferred`.

## Run State

- Repository: `G:\AI\PDDDD\injection-alert-system`
- Branch: `feat/cybertrace-v6-1`
- Base commit: `12c5708b2e7755bece7764a0e3ff566b9fcad3cf`
- Latest accepted commit: `ede2a53` (Unit 3)
- Current unit: Unit 2 — ADMIN User Management and account setup
- Current bounded objective: implement server-authorized account listing/creation/setup, role/status management, and verified managed-email transitions.
- Next exact action: begin Unit 4 pre-auth challenge, normal TOTP login, and Auth.js completion handoff.

## Unit 2 Contract

- Status: `Implemented`
- In scope: ADMIN-only navigation/page/APIs, safe account list, account creation without ADMIN-chosen passwords, one-time setup link, role-derived MFA policy, setup completion, role change, disable/re-enable, managed-email verification, and authorization-negative tests.
- Out of scope: usable ADMIN MFA sessions (Unit 4), TOTP enrollment (Unit 3), MFA reset (Unit 6), recovery, Turnstile, and public deployment.
- Locked invariants: all mutations require a fresh server-side account reload plus ADMIN/TOTP/recent-auth claims; until Unit 4 can issue those claims, mutations fail closed; tokens are generated/digested server-side, URLs use trusted configured origin, GET never consumes a token, and ADMIN never supplies or sees another user's password.
- Primary change kind: `new feature slice`.
- Secondary change kinds: additive contract change and boundary extraction.
- Scope: one additive migration, narrow account-management RPCs, local Next.js server modules/routes, local account-management feature UI, safe headers, and focused tests.
- Extraction outcome: `boundary` for account-management orchestration; `local module` for token/password policy and Supabase RPC adapters.
- Contract surfaces: additive account/reset fields and explicit RPCs; new BFF routes/pages; additive permission and session-claim reads; no existing alert/FastAPI response changes.
- Materialization: page is a route-level `container`; the User Management workspace is a local interactive component boundary; DB adapter and token handling remain server-only infrastructure boundaries.
- Convention decision: preserve existing App Router, Zod route validation, server-only Supabase client, semantic surface tokens, and thin route handlers.
- Validation depth: guard/route/component unit tests, migration source and disposable-PostgreSQL transition tests, Node 24 lint/typecheck/Vitest/build, and affected backend migration suite.
- Escalation: none; Unit 4 is an explicit dependency for reachable successful ADMIN mutations, and Unit 2 remains securely fail-closed until then.
- Visual thesis: a calm graphite-and-amber SOC administration workspace with dense readable rows and minimal chrome.
- Content plan: concise page orientation, account-creation control, safe account table, and contextual row actions/status.
- Interaction thesis: restrained entry reveal, clear pending/success feedback, and compact row action transitions; no ornamental dashboard-card grid.

## Unit 3 Contract

- Status: `Implemented`
- In scope: additive TOTP factor corrections, AES-256-GCM secret encryption, RFC 6238 generation/verification with a three-step window and atomic replay protection, pending enrollment/activation, eight one-time Argon2id backup codes, display-once enrollment UI, and safe security/notification transitions.
- Out of scope: normal password-plus-TOTP login handoff (Unit 4), recovery email OTP and backup-code recovery (Unit 5), password recovery and ADMIN MFA reset (Unit 6), Turnstile, deployment, and live provider execution.
- Locked invariants: no plaintext TOTP secret or backup-code hash leaves trusted server code; pending factors expire after ten minutes; only one active factor exists per account; accepted time steps are monotonic and atomically consumed; backup codes are generated with cryptographic randomness, hashed, shown once, and never retrievable by ADMIN; Unit 4 claims remain the only path to a reachable final MFA session.
- Primary change kind: `new feature slice`.
- Secondary change kinds: additive schema correction and boundary extraction.
- Scope: one additive migration, server-only crypto/TOTP/backup modules, narrow Supabase RPC adapters, enrollment route/UI, and focused tests.
- Extraction outcome: `boundary` for MFA crypto and enrollment orchestration; `local module` for backup-code formatting and server-only database adapters.
- Contract surfaces: additive factor/backup-code fields and explicit RPCs; new enrollment route/component; no FastAPI or alert contract changes.
- Materialization: enrollment page is a route-level `container`; the setup form is a local interactive component; crypto and persistence remain server-only infrastructure boundaries.
- Convention decision: preserve App Router, Zod, server-only Supabase, Auth.js session claims, and thin route handlers; use Node built-in crypto and existing Argon2id support.
- Validation depth: crypto/TOTP/backup unit tests, migration source and disposable-PostgreSQL concurrency tests, Node 24 lint/typecheck/Vitest/build, and affected backend migration suite.
- Escalation: none; normal login and final MFA session creation remain explicitly deferred to Unit 4.

## Unit 1 Contract

- Status: `Implemented`
- In scope: `EmailProvider`, fake provider, Resend HTTP adapter, safe versioned templates, outbox claim/complete/fail RPCs, one logical Python worker, deterministic retry policy, safe configuration, and fake/mocked/live-guard tests.
- Out of scope: account setup/recovery route wiring (Units 2/5/6), MFA behavior, Turnstile, public deployment, and live provider execution unless the locked opt-in environment gate is already satisfied.
- Locked invariants: handlers enqueue only; Resend is called only by the worker/smoke boundary; durable dedupe remains in PostgreSQL; provider retries preserve payload and idempotency key; errors never expose secrets or arbitrary provider text; WAF/auth request paths do not depend on provider availability.
- Primary change kind: `new feature slice`.
- Secondary change kind: `boundary extraction` for the provider and outbox worker seams.
- Scope: backend notification package, central settings, one additive migration, focused tests, environment placeholders, and worker lifecycle wiring only where proven necessary.
- Extraction outcome: `boundary` for notifications, with local modules for provider, templates, repository, and worker.
- Contract surfaces: additive database columns/functions, settings fields, and worker entrypoint; existing BFF/FastAPI response shapes remain unchanged.
- Materialization: Python owns delivery because it already owns WAF ingest and the long-running backend lifecycle; frontend/auth code will later enqueue through narrow Supabase operations.
- Convention decision: async interfaces, Pydantic central settings, SQLAlchemy sessions, thin startup wiring, and narrow fully qualified PostgreSQL functions.
- Validation depth: unit/provider contract tests, migration source checks, worker behavior tests, affected backend suite, disposable PostgreSQL migration/RPC checks when a non-production target is confirmed.
- Escalation: no product decision is unresolved; schema application stops if a target cannot be proven disposable.

## Unit 0 Contract

- Status: `Implemented`
- In scope: read-only ownership/schema/deployment discovery plus this factual audit log.
- Out of scope: feature code, migration changes, live database mutation, live provider calls, and configuration cleanup.
- Locked invariants: Auth.js remains the session framework; `auth_accounts` remains the account source; service-role access stays server-only; Browser -> Next.js BFF -> FastAPI remains intact; no weaker fallback is introduced.
- Primary change kind: `new feature slice` (discovery gate for the approved V6.1 slice).
- Secondary change kinds: none for Unit 0.
- Scope: documentation evidence only.
- Extraction outcome: `inline`.
- Contract surfaces: observed only; no contract changed.
- Convention decision: preserve the current Next.js server-only Supabase repository and thin BFF route pattern.
- Validation depth: focused frontend auth/BFF tests plus backend migration/startup tests.
- Escalation: none; repository ownership is compatible with the locked plan.

## Verified Repository Discoveries

### Authentication and session flow

- `frontend/auth.ts` configures the Node-runtime Auth.js Credentials provider. `authorize()` normalizes credentials, checks `loginThrottle`, calls `findAuthAccountByIdentifier()`, and verifies Argon2id with `verifyPasswordForAccount()` behind `passwordHashConcurrencyGate`.
- `frontend/lib/auth/password-hash.ts` owns approved Argon2id PHC validation, hashing, real-account verification, and the matching dummy-hash path.
- `frontend/lib/server/db/auth-accounts.ts` owns login and request-time freshness queries for `auth_accounts`; it validates returned rows with Zod.
- `frontend/lib/server/db/client.ts` creates a non-persistent server-only Supabase client. `frontend/lib/server/db/env.ts` requires `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` and rejects `NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY`.
- `frontend/auth.ts` `jwt()` stores account id, role, and `authz_version`; `session()` exposes those validated claims. Current claims do not yet include `auth_level`, `auth_method`, or `auth_time`.
- `frontend/lib/auth/route-guard.ts` `requirePermission()` reloads the current account for each protected BFF request and rejects missing, disabled, MFA-required, stale-version, role-mismatched, or unauthorized accounts.
- `frontend/app/(dashboard)/layout.tsx` also requires a fresh authorized account before rendering the dashboard. `frontend/proxy.ts` provides an edge Auth.js check and shared response headers, but final authorization remains in server routes/layout.
- `frontend/app/api/auth/[...nextauth]/route.ts` exposes the Auth.js GET/POST handlers. `frontend/app/(auth)/login/actions.ts` invokes Credentials sign-in and currently redirects successful sessions to `/dashboard`.

Current verified sequence:

```text
Browser login form
-> Next.js server action
-> Auth.js Credentials authorize()
-> server-only Supabase auth_accounts lookup
-> Argon2id verification
-> Auth.js JWT/session callbacks
-> dashboard/BFF requirePermission() fresh account reload
-> Next.js BFF permission check
-> FastAPI internal bearer-authenticated application API
```

FastAPI does not create, update, or validate application-user sessions. `web_app/presentation/dependencies/auth.py` validates only the shared internal bearer credential. `web_app/presentation/api/routes.py` and `triage_router.py` apply that dependency to internal application APIs.

### Authorization boundaries

- `frontend/lib/auth/roles.ts` is the current role-permission matrix.
- The alert list/detail, triage, action, stats, and ML-health route handlers call `auth()` and await `requirePermission()` before downstream FastAPI work.
- The BFF is the application-user authorization boundary. FastAPI is an internal application boundary protected by `API_SECRET_KEY`; it does not trust browser role claims because the browser never calls it directly.
- Current `mfa_required=true` behavior is fail-closed at both login and BFF freshness checks. No MFA completion path exists yet.

### Existing schema and scripts

- `migrations/versions/20260704_000008_add_auth_security_foundation.py` creates `auth_accounts`, `auth_mfa_factors`, `auth_mfa_challenges`, `auth_mfa_completion_tokens`, `auth_email_otp_challenges`, `auth_backup_codes`, `auth_reset_tokens`, `security_events`, and `notification_outbox`.
- The migration enables RLS and revokes `PUBLIC`, `anon`, and `authenticated` access. It defines no browser policies and no security-transition RPCs; the only function is the `auth_accounts.updated_at` trigger function.
- Existing schema differs from V6.1: factor states are `pending/verified/disabled`; factor nonce, pending expiry, activation/revocation timestamps are absent; backup codes have no revocation marker or lookup prefix; reset purposes/states differ; security events lack actor/target/auth-method schema fields; outbox states/lease/provider fields are incomplete for the approved worker contract.
- `frontend/scripts/create_auth_account.mjs`, `list_auth_accounts.mjs`, `disable_auth_account.mjs`, and `set_auth_account_password.mjs` use the script-only Supabase client. They are operator foundations, not the approved ADMIN UI/setup/recovery flows.
- No Resend adapter, email provider boundary, notification worker, Turnstile verifier, or existing email delivery implementation was found.

### Rate limiting

- `frontend/lib/auth/login-throttle.ts` provides process-memory per-identifier and global password-failure counters plus a password-hash concurrency cap.
- It has no PostgreSQL persistence, trusted-client-IP dimension, Turnstile threshold, email-destination limit, or challenge/account recovery counters.

### Runtime and deployment

- `docker-compose.yml` runs frontend, internal-only FastAPI backend, ModSecurity on host port 8088, and the audit bridge. The frontend calls `http://backend:8000` inside Compose.
- `docker-compose.demo-target.yml` adds the optional separate portal, ModSecurity host port 8089, and demo-target bridge.
- `frontend/Dockerfile` pins Node 24; the root backend image pins Python 3.14. The active shell Node was 22.22.2, so validation uses the bundled Node 24.14.0 runtime.
- No committed public deployment configuration was found. The current verified deployment boundary is local Compose plus hosted Supabase; a connected public thesis environment remains `Planned`.
- `.codex/config.toml` and `.codex/agents/terra-worker.toml` are ignored abandoned-workflow files and were left unchanged as instructed.

## Files Changed by Unit

- Unit 0: `docs/project-ops/AUTH_V6_EXECUTION_LOG.md`
- Unit 1: `.env.example`, `web_app/config.py`, `web_app/notifications/*`, `web_app/presentation/app.py`, `web_app/presentation/api/routes.py`, `scripts/run_resend_smoke.py`, migration `20260710_000009`, and focused notification/migration/PostgreSQL/script tests.
- Unit 2: account-management migration `20260710_000010`, server-only account-management/token/password modules, ADMIN and public setup/verification route handlers, User Management/setup UI, role/sidebar/header updates, and focused frontend/backend/PostgreSQL tests.
- Unit 3: TOTP migration `20260710_000011`, server-only AES-GCM/TOTP/backup-code modules, enrollment RPC adapters/routes/UI, MFA enrollment permission, QR generation dependency, and focused frontend/backend/PostgreSQL tests.

## Migrations and RPCs Introduced

- Unit 0: none.
- Unit 1: additive revision `20260710_000009`; RPCs `claim_notification_outbox_batch`, `complete_notification_outbox_job`, and `fail_notification_outbox_job` with `SECURITY INVOKER`, empty `search_path`, fully qualified tables, bounded inputs, `PUBLIC`/`anon`/`authenticated` revokes, and conditional `service_role` grant.
- Unit 2: additive revision `20260710_000010`; RPCs `admin_create_auth_account`, `admin_resend_password_setup`, `consume_password_setup_token`, `admin_change_account_role`, `admin_set_account_enabled`, `admin_request_managed_email_change`, and `activate_verified_managed_email`. All are `SECURITY INVOKER`, use an empty `search_path`, apply bounded inputs and actor/self-mutation checks, and revoke browser roles with conditional `service_role` grants.
- Unit 3: additive revision `20260710_000011`; RPCs `begin_totp_enrollment`, `activate_totp_factor`, `consume_totp_step`, `list_backup_code_candidates`, and `consume_backup_code`. They enforce pending/active/revoked factor lifecycle, atomic monotonic TOTP-step consumption, one-time backup-code updates, safe security events, and owner notifications.

## Validation Evidence

- Workspace: abandoned `feat-cybertrace-v6-1` worktree path absent; no external matching process; `git worktree prune --verbose` completed; main checkout clean on the expected branch.
- Frontend baseline with Node 24.14.0: focused Auth.js, route-guard, server DB, dashboard layout, and BFF suite -> 9 files, 117 tests passed.
- Backend baseline: auth-foundation migration plus application-startup tests -> 30 passed.
- Unit 1 red evidence: notification imports/migration were absent; later direct smoke execution reproduced `ModuleNotFoundError: web_app` before the entrypoint fix.
- Unit 1 focused backend gate: notification providers/templates/worker/service/outbox/threat/smoke, configuration, WAF route, app startup, and migration tests -> 74 passed before final hardening; focused provider/migration hardening -> 12 passed; direct smoke wrapper regression -> 1 passed.
- Unit 1 final full backend suite: 558 passed, 2 opt-in PostgreSQL tests skipped in the ordinary environment-gated run; the same 2 tests passed separately against disposable PostgreSQL.
- Unit 1 disposable PostgreSQL 17: full migration upgrade succeeded; outbox two-worker claim and transaction-rollback tests -> 2 passed using independent connections; downgrade one revision and re-upgrade succeeded. Target was local container `cybertrace-v61-pgtest`, not hosted or production.
- Unit 1 dependency/compile checks: `pip check` reported no broken requirements; `compileall` and `git diff --check` passed.
- Unit 1 live Resend: safely skipped. Required key/from/approved-recipient/enablement gates were all absent or false; no network request was made.
- Unit 2 focused frontend gate with Node 24.14.0: ESLint passed, TypeScript passed, and 64 targeted Vitest tests passed.
- Unit 2 full frontend gate with Node 24.14.0: 52 test files and 360 tests passed; production `next build` completed successfully with non-production sentinel environment values.
- Unit 2 backend gate: full suite 562 passed and 6 opt-in PostgreSQL tests skipped in the ordinary environment-gated run.
- Unit 2 disposable PostgreSQL 17: migration source checks 3 passed; account-management integration 4 passed, including concurrent single-use setup-token consumption, authz-version changes, MFA derivation, managed-email activation, old-address notice, and collision rejection. The container target was local `cybertrace-v61-pgtest`, not hosted or production.

## Failures, Fixes, and Risks

- Environment: default shell resolved Node 22.22.2 instead of the pinned major. Fix: use bundled Node 24.14.0 for all frontend gates.
- Discovery mismatch: V6.1 plan names one logical challenge table while the repository has separated MFA, email-OTP, and completion tables. Decision: preserve the existing additive split and extend it narrowly where it can satisfy the same invariants.
- Risk: no disposable PostgreSQL target has yet been confirmed. No migration or schema mutation will be applied until a non-production target is proven.
- Risk: live Resend and deployed connected-environment checks depend on external configuration and remain separate from fake/mocked implementation proof.
- Unit 1 implementation regression: direct script execution lacked the repository root import path. Fixed in the command wrapper and locked with a subprocess regression test.
- Unit 1 High self-review fixes: legacy `sending` rows now receive an immediately reclaimable lease during migration; completion is owner-bound rather than time-bound after provider acceptance; provider message IDs are restricted to log-safe characters before reporting.
- Unit 1 remaining limitation: provider acceptance is proven through fake/mocked contracts only; real inbox delivery, verified-domain sending, and deployed worker operation remain external human/deployment actions.
- Unit 2 implementation regression: initial downgrade left `email_verification` reset rows that violated the restored legacy constraint. Fix: downgrade deletes only those ephemeral rows before restoring the prior constraint; durable accounts and security events remain preserved.
- Unit 2 High self-review fixes: managed-email requests reject collisions against current and pending addresses; custom mutation routes enforce the configured same-origin `Origin` boundary before parsing bodies; Next response-header rules keep route-specific no-store/no-referrer/noindex rules after the global rule so the specific values win.
- Unit 2 remaining limitation: successful ADMIN mutations remain intentionally unreachable until Unit 4 supplies `auth_level=mfa`, `auth_method=totp`, and recent `auth_time` claims. Public setup/verification routes are explicit POST-only flows and do not auto-login.
- Unit 3 focused frontend gate with Node 24.14.0: crypto/TOTP/backup/enrollment/guard/route/component tests passed; ESLint and TypeScript passed after the final QR component change.
- Unit 3 disposable PostgreSQL 17: migration upgrade, downgrade to `20260710_000010`, and re-upgrade all passed; TOTP activation/replay and concurrent backup-code consumption tests passed 2/2.
- Unit 3 remaining limitation: normal password-plus-TOTP login, pre-auth challenge, Auth.js completion handoff, and recovery workflows remain deferred to Units 4 and 5. Enrollment is feature-flagged off by default.
