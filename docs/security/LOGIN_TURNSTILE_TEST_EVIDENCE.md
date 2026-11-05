# Adaptive Login Turnstile Implementation Evidence

**Reviewed:** 2026-11-05
**Branch:** `feat/auth-adaptive-turnstile-login`
**Base:** `master` at `3542838a2225db95e79e6528e21ceb5352a06d4e`
**State:** Implemented and verified locally; not deployed or enabled in production.

## Phase checklist

- [x] Phase 0: inspected live auth, throttle, audit, CSP, migration, WAF, and E2E paths; captured baseline tests.
- [x] Phase 1: independently challenged the preliminary findings and recorded corrections and residual risks in `LOGIN_TURNSTILE_REAUDIT.md`.
- [x] Phase 2: checked current OWASP, NIST, Cloudflare, Auth.js, Next.js, Supabase, and WCAG guidance; design choices and links are in `LOGIN_TURNSTILE_DESIGN.md`.
- [x] Phase 3: created the dedicated branch after the audit and research; kept unrelated dirty work out of the feature commits.
- [x] Phase 4: added canonical-account PostgreSQL state and atomic attempt reservations, covered by disposable PostgreSQL and migration tests.
- [x] Phase 5: enforced challenge verification within Auth.js `authorize()`, retaining exclusive MFA and recovery modes.
- [x] Phase 6: added conditional accessible widget rendering, token lifecycle handling, narrow CSP allowances, and environment documentation.
- [x] Phase 7: exercised aliases, direct callback bypass, cooldown, concurrency, MFA/recovery, CSP, mobile-width layout, and the existing WAF Turnstile path.
- [x] Phase 8: completed final validation and reviewed the feature diff. PR submission is recorded after the branch push below.

## TDD record

- Baseline auth suite before implementation: **6 files / 57 tests passed**.
- RED checkpoint after writing the first implementation assertions: **7 files failed; 20 tests failed and 43 passed**. The missing shared storage/RPC, migration, verifier integration, and conditional UI were the expected failures.
- The real PostgreSQL slice exposed a qualified SQL `LEAST` issue. The Cloudflare dummy-key test exposed the official `example.com`/no-action response shape. E2E caught a missing isolated fixture identity and a shared MFA seed; each was corrected and retested.
- Final independent SQL review added a stale-reservation completion test first: managed disposable PostgreSQL was **red (1 failed, 9 passed)** because an expired lease could still increment failures. The completion RPC was tightened to consume only a live reservation; the stale row is removed without changing the failure count. The rerun passed all **10 PostgreSQL cases** and the focused challenge journey.
- Green storage checkpoint was pushed as `0737f48` after the PostgreSQL and migration tests passed. Audit/research checkpoint `ce61b31` was pushed before implementation.
- Hosted CI exposed an old PR7 migration test that hard-coded `20261007_000033` as the Alembic head. It now checks the invariant: one head, with the PR7 revision still in its history. The full local migration suite and hosted PostgreSQL migration suite pass.
- Final acceptance tests added after the first green run cover failure-window expiry, cooldown expiry, expired reservations, a fresh token after a wrong password, unrelated-account availability, account aliases across browser contexts, and challenge followed by the existing TOTP handoff. These passed with the completed implementation.
- Hosted run `41969067392` reached all 12 auth journeys: 11 passed, while the theme journey first sampled an intermediate border transition and its Playwright retry stayed on the MFA page. Because the test could reuse a TOTP step already accepted by its first attempt, retry login now waits for a fresh step in line with the existing replay policy. The E2E also captures one fully consistent theme-color snapshot; the focused regression, focused browser journey, and full 12-journey suite pass locally after both fixes.
- The user then requested shortening the known-account cooldown from 300 to 60 seconds. RED tests confirmed the old 300-second default was still wired through the policy and PostgreSQL adapter; the code default and sample environment now use 60 seconds. GREEN: 49 targeted policy/adapter/Auth.js tests, the 840-test frontend suite, and the 12-journey managed auth E2E passed with the 60-second default. The 300-second failure window, five-failure limit, Turnstile token lifetime, and configurable environment override remain unchanged. No migration or database contract change was needed.

## Final validation

All commands ran locally on **Node v24.20.0**. The managed auth harness created a temporary PostgreSQL/PostgREST setup, applied the repository Alembic chain, used Cloudflare's published dummy keys only for loopback E2E, and removed its disposable resources afterward.

| Command | Result |
|---|---|
| `npm exec -- vitest run --pool=threads` | **119 files / 840 tests passed**; rerun after the cooldown change |
| `npm exec -- vitest run lib/auth/login-throttle-policy.test.ts lib/auth/login-throttle.test.ts lib/server/db/login-throttle.test.ts lib/auth/auth.integration.test.ts` | **49 passed** after the cooldown change |
| `npm run lint` | **0 errors**; 6 existing `window.location.assign()` warnings in unrelated navigation components |
| `npm run typecheck` | Passed |
| `npm run build` | Passed; local build used throwaway `AUTH_SECRET`/Supabase values, Turnstile disabled, and no public site key |
| `npm run test:e2e:auth` | **12/12 Chromium journeys passed**; rerun after the cooldown change; includes email/username/UUID rotation, refresh, fresh browser context, 390px layout, focus order, effective CSP, direct Auth.js callback denial, successful Turnstile, TOTP completion, retry-safe TOTP, and transition-stable theme assertions |
| `npm run test:e2e:auth -- --grep "theme changes and dashboard charts stay immediate across affected pages"` | **1/1 focused Chromium journey passed** after the hosted transition-snapshot failure |
| Managed `tests/integration/test_auth_login_throttle_postgres.py` | **10 PostgreSQL cases passed** on disposable tmpfs DB: thresholds, disabled-feature cooldown, cross-connection concurrency, success reset, window/cooldown expiry, reservation pruning/expiry, unrelated-account availability, and grants/RLS |
| Managed Alembic downgrade/re-upgrade | Passed on disposable PostgreSQL |
| `.venv\Scripts\python.exe -m pytest -q --tb=short tests/migrations/test_auth_login_throttle_migration.py` | **2 passed** |
| `.venv\Scripts\python.exe -m pytest -q --tb=short tests/migrations` | **64 passed**; includes the current single-head history invariant |
| `.venv\Scripts\python.exe -m pytest -q --tb=short tests/unit/test_enforcement_route.py tests/unit/test_enforcement_repository.py tests/unit/test_enforcement_policy.py tests/unit/test_enforcement_auth_dependency.py tests/unit/test_enforcement_use_cases.py tests/unit/test_enforcement_turnstile.py tests/unit/test_enforcement_schema.py tests/unit/test_post_triage_enforcement.py tests/integration/test_enforcement_check_route.py tests/waf_runtime/test_compose.py` | **124 passed**; dedicated WAF Turnstile configuration/path remains separate |
| `.venv\Scripts\python.exe -m pip_audit -r requirements.txt --ignore-vuln PYSEC-2026-3447` | **No known vulnerabilities found**; the existing certifi pin is updated to `2026.10.18` |
| `git diff --check` | Passed during final diff review |

The explicit `npm run build` loaded the ignored local Next environment file as Next.js normally does; its contents were not read or recorded. The feature flag and public site key were explicitly set to disabled/empty for that build. The managed E2E build separately used only generated disposable test credentials.

### Hosted CI

On PR #185 at code head `4820dee`, all eight hosted CI jobs passed, including backend tests and `pip-audit`, PostgreSQL integration and migrations, frontend lint/typecheck/Vitest/build, dependency review, secret scan, container smoke, WAF runtime checks, and auth E2E. The hosted auth job ran **12/12 Chromium journeys** and passed its disposable PostgreSQL throttle tests and migration downgrade/re-upgrade. Earlier runs at `5f49307` and `849606a` hit an intermittent external `next/font/google` Orbitron response parse error before Playwright. Run `41969067392` at `e174a2b` reached Playwright and passed 11/12 journeys; the theme journey exposed the intermediate-color/retried-TOTP issue recorded above. Those E2E fixes were verified locally and the latest hosted run was green. The 60-second cooldown adjustment was first verified locally; hosted run `42012465193` attempt 1 hit the same external Google Font parse error before Playwright, then attempt 2 at code head `3d74ee7` passed all eight jobs, including **12/12 auth E2E journeys**.

## Acceptance matrix

| ID | Status | Executed evidence and boundary |
|---|---|---|
| AT-01 | PASS | Auth integration success and normal login → TOTP E2E; challenge journey also reaches TOTP after password success. |
| AT-02 | PASS | Generic wrong-password auth test; first two E2E failures show no widget. |
| AT-03 | PASS | Auth integration challenge boundary and E2E shows verification after the third failure, before the next password check. |
| AT-04 | PASS | Login action/page tests submit no token until the server requests verification; Auth.js boundary rejects missing required token. |
| AT-05 | PASS | Direct credentials callback E2E without a token produces no session. |
| AT-06 | PASS | Auth integration test verifies a valid token before Argon2 and counts the wrong password. |
| AT-07 | PASS | Auth integration preserves the MFA handoff; E2E completes Turnstile, password, and TOTP in order. |
| AT-08 | PASS | Disposable PostgreSQL test confirms the fifth failure starts the 60-second cooldown and even verified attempts remain blocked. |
| AT-09 | PASS | E2E reloads the login page and uses a clean browser context; shared state continues across both. |
| AT-10 | PARTIAL | PostgreSQL integration uses independent connections and proves shared persistent state/concurrent admission. Separate application processes or a production replica/restart were not started. |
| AT-11 | PASS | Auth integration and real seeded E2E rotate the same account through email, username, and UUID. |
| AT-12 | PASS | Unknown and disabled accounts return generic outcomes; unknowns use dummy Argon2 and do not create persistent throttle rows; local map bounds entries. |
| AT-13 | PASS | Twelve concurrent independent PostgreSQL clients admit at most the configured five reserved attempts. |
| AT-14 | PASS | Verifier tests reject empty, oversized, timeout/duplicate, malformed, and wrong-host tokens; direct callback test confirms no-token denial. |
| AT-15 | PASS | Verifier tests reject wrong action, missing action, and wrong hostname. |
| AT-16 | PARTIAL | Unit tests cover timeout, HTTP 4xx/5xx, malformed JSON, and fail-closed config. A live Cloudflare outage/latency E2E was not run because the managed harness has no safe server-side provider interception. |
| AT-17 | PASS | Auth integration requires another token after a challenged wrong password; UI tests discard submitted tokens and reset the widget. |
| AT-18 | PASS | PostgreSQL tests cover success reset, active cooldown, cooldown expiry, failure-window expiry, and expired reservation cleanup. |
| AT-19 | PARTIAL | Full E2E covers TOTP login/enrollment, backup/email recovery, step-up, forgot-password privacy, roles, and session freshness. The password-reset feature remains disabled in the managed environment, so reset completion E2E was not run. |
| AT-20 | PASS | CSP config tests plus a browser assertion on the effective login response confirm the Turnstile origin and `frame-ancestors 'none'`. |
| AT-21 | PARTIAL | Component roles/status, keyboard focus order, and a 390px browser layout pass. A manual screen-reader review was not performed. |
| AT-22 | PASS | Feature-off PostgreSQL test preserves the five-failure, 60-second cooldown; invalid enabled config fails closed before password verification. |
| AT-23 | PASS | Audit unit tests and auth integration assertions verify credentials, raw identifiers, tokens, secrets, and store errors are not logged. |
| AT-24 | PASS | 124 focused backend enforcement/WAF tests passed; the auth feature uses separate `AUTH_TURNSTILE_*` settings. |
| AT-25 | PASS | Config test rejects Cloudflare's dummy credentials in production outside the guarded managed loopback harness. |
| AT-26 | PASS | Target cooldown remains enforced; a database test confirms an unrelated account can still authenticate. Residual targeted account lockout risk is documented. |
| AT-27 | N/A | No public challenge-status endpoint was introduced. |
| AT-28 | PASS | Migration source tests and managed disposable PostgreSQL downgrade/re-upgrade passed; RLS and role grants were checked. |

## Deployment requirements and residual limits

- Keep `AUTH_TURNSTILE_ENABLED=false` until the approved deployment applies migration `20261105_000034`, provisions production site/secret keys for the exact application hostname, sets the cooldown override to 60 seconds if present, rebuilds with `NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY`, and validates CSP/grants/login in staging.
- Never deploy the official dummy keys. The task did not modify production, hosted database state, Cloudflare configuration, CI, or deployment secrets.
- The five-failure, 60-second cooldown can still be targeted against one known account; the shorter delay allows a new failure round sooner than the original five-minute default. Unknown-identifier throttling remains process-local and bounded; persistent audit storage and trusted-IP global controls remain separate decisions.
- Local browser/database evidence does not establish hosted routing, production credentials, Cloudflare provider availability, app-replica behavior, or production migration state. Screen-reader and reset-completion E2E also remain unverified as listed above.

## Git / review state

- Branch: `feat/auth-adaptive-turnstile-login` (pushed after each major green implementation slice).
- Commits pushed before PR submission: `ce61b31` audit/research; `0737f48` shared PostgreSQL throttle; `a49940e` stale-reservation fix; `54bcb58` Auth.js challenge enforcement; `7c9e877` conditional UI and CSP; `ac6a6b1` E2E and MFA regressions; `c144b47` test evidence and rollout docs.
- Follow-up commits pushed: `aca85ad` PR link in evidence; `a05fb73` current migration-history assertion; `548c347` transition-aware theme E2E; `5f49307` certifi security pin; `849606a` retry-safe TOTP and consistent theme-color snapshots.
- PR: [#185](https://github.com/PooKYZZZ/injection-alert-system/pull/185) targeting `master`; open for review.
- No merge or production change is authorized by this implementation task.
