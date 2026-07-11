# PR #83 Remediation Execution Record

**Execution date:** 2026-07-11  
**Working branch:** `feat/cybertrace-v6-1`  
**Starting HEAD:** `488436c277db28f3a54dd36de09c2cdb4d5b6016`  
**Migration head after this work:** `20260711_000018`

This is the living evidence record for the PR #83 remediation plan. Feature
switches remain disabled. No hosted Supabase database, production credential,
or live email provider was used.

## End-to-end hardening execution

This section tracks the follow-up implementation units that revalidate the
remaining PR #83 findings against the current branch. The findings below are
evidence classifications, not completion claims.

### Progress

- [ ] Unit 0 — Baseline and evidence freeze
- [ ] Unit 1 — Deterministic authentication E2E harness
- [ ] Unit 2 — Redirect, worker, readiness, and reconciliation correctness
- [ ] Unit 3 — Merge evidence and repository cleanup
- [ ] Unit 4 — Outbox secret protection and hosted-readiness preparation
- [ ] Unit 5 — Thesis-grade evidence package
- [ ] Unit 6A — Required Playwright CI gate
- [ ] Unit 6B — Notification reconciliation observability
- [ ] Unit 6C — Restricted break-glass mechanism
- [ ] Unit 6D — Operational documentation consolidation

### Unit 0 baseline freeze

| Item | Verified baseline |
|---|---|
| PR | Open draft PR #83, base `master`, head `feat/cybertrace-v6-1` |
| Starting HEAD | `4995f7641c880a6b4767c91316452aa3e03a02b1` locally, on `origin/feat/cybertrace-v6-1`, and at the PR head |
| Worktree | Pre-existing untracked root `package.json`, `package-lock.json`, and `test-results/` are preserved as user-owned files; no tracked modification was present before this record update |
| Runtime | Python `3.14.3`; frontend checks use the repo-pinned Node `24.18.0` and npm `11.16.0` through `fnm` |
| Migration head | Alembic reports `20260711_000018 (head)`; revisions `000008` through `000018` form one additive chain |
| Feature switches | `AUTH_ACCOUNT_MANAGEMENT_ENABLED`, `AUTH_MFA_ENROLLMENT_ENABLED`, `AUTH_EMAIL_RECOVERY_ENABLED`, `AUTH_PASSWORD_RESET_ENABLED`, `AUTH_TURNSTILE_ENABLED`, `NOTIFICATION_WORKER_ENABLED`, `NOTIFICATION_WORKER_REQUIRED`, `THREAT_EMAIL_ENABLED`, and `RESEND_LIVE_TEST_ENABLED` are `false` in the tracked examples/defaults |
| Remote CI | At the starting HEAD, GitHub reports `backend`, `postgres`, `frontend`, and `secret-scan` successful; the workflow contains no authentication Playwright job |
| Frontend baseline | Six targeted auth files passed: 28 tests. Playwright lists the five Chromium auth journeys, but its actual run times out before executing them because the configured Turbopack development server fails to build `/login` in the current multi-lockfile checkout |
| Backend baseline | Targeted notification worker/service/smoke, config, and public-health coverage passed: 28 tests |
| Documentation discovery | `docs/agent-tooling.md` is referenced by maintained docs and repository instructions but is `Not Found` in this branch |

The current Playwright startup failure was isolated without changing source:
`npx playwright test e2e/auth-journeys.spec.ts --project=chromium` timed out
waiting for the configured default Next.js development server after a React
client-manifest error. Starting the same tracked application with
`npm run dev -- --webpack` returned HTTP 200 for `/login`. The untracked root
lockfile remains untouched; Unit 1 must add a repo-owned, automated regression
and a stable server strategy.

### Finding revalidation at the starting HEAD

| Finding | Status | Repository evidence and impact |
|---|---|---|
| F-01 | CONFIRMED | `frontend/e2e/auth-journeys.spec.ts` submits the same environment-provided TOTP for login and recent step-up, while the database records and rejects reused accepted time steps. Replay protection must remain unchanged. |
| F-02 | CONFIRMED | All five journeys require static `CYBERTRACE_E2E_*` identity, password, TOTP, backup-code, or email-OTP values. No setup/teardown harness creates disposable identities or retrieves fresh recovery values. |
| F-03 | CONFIRMED | The suite is skipped unless two manual environment switches are set, and `.github/workflows/ci.yml` has no Playwright job. The current local run also fails during web-server startup before journey execution. |
| F-04 | CONFIRMED | `frontend/auth.ts` consumes MFA and recovery completion tokens although the Credentials provider declares only identifier/password fields. It accepts the first completion mode found and does not reject mixed password/MFA/recovery input. Existing tests call `authorize` directly rather than proving the framework/browser handoff. |
| F-05 | CONFIRMED | Enrollment, login, MFA verification, recovery, and step-up paths compare thrown error messages to the private string `NEXT_REDIRECT`. Unexpected exceptions share broad catch blocks. |
| F-06 | CONFIRMED | `web_app/notifications/worker.py` increments `sent` immediately after provider acceptance and before `repository.complete()` succeeds. A completion failure is logged but not counted as failed or ambiguous. |
| F-07 | CONFIRMED | `/health` and `/api/health` share one handler and return overall `healthy` whenever the database probe succeeds, including when a configured required worker is unavailable, unhealthy, or starting. |
| F-08 | CONFIRMED | The PR body still reports 572 backend passes, 406 frontend tests, and 13 migration/integration checks, while the checked-in execution record and current head contain later counts and an additional commit. Final evidence must be regenerated. |
| F-09 | CONFIRMED | `.env.example` and `web_app/notifications/smoke.py` contain a personal smoke recipient. Related tests bind behavior to that value. Replace it with a non-personal, explicit opt-in test boundary. |
| F-10 | CONFIRMED | Migration functions persist reset, setup, verification URLs and email-recovery OTPs as plaintext JSON in `notification_outbox.payload_safe_json`; the worker reads the same plaintext mapping. Terminal scrubbing does not protect pending rows. |
| F-11 | UNKNOWN | The repo contains a deployment runbook, but no authorized hosted project/provider identity or smoke evidence is available in this run. Hosted migration, role, provider, email, and feature-flag actions remain prohibited. |
| F-12 | CONFIRMED | The five browser definitions are not a required CI gate and have no isolated database/PostgREST setup or failure-artifact job. |
| F-13 | CONFIRMED | Completion failures emit only a generic warning plus error type. Event, request/trace, provider message, idempotency, attempt, state, outcome, reconciliation, and duration fields are absent. |
| F-14 | CONFIRMED | `operator_reset_admin_mfa` and its script create an audit event and require a reason, but execute through the broad service-role boundary; maintained architecture docs acknowledge that no isolated break-glass role exists. |
| F-15 | CONFIRMED | Stable auth, migration, notification, recovery, and demo instructions overlap across setup and operator docs. `docs/CONTEXT.md` also retains a stale `Not Yet Implemented` list that contradicts its own PR #83 section. |

### Initial validation matrix

| Requirement | Baseline command/procedure | Result at starting HEAD |
|---|---|---|
| Auth/TOTP/credential handoff units | `npx vitest run --pool=threads lib/auth/totp.test.ts lib/auth/auth.integration.test.ts app/api/mfa-enrollment-finalize.test.ts app/api/mfa-verify.test.ts app/api/mfa-step-up.test.ts app/api/mfa-recovery.test.ts` | PASS — 6 files / 28 tests; mixed-mode rejection is not covered |
| Worker/readiness/config units | `.venv\\Scripts\\python.exe -m pytest -q tests/unit/notifications/test_worker.py tests/unit/notifications/test_service.py tests/unit/notifications/test_smoke.py tests/integration/test_api.py::test_auth_health_endpoint_is_public tests/integration/test_app_startup.py::test_auth_api_health_endpoint_is_public tests/unit/test_config.py` | PASS — 28 tests; durable-completion ambiguity and required-worker readiness are not covered |
| Critical browser suite discovery | `npx playwright test e2e/auth-journeys.spec.ts --project=chromium --list` | PASS — five journeys listed |
| Critical browser execution | `npx playwright test e2e/auth-journeys.spec.ts --project=chromium` | FAIL — configured web server timed out before tests ran |
| Migration topology | `.venv\\Scripts\\python.exe -m alembic heads` plus revision/down-revision inspection | PASS — single head `20260711_000018`; runtime behavior still requires disposable PostgreSQL replay after changes |

### Decision log

#### D-001 — Preserve the existing PR branch and user-owned untracked files

- Date: 2026-07-11
- Actor: Codex
- Decision: Work only on `feat/cybertrace-v6-1`, preserve the three pre-existing untracked root paths, and use tracked frontend tooling rather than the untracked root Playwright install.
- Rationale: PR #83 points to this branch; deleting or adopting unknown user files would violate the execution safety rules.
- Evidence: local/remote/PR SHA equality and the initial `git status --short --branch` output.
- Alternatives considered: deleting the root lockfile, adopting the root package, or creating another feature branch; all were rejected as unsafe or contrary to the requested PR target.
- Compatibility impact: none.
- Rollback impact: none; this is an execution-boundary decision.

### Surprises and discoveries

#### 2026-07-11 — Playwright server fails before skipped journeys are reported

- Status: CONFIRMED
- Evidence: the configured default Next.js server timed out with a login-route client-manifest error; webpack served the same route successfully.
- Impact: the earlier `25 skipped` evidence is not reproducible from the current checkout, and browser execution needs both a deterministic data harness and a stable server startup path.
- Plan change: Unit 1 will cover the server command with an automated config test before changing it, then retain webpack or another repository-supported stable path only if the regression passes.

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
