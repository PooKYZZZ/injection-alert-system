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

- [x] Unit 0 — Baseline and evidence freeze (`d41c3d3`)
- [x] Unit 1 — Deterministic authentication E2E harness (`2689813`)
- [x] Unit 2 — Redirect, worker, readiness, and reconciliation correctness
  (`c4629c1`)
- [ ] Unit 3 — Merge evidence and repository cleanup (implementation and local
  validation complete; awaiting commit/push and PR-body evidence)
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
lockfile remains untouched. This established the baseline requirement for a
repo-owned regression and stable server strategy, which Unit 1 now supplies.

### Unit 1 deterministic authentication E2E evidence

Unit 1 replaces static credentials and skip switches with a managed local test
boundary. `npm run test:e2e:auth` now creates uniquely named, loopback-only
PostgreSQL 17.6 and PostgREST 14.14 containers plus a localhost Supabase REST
compatibility proxy; applies Alembic through `20260711_000018`; generates five
separate `example.test` identities and short-lived test keys; precompiles the
critical pages and API handlers; runs the five Chromium journeys; deletes the
seeded rows; and removes every disposable container and network in `finally`.

The final managed run passed all five journeys in 1.2 minutes and printed the
cleanup confirmation. Each journey also passed independently through the same
managed command using `--grep`; every isolated invocation provisioned a fresh
migrated environment and printed its cleanup confirmation. The evidence proves
dynamic TOTP enrollment/login, one-time backup and email recovery, forced
recovery re-enrollment, rejected replay, a newer accepted TOTP step for recent
reauthentication, final session claims, and durable database state. No hosted
project or live provider was used.

Browser traces, videos, automatic screenshots, raw page snapshots, and Next.js
server-function argument logs are disabled because they can retain passwords,
OTPs, provisioning URIs, or backup codes. Failure evidence is limited to an
HTML report, fixed redacted context, and input/QR-masked screenshot.

An independent in-app Browser smoke check reproduced the original inert login
button under the rejected loopback development origin. After the repo-owned
Next.js origin/root correction, the same local UI hydrated and transitioned to
`Signing in...`. That smoke used nonfunctional loopback database settings; the
managed Playwright project supplied the database-backed journey evidence.

| Unit 1 validation | Result |
|---|---|
| Managed auth browser project | PASS — 5 journeys / 5 passed |
| Each journey in isolation | PASS — 5 independent invocations / 5 passed |
| Frontend full Vitest suite | PASS — 83 files / 462 tests |
| Frontend lint and typecheck | PASS |
| Adjacent backend/config/health baseline | PASS — 28 tests |
| Disposable cleanup | PASS — rows, containers, network, and proxy removed |
| Gitleaks 8.24.3 PR-range scan | PASS — published RFC test vector narrowly allowlisted |

Unit 1 fixes F-01, F-02, and F-04 locally. F-03 remains partial until Unit 6A
makes the managed command a required PR job.

### Unit 2 correctness and reconciliation evidence

Unit 2 removes the final production dependency on exact `NEXT_REDIRECT` message
matching. Password login and every fetch-based Auth.js completion now use
`redirect: false`; the client owns final dashboard navigation, after which the
existing route guard selects MFA enrollment or verification as required.
Unexpected Auth.js errors retain a generic public response and redacted error
class only.

Notification delivery now increments `sent` only after
`complete_notification_outbox_job_v61` succeeds. Provider acceptance followed
by a completion exception increments a separate `ambiguous` result, does not
invoke the failure transition, and emits
`notification.delivery_completion_ambiguous`. The structured event contains the
outbox event ID, available request/trace correlation, provider message ID,
idempotency key, attempt number, requested state transition, completion result,
reconciliation status, error class, and duration. It never receives the
recipient or payload. Cancellation after provider acceptance emits the same
reconciliation evidence and then propagates shutdown.

`/health` and `/api/health` remain public aliases with their existing response
fields and now represent readiness plus component detail. Database failure or a
configured required worker in any state other than `healthy` returns 503 and an
`unhealthy` body. A disabled or unhealthy optional worker remains visible in the
component field without failing readiness. This repository does not add a
separate process-only liveness route.

| Unit 2 validation | Result |
|---|---|
| Redirect component regressions | PASS — 8 tests |
| Worker and readiness regressions | PASS — 10 tests |
| Adjacent notification/config/API suite | PASS — 72 passed / 7 PostgreSQL skips |
| Disposable PostgreSQL outbox lifecycle | PASS — 7 tests after migrations through `20260711_000018` |
| Full backend suite | PASS — 590 passed / 28 PostgreSQL-only skips |
| Frontend lint, typecheck, Vitest, build | PASS — 83 files / 462 tests / 39 static pages |
| Managed auth browser project | PASS — 5 journeys / 5 passed in 1.4 minutes |
| Disposable cleanup | PASS — PostgreSQL, PostgREST, proxy, containers, and networks removed |

Unit 2 fixes F-05, F-06, F-07, and F-13 and completes the remaining F-04
redirect-handoff hardening. The durable outbox still relies on lease expiry plus
the stable provider idempotency key for a later reconciliation attempt; no blind
same-run resend was added.

### Unit 2 outcome

- Commit: `c4629c147b21b9c4fd7a2b0e7b80c235a8b346a1`
- Remote verification: local, `origin/feat/cybertrace-v6-1`, and PR #83 head
  matched after the normal push.
- Findings addressed: F-04 remainder, F-05, F-06, F-07, and F-13.
- Files changed: login action/page and tests; Playwright config test; worker
  model/service/implementation and tests; health handler and tests; execution
  record.
- Tests: all Unit 2 validation rows above passed from the committed code state.
- CI: secret-scan passed immediately; backend, PostgreSQL, and frontend jobs were
  running when remote presence was recorded.
- Remaining work: Unit 3 onward; required Playwright CI remains Unit 6A.
- Residual risk: a provider-accepted ambiguous row requires later reconciliation
  after lease expiry; the stable provider idempotency key prevents an unkeyed
  resend but provider-side behavior still needs hosted validation before enablement.

### Unit 3 merge evidence and repository cleanup

Unit 3 began from pushed head `96ec6dc084d78eb924358c6a6b4c2b6b1a32608e`.
Local, remote, and PR metadata agreed on the branch, and every one of the 16
commits after `origin/master` appeared in the PR commit list in the same order.
The complete PR diff contained 207 files and remained confined to the planned
authentication, account-management, notification, migrations, tests, CI, and
documentation surfaces. No generated test report, coverage, build, archive, or
media artifact is tracked.

The only manifest additions are the auth E2E command plus `qrcode` and its type
package, with matching lockfile changes required by the checked-in enrollment
UI. The user-owned untracked root package files and test results remain excluded.
The auth/notification migration chain is linear from `20260704_000008` through
single head `20260711_000018`; all eleven reviewed revisions define downgrade
functions and all 33 migration tests pass. Disposable PostgreSQL migration and
outbox lifecycle replay remains 7/7 from Unit 2.

The personal smoke recipient in `.env.example` and
`web_app/notifications/smoke.py` is replaced with the non-routable,
non-personal `smoke-recipient@example.test` placeholder. The tracked-email and
credential-pattern review found only reserved example domains, provider defaults,
and explicit test vectors/fixtures. The remaining Gmail-shaped value is the
synthetic `first.last+soc@gmail.com` normalization test, not configuration or an
operator identity.

| Unit 3 validation | Result |
|---|---|
| Full backend suite after safe-example change | PASS — 591 passed / 28 PostgreSQL-only skips |
| Migration source/tests | PASS — one head / 33 tests |
| Frontend lint, typecheck, Vitest, build | PASS on unchanged frontend head — 83 files / 462 tests / 39 static pages |
| Managed auth browser project | PASS on unchanged auth head — 5 journeys / 5 passed |
| Python dependency integrity/audit | PASS — no broken requirements / no known vulnerabilities |
| npm audit at high threshold | PASS — no high/critical; 3 moderate transitive PostCSS findings recorded |
| Remote CI at `96ec6dc` | PASS — backend, PostgreSQL, frontend, secret-scan |
| Generated artifact review | PASS — none tracked |

The three moderate npm findings have no non-breaking automated remediation in
the current audit output; `npm audit fix --force` proposes an unrelated breaking
Next.js change and was not run. Hosted database/provider identity, live email,
hosted smoke, and feature enablement remain explicitly unperformed.

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

#### D-002 — Use a disposable Supabase-compatible local boundary

- Date: 2026-07-11
- Actor: Codex
- Decision: Use migrated PostgreSQL plus standalone PostgREST behind a
  localhost `/rest/v1` compatibility proxy and generated service-role JWT.
- Rationale: Exercise the existing Supabase client and database functions
  without changing the Browser -> Next.js boundary or touching the hosted
  project.
- Evidence: the final five-journey run and unconditional cleanup confirmation.
- Alternatives considered: static credentials, a hosted test project, direct
  browser database access, and a test-only production route; all were rejected.
- Compatibility impact: test-only local processes and ignored reports.
- Rollback impact: remove the dedicated config, orchestrator, setup, support,
  and journey changes; production feature switches remain unchanged.

#### D-003 — Represent provider-accepted completion failures explicitly

- Date: 2026-07-11
- Actor: Codex
- Decision: add an `ambiguous` worker result and structured reconciliation event;
  count `sent` only after the durable completion transition succeeds.
- Rationale: provider acceptance is not equivalent to a committed outbox state,
  while treating it as an ordinary failure can cause an unsafe immediate resend.
- Evidence: worker failure, retry, cancellation, redaction, and PostgreSQL outbox
  lifecycle tests.
- Alternatives considered: count provider acceptance as sent; mark the job
  failed immediately; add a new database state in this unit.
- Compatibility impact: the result dataclass gains a defaulted field and existing
  lease/idempotency behavior is preserved.
- Rollback impact: revert the worker/model/service changes; no schema change.

#### D-004 — Treat both existing health paths as readiness with component detail

- Date: 2026-07-11
- Actor: Codex
- Decision: keep `/health` and `/api/health` public and shape-compatible, but
  return 503 when the database or a required notification worker is unready.
- Rationale: startup already fails fast for a required worker; runtime health must
  not report healthy for the same condition.
- Evidence: unit coverage for required, optional, disabled, and database-failure
  states plus route-level public/readiness tests.
- Alternatives considered: add new health paths; fail readiness for optional
  worker degradation; retain HTTP 200 for an unhealthy body.
- Compatibility impact: unhealthy readiness changes HTTP status from 200 to 503;
  JSON fields are unchanged.
- Rollback impact: restore the previous status-code behavior; no data impact.

### Surprises and discoveries

#### 2026-07-11 — Default diagnostics retained interactive secrets

- Status: FIXED
- Evidence: Playwright's automatic page snapshot included filled input values,
  and Next.js development server-function logging included action arguments.
- Impact: even disposable credentials must not enter retained artifacts or CI
  logs.
- Correction: attach a fixed redacted context, retain masked screenshots only,
  disable raw trace media, disable server-function/browser-console forwarding,
  and ignore web-server stdout in the auth project.

#### 2026-07-11 — Cold compilation reloaded stale auth state

- Status: FIXED
- Evidence: first-use page/API compilation reloaded enrollment after the
  database incremented `authz_version`, correctly invalidating the old password
  session before the client rendered completion state.
- Correction: prewarm five pages and nine POST handlers; fetch-based completion
  handlers use Auth.js `redirect: false` and client-owned final navigation.

#### 2026-07-11 — Published RFC TOTP vector triggered the secret scanner

- Status: FIXED
- Evidence: the first CI run for `2689813` identified only the public RFC 6238
  SHA-1 Base32 test vector in `totp.test.ts` under the generic API-key rule.
- Impact: no credential was exposed, but the required secret-scan job correctly
  remained red until the false positive was bounded.
- Correction: retain the default gitleaks rules and add an `AND` allowlist scoped
  to the exact generic rule, exact test path, and exact published vector. A local
  gitleaks 8.24.3 scan of the same 13-commit PR range reports no leaks.

#### 2026-07-11 — Auth config test depended on a gitignored local file

- Status: FIXED
- Evidence: Unit 1 frontend CI failed TypeScript resolution for
  `./playwright.config`; the file exists locally but is explicitly ignored and is
  absent from a clean checkout.
- Impact: local validation passed while Linux CI correctly rejected the
  non-portable test dependency.
- Correction: keep the tracked authentication config self-contained, remove the
  ignored base-config import, and revert the local ignored-file edit. Targeted
  config tests and clean TypeScript validation pass.

#### 2026-07-11 — Playwright server fails before skipped journeys are reported

- Status: CONFIRMED
- Evidence: the configured default Next.js server timed out with a login-route client-manifest error; webpack served the same route successfully.
- Impact: the earlier `25 skipped` evidence is not reproducible from the current checkout, and browser execution needs both a deterministic data harness and a stable server startup path.
- Plan change: Unit 1 will cover the server command with an automated config test before changing it, then retain webpack or another repository-supported stable path only if the regression passes.

## Prior PR implementation snapshot

The sections below preserve the evidence snapshot that existed before the
follow-up units above. The progress list and unit evidence supersede any older
browser-unavailable statement in this snapshot.

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
