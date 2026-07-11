# PR #83 Remediation Execution Record

**Execution date:** 2026-07-11  
**Working branch:** `feat/cybertrace-v6-1`  
**Starting HEAD:** `488436c277db28f3a54dd36de09c2cdb4d5b6016`  
**Migration head after this work:** `20260711_000018`

This is the living evidence record for the PR #83 remediation plan. Feature
switches remain disabled. No hosted Supabase database, production credential,
or live email provider was used.

## Phase status

| Phase | Status | Evidence / notes |
|---|---|---|
| P0 revalidation and baseline | Complete | Repository instructions, plan, current source, migration chain, CI, and baseline checks re-read. Ordinary baseline was 572 passed / 15 PostgreSQL skips; frontend lint, typecheck, Vitest, and build passed. |
| P1 authentication and assurance | Complete | Purpose-bound completion consumers, DB `verified_at`, trusted Auth.js claims, challenge-expiring password sessions, and fail-closed enrollment guards are covered by frontend tests and PostgreSQL state tests. |
| P2 enrollment and recovery | Complete in code | Factor-aware enrollment, final enrollment handoff, persistent TOTP/OTP attempts, backup/email recovery, retry-safe handoff, and password-token preflight are implemented and PostgreSQL-tested. |
| P4 password work and throttling | Complete | Shared bounded Argon2 concurrency gate, token preflight, per-identifier cooldowns, and bounded identifier memory are unit-tested. Turnstile remains disabled as planned. |
| P5 notification lifecycle | Complete except payload encryption gate | Versioned deadline/claim/terminal functions, cancellation triggers, supported templates, legacy terminalization, batch-one worker behavior, lease-safe transitions, health state, and provider validation are implemented and PostgreSQL/unit-tested. Terminal scrubbing is implemented; pending secret-bearing payload encryption remains a required security decision before enablement. |
| P6 CI, browser, operations, and docs | Partial | Required PostgreSQL CI job and five Playwright journeys are checked in. Browser execution is not proven locally because Playwright browsers and a seeded Supabase-backed app environment are unavailable. Maintained docs and runbook were updated with this boundary. |

## Finding disposition

- **Fixed:** F-01 through F-13, F-15 through F-19, F-21 through F-23, F-25,
  F-28, F-29, F-30, F-32, and F-33.
- **Partial:** F-14 (terminal payload scrubbing is enforced, but the preferred
  pending-payload encryption design is not enabled or approved); F-20 (the
  operator helper is explicitly documented as a high-privilege service-role
  helper, not an isolated break-glass role); F-22 (browser journeys are added
  but not executed in this environment).
- **Already correct / retained:** F-24 remains a disabled Turnstile helper and
  is not treated as the primary rate limit; F-26 retains the existing
  best-effort alert enqueue contract and documents that alert persistence is
  authoritative.
- **External validation required:** F-27 requires a deployment-time identity
  check proving Next.js and FastAPI use the same intended PostgreSQL target.
- **Deferred by plan:** F-31 remains outside the remediation scope.

## PostgreSQL evidence

Disposable local PostgreSQL was used at `127.0.0.1:55432` only. The following
checks passed against it:

- `pytest -q tests/integration` — 104 passed.
- `pytest -q tests/migrations` — 33 passed.
- `alembic upgrade head` — passed.
- Clean downgrade to `20260710_000014` and re-upgrade to
  `20260711_000018` — passed.
- `cd frontend; npm run lint` — passed.
- `cd frontend; npm run typecheck` — passed.
- `cd frontend; npx vitest run --pool=threads` — 73 files / 417 tests passed.
- `cd frontend; npm run build` — passed.
- `.venv\Scripts\python.exe -m pip_audit -r requirements.txt` — no known
  vulnerabilities.
- `npm audit --audit-level=high` — exit 0; three existing moderate PostCSS
  findings remain and remediation would require a breaking dependency change.
- Redacted Gitleaks scan of tracked and untracked working-tree files — no
  leaks after removing legacy hard-coded smoke-runbook credentials. A
  history-inclusive scan still reports five redacted placeholder matches in
  an older smoke-runbook commit.
- `cd frontend; npm run test:e2e` — 25 tests skipped because the required
  seeded E2E environment and Playwright browser binaries are unavailable.
- Auth, recovery, step-up, enrollment, account-status idempotency, outbox
  deadline, cancellation, lease, and terminal-scrub tests — passed.

## Remaining gates

- Install the pinned Playwright browsers and run the five journeys against a
  disposable seeded Supabase-compatible application environment.
- Approve and implement the pending secret-bearing notification payload
  encryption/key-management design before enabling security-email flags.
- Verify the intended shared PostgreSQL target and apply migrations through a
  reviewed hosted deployment process; this record does not authorize that
  operation.
- Obtain an approved Resend/provider configuration and recipient before any
  live delivery smoke.

## New discoveries and deviations

- Enrollment, backup recovery, and email recovery increment `authz_version`
  before the browser completes Auth.js sign-in. The ordinary freshness guard
  therefore rejected the legitimate retry/handoff request. A narrowly scoped
  exception now requires the MFA-enrollment permission, a password-level
  session with the expected challenge purpose and unexpired challenge claim,
  and a present short-lived completion cookie; ordinary stale sessions remain
  denied.
- The repository’s standalone PostgreSQL integration tests use the venv
  interpreter and a psycopg URL. Bare `pytest` selected the global Python 3.13
  interpreter and was not used as evidence. An initial async-driver URL also
  failed psycopg parsing; the corrected disposable URL passed all tests.
- The current smoke runbook contained four hard-coded `local-dev-secret`
  examples. They were replaced with container-side `API_SECRET_KEY` lookup;
  the redacted working-tree Gitleaks scan now reports no leaks. History still
  contains five redacted placeholder matches in an older runbook commit.

## Final validation snapshot

- Backend: `.venv\Scripts\python.exe -m pytest -q` with disposable PostgreSQL
  — 612 passed.
- PostgreSQL: `.venv\Scripts\python.exe -m pytest -q tests/integration` — 104
  passed; `.venv\Scripts\python.exe -m pytest -q tests/migrations` — 33
  passed.
- Frontend: lint, typecheck, `npx vitest run --pool=threads` (73 files / 417
  tests), and build — passed.
- Browser: `npm run test:e2e` — 25 skipped because the required seeded
  environment and browser binaries are unavailable.
- Migration: clean downgrade/re-upgrade — passed; final head is
  `20260711_000018`.
- Dependency and secret scans: pip-audit clean; npm audit has no high/critical
  findings but retains three moderate PostCSS findings; redacted working-tree
  Gitleaks clean.
