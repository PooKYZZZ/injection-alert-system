# Project Ops Status

**Scope:** operator-only session status
**Defense:** May 2026
**Last updated:** 2026-07-30

---

## Current Verified Repo State

### PR7 Block 1 and Block 2 controlled-local enforcement

- The branch implementation adds the additive migration
  `20260728_000025_add_pr7_effective_waf_state.py` with a singleton revision
  row, durable effective WAF state, PostgreSQL lifecycle constraints, restricted
  recommendation ownership, and partial uniqueness for ACTIVE source/path
  owners. Disposable PostgreSQL upgrade, downgrade, re-upgrade, and one-head
  checks passed; the final migration head is `20260728_000025`.
- The async mutation repository canonicalizes source IP/path inputs, locks the
  singleton first under `READ COMMITTED`, uses PostgreSQL `clock_timestamp()`,
  performs idempotent recommendation creation and effective-state mutation in
  one transaction, increments the desired-state revision once per change, and
  retains terminal rows for auditability. The final disposable PostgreSQL
  integration matrix passed **16 tests**, including same-key and different-key
  serialization, lock-wait timing, replay finality, supersession, capacity
  finality, snapshot stability, and injected rollback.
- The repeatable-read read-only snapshot and authenticated controlled-local
  endpoint are implemented and covered by focused tests.
- Block 1 effective-state migration, repository, and authenticated snapshot
  endpoint are implemented.
- Block 2 local WAF runtime is implemented in PR #97 at current head
  `d74d6b6` (documentation sync after implementation head `77aa821`).
- The runtime uses the pinned CRS image, deterministic ModSecurity rules, safe
  startup, reload confirmation, candidate-specific probing, rollback,
  OFF/DRY_RUN/ENFORCE modes, and persistent disable.
- Focused runtime suite: **50 passed locally**.
- Real PostgreSQL-to-backend-to-WAF CRITICAL integration: **passed**.
- PR7 Block 3 controlled-local attack-to-WAF lifecycle: **passed**. The real
  staged model classified the SQLi vector as `SQL Injection` / `CRITICAL`, the
  JSONL bridge created one atomic PR7 state, Block 2 returned a matching-source
  403, source/path isolation held, WAF-side upstream fields were empty, and
  revocation cleared the snapshot. Evidence is in
  `docs/project-ops/PR7_BLOCK_3_EVIDENCE.md`.
- GitHub CI: backend, PostgreSQL, migrations, frontend, authentication E2E,
  secret scan, and PR7 WAF runtime passed.
- Hosted, staging, and production enforcement remain disabled.
- Real Cloudflare ingress/source equivalence, combined PR6/PR7 portal
  interaction, portal-owned no-upstream evidence, and any hosted rollout
  remain unverified or blocked.

- Historical PR5 merge reference: backend PR #90 commit `62fc168`.
  Git is authoritative for the current branch and HEAD.
- Python runtime target: `3.14+`
- Local venv currently recreated and verified on: `Python 3.14.3`
- Frontend runtime: Next.js `16.2.9`, React `19.2.4`, TypeScript `5.9.3`, Zod `4.3.6`
- Backend runtime: FastAPI `0.138.0`, Pydantic `2.12.5`, SQLAlchemy `2.0.48` (async)
- Model/runtime artifacts boundary: `ml_model/model_registry/`
- Data/runtime boundary: Supabase-backed PostgreSQL for app runtime, SQLite for tests
- DistilBERT promotion workflow CLI: `ml_model/export/promote_final_training_run.py`
- Active staged path remains stable: `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755`
- Client requirements are now tracked in `docs/client-requirements.md`: secure login, RBAC, 2FA, timely alerts, email notifications after detection, and `CRITICAL >=90%`.
- Account-security runtime: Auth.js Credentials login now reads Supabase `auth_accounts`, verifies Argon2id hashes, preserves role/authz/MFA claims, and rechecks current DB account state across protected BFF routes.
- Auth/security schema foundation implemented: an additive Alembic migration defines nine public-schema auth/security tables with RLS enabled, public-role privileges revoked, and no policies; `frontend/lib/server/db/` provides validated server-only Supabase service-role access. Hosted Supabase is migrated through `20260712_000020`; the full chain and downgrade/re-upgrade also passed on disposable PostgreSQL.
- `AUTH_USERS_JSON` is no longer a runtime login or freshness source. Supabase/client failure fails closed with no env fallback; the hosted test account is provisioned through the supported flow.
- Alerts dashboard UI role affordances now hide unavailable dense-row actions for viewers, keep triage controls for analysts, and keep the full control set for admins.
- Login hardening is local/process-bound: approved Argon2id PHC parameter enforcement, precomputed same-profile dummy verification, bounded per-identifier failure throttles, a default two-operation password-hash cap, database-expiring password-level MFA sessions, replay-safe TOTP/recovery claims, current-row MFA fail-closed checks, and secret-safe JSON login and route-guard audit events are implemented.
- Operational account scripts load `frontend/.env.local` for ordinary provisioning. ADMIN MFA break glass instead uses `scripts/operator_reset_admin_mfa.py` with a dedicated direct PostgreSQL login whose only membership is the execute-only `cybertrace_break_glass` role. TOTP, recovery, and password-reset feature flags fail closed when absent and are evaluated at request time.
- PR #83 adds database-authoritative MFA/recovery handoffs, recent-TOTP step-up, password-work preflight, protected notification payloads, notification lifecycle/worker hardening, required PostgreSQL and authentication-browser CI jobs, and the hosted Admin journey. Public deployment is active through Cloudflare Tunnel at `app.cybertracesystems.com`; `target.cybertracesystems.com` is protected by Cloudflare Access; the Resend domain and live delivery are verified.

### Telegram threat alerts PR state

- The local PR3 branch adds Telegram as a second durable outbox channel at
  historical Alembic revision `20260720_000022`. Only persisted non-Normal `HIGH` and
  `CRITICAL` confidence-tier alerts are eligible.
- Detection persistence and SSE remain authoritative. Email and Telegram
  enqueue attempts have separate failure boundaries; provider/API work remains
  in the worker and cannot change a successful WAF response.
- Telegram uses existing HTTPX and Bot API `sendMessage`, plain text, explicit
  timeouts, bounded 429/5xx retry behavior, a 30-minute deadline, safe logs,
  database-enforced channel/kind restrictions, and channel-specific dedupe.
- External exactly-once Telegram delivery is not claimed. A post-commit enqueue
  crash window and provider-accepted/database-completion ambiguity remain
  documented limitations.
- Automated provider tests use mocks only. No live Telegram message, hosted
  deployment, or hosted migration is claimed in this status.
- Local verification after implementation: focused Telegram/config/migration/WAF
  matrix **165 passed**; canonical backend suite **754 passed, 34 skipped**;
  disposable PostgreSQL notification outbox/lifecycle **10 passed**; migration
  upgrade, downgrade to `20260715_000021`, re-upgrade, and final
  `20260720_000022` as the historical PR3 endpoint all passed. The full suite skips PostgreSQL unless an
  explicit disposable URL is supplied, so these evidence classes remain separate.

### PR4 shadow enforcement state

- PR4 End-to-End Shadow Enforcement ✅ MERGED: portal PR #89 merged into
  `stable/portal-pre-waf` as `bdeef868a8a3d9e56f9593f3b3f776cff165c26a`, and
  backend PR #88 merged into `master` as
  `ad170c36462eb12293a268a9a049c6fd2188f933`. The post-merge
  `demo-target-8089` smoke passed on the merged stack. Fresh post-merge
  evidence, including healthy recommendation matching, backend-down fail-open,
  recovery, and a second full smoke is recorded in
  `reports/shadow-enforcement/e2e-proof.md`.
- Post-merge manual validation passed: the maintained demo-target smoke
  correlated a fresh CRS HTTP 403 event through audit, bridge, and backend;
  the later benign `/records/search` request returned HTTP 200; the active
  recommendation matched as `CRITICAL` with hypothetical `WAF_BLOCK`, while
  `actual_decision=ALLOW` and `degraded=False` remained true.
- Backend-down validation passed with portal HTTP 200 and sanitized
  `TIMEOUT_OR_NETWORK` degradation; backend recovery and a second complete
  WAF correlation smoke also passed. A transient startup/readiness timing
  report and successful shadow-check log visibility remain non-blocking
  follow-ups only.
- Code is implemented locally through Alembic head `20260720_000023`: completed
  WAF triage can create one expiring recommendation for `/records/search`.
  Recommendation persistence runs after the single inference queue releases its
  worker, and expiry is anchored to the authoritative WAF event timestamp so a
  late replay cannot resurrect stale state. The dedicated-key internal check
  returns `ALLOW` for completed evaluations,
  returns `503` when lookup is unavailable, and logs match metadata.
- The separate land-records portal calls that check server-side only from
  `/records/search`; it makes one bounded attempt and fails open. No browser
  bundle, middleware, or real block/throttle control is involved.
- Final tested source pair: CyberTrace
  `7587bdf24df58adf534328ff468520bb9932cfef`, land-records-portal PR89
  `8e8dabc725d1ea0d171210296f2bfe4569e995ab`. The portal Docker runtime files
  are committed in PR89; no uncommitted source is required for the tested image.
  Focused backend PR4 validation passed `52` tests with `1` PostgreSQL test
  skipped; portal enforcement tests, typecheck, lint, and production build
  passed. The final single-stack WAF smoke and a backend-unavailable fail-open
  smoke both passed, and `/records/search` was sanity-checked in the in-app
  browser.
- Final portal-path latency was material: shadow healthy p50 `320.0 ms` versus
  enforcement-off p50 `20.3 ms`; the portal-container-to-backend check alone
  measured p50 `297.1 ms`. The earlier p50 `4.67 ms` backend-only result came
  from a different measurement/runtime and is not comparable. Shadow mode does
  not change allow/block outcomes, but it introduces synchronous latency while
  enabled. Hosted shadow enablement remains deferred pending target-topology
  measurement and timeout selection; live expiration was not destructively
  forced because active recommendations were preserved.

### PR #90 — PR5: add controlled LOW/MEDIUM active enforcement

- Backend PR #90 is merged into `master` at `62fc168`; its five CI jobs passed.
  The separately evidenced portal PR #91 passed its recorded CI checks; no portal
  merge state is asserted here.
- Controlled local full-stack E2E is PASS through the realistic
  `http://localhost:8089/records/search` path using Docker Compose and disposable
  PostgreSQL 16. The canonical evidence is
  [`reports/active-enforcement/PR5_CONTROLLED_E2E_PROOF.md`](../../reports/active-enforcement/PR5_CONTROLLED_E2E_PROOF.md).
- The E2E run validated LOW challenge/grant persistence and valid-grant counter
  bypass; MEDIUM immediate challenge, grant persistence, fixed-window counting,
  positive retry countdown, and throttling; invalid Turnstile with no grant/window;
  and backend-evaluation outage fail-open with no fabricated grant/window.
- LOW 1–5 ALLOW and sixth-request CHALLENGE, and MEDIUM 10→11 throttling, were
  functionally observed. Clean one-request-at-a-time screenshot pairs for those
  exact boundaries were not preserved because refreshes were rapid during parts
  of the manual run.
- PR4 `SHADOW` remains advisory and preserves historical recommendation rows and
  `action_taken` values. HIGH/CRITICAL active blocking, WAF enforcement, Redis,
  and global middleware are out of scope.
- The PostgreSQL concurrency test and the controlled E2E used disposable local
  database state; no hosted database mutation is claimed.
- Hosted/production `ENFORCEMENT_MODE` defaults to `off`; no hosted destructive
  enforcement readiness or real-user rollout is claimed. Cloudflare trusted-source,
  Pseudo IPv4, origin-isolation, and related topology gates remain open.

**Completed:** implemented, wired, automated-tested, and controlled-local
E2E-validated LOW/MEDIUM check, challenge, grants, counters, and throttling;
five PR #90 CI jobs succeeded. Evidence: `web_app/presentation/api/routes.py`,
`web_app/application/enforcement_use_cases.py`, enforcement tests, and
`reports/active-enforcement/PR5_CONTROLLED_E2E_PROOF.md`.

**Partially completed:** none within the approved PR5 local scope; hosted rollout
is a separate gate. **Resolved gaps:** stale tracker claims that LOW/MEDIUM and
Turnstile were absent (no stable prior IDs). **New gaps:** `BUG-001`, `BUG-002`,
`LIMIT-005`, `BUG-003`. **Known limitations:** `LIMIT-001` and the local-versus-
production evidence boundary only. **Technical debt:** none newly classified.
**Deferred:** `DEFER-001` only. **Still open:** `BLOCK-001`, `BLOCK-002`,
`GAP-002` (partial), `BUG-001`, `BUG-002`, `LIMIT-005`, `LIMIT-006`,
`LIMIT-007`, and `BUG-003`. See
`IMPLEMENTATION_GAP_REGISTER.md` for definitions and cumulative state.

### PR6 working branch — HIGH application blocking

- CyberTrace branch `feat/pr6-high-enforcement` extends the existing v2
  recommendation query and response contract so valid applicable HIGH rows
  return exact `BLOCK`; HIGH outranks MEDIUM/LOW and CRITICAL remains excluded.
- The sibling portal branch `feat/pr6-portal-high-enforcement` accepts only exact `BLOCK`,
  stops before protected record-search work, renders generic temporary-block
  copy, keeps the dynamic response non-cacheable, and logs
  `enforcement.application_block_applied` at the actual block branch. Unknown/malformed responses remain fail-open.
- Automated validation passed: backend full suite **859 passed, 36 skipped**
  with process-only notification-worker isolation; PR6 focused backend tests
  passed; portal **32 unit tests**, typecheck, lint, and production build passed.
  PostgreSQL-only repository tests were **NOT_RUN** because no explicit test URL
  was supplied to pytest; equivalent migrated-query behavior was exercised in
  the disposable controlled E2E database.
- Final coordinated controlled local E2E passed for active HIGH block, absence of record-table
  content, `no-store` response headers, deterministic expiry, outage fail-open,
  safe block/degraded logs, and backend recovery. Exact distinct-source E2E was
  not possible in the single-source local topology; automated query tests cover
  wrong-source isolation. HTTP 403 was not adopted because the installed stable
  Next.js page API would require enabling experimental cross-app
  `authInterrupts`; the server-rendered block view currently returns HTTP 200.
  The consolidated review fixes are covered by red/green focused and full-suite
  tests; the final controlled proof is recorded in
  `reports/active-enforcement/PR6_HIGH_APPLICATION_BLOCK_PROOF.md`.
- Shared-IP collateral blocking is tracked as `LIMIT-006`; HTTP 200 block
  semantics are tracked as `LIMIT-007`. Hosted/production `ENFORCE` remains disabled. `BLOCK-001` and `BLOCK-002`
  remain open. `GAP-001` is complete for the approved local PR6 scope;
  `GAP-002` is partially resolved for PR7 CRITICAL/WAF enforcement; the
  remaining trust-topology, portal, and PR6 integration evidence is listed in
  the gap register.

### Trusted source correlation PR state

- PR #84 implementation is frozen at baseline
  `6cfe67bd331e55d4309c201c8c254668bc2ea688`. The branch was clean, remote CI
  was green, and this maintenance pass adds documentation only; no PR1 feature
  work remains.
  PR2 implemented SSE separately. This historical PR #84 note does not describe
  current work; Telegram is a completed historical PR3 slice.

### Real-time alert SSE PR state

- PR #85 implementation and all five GitHub checks are green: backend,
  frontend, postgres, auth-e2e, and secret-scan. Frontend lint, typecheck,
  audit gate, Vitest, and production build also passed.
- Local PR2 validation passed: backend **717 passed, 32 skipped**, frontend
  **87 files / 498 Vitest tests**, the named SSE edge matrix passed **97 backend
  tests and 31 frontend tests**, and disposable Chromium SSE E2E passed.
- Manual technical WAF verification on 2026-07-19 passed four consecutive
  `waf-8088 --require-backend-lookup` runs. Each passed healthz, API health,
  SQLi block, audit transaction, backend lookup, and final summary. Markers:
  `CYBERTRACE_SMOKE_20260719T160600_dbbf110dfbb14c3088b9fe34cc16c0a4`,
  `CYBERTRACE_SMOKE_20260719T160811_dec1f89a858441d88f1561881993cd68`,
  `CYBERTRACE_SMOKE_20260719T160849_b17bd52a0f1749a1a198c64ca1b210c0`,
  and `CYBERTRACE_SMOKE_20260719T161013_1e6a73a29fb54694afc3524dde70c9e4`.
- Manual browser verification passed: an open Alerts page received new
  persisted alerts without refresh; the browser connected to the authenticated
  hosted `/api/alerts/stream` endpoint with `text/event-stream`; offline/online
  recovery reconnected EventSource, refetched canonical REST state, and showed
  the missed alert without a page reload.
- Hosted SSE delivery and browser reconnect were manually verified through
  `https://app.cybertracesystems.com`. This proves the tested deployment path,
  not every possible Cloudflare or proxy configuration.
- Hosted source-correlation regression also passed from two independent phone
  two independent network paths remained distinct in
  new `/records/search` alerts and did not collapse to `172.18.0.1`. This is
  regression evidence only; hosted WAF verification remains `unverified`.
- PR2 remains intentionally bounded: the broadcaster is single-process and
  in-memory, there is no durable replay or `Last-Event-ID`, no multi-worker
  fan-out, and no latency benchmark was performed.

- PR #84 remediation is implemented through the single Alembic head
  `20260715_000021`:
  canonical source/provenance contracts, separate WAF submission credential,
  ingest-time verification derivation, factual SHA-256 fingerprints, immutable
  duplicate metadata, and atomic matching stale reclaim.
- Default Compose now excludes the technical WAF pair; `technical-waf` restores
  `8088`. Hosted rendering excludes that pair and publishes exactly one
  loopback `8089`. The controlled topology has separate trusted/untrusted
  networks, one `/32` trusted proxy, no host ports, and an isolated SQLite DB.
- Hosted startup now has one explicit persistent path:
  `scripts/start_hosted_target.ps1` reads the ignored root `.env`, validates the
  observed narrow `HOSTED_WAF_TRUSTED_PEER`, requires
  `WAF_SOURCE_VERIFICATION_MODE=unverified`, and then renders the hosted
  overlay. Missing or broad trust values fail before Compose starts.
- The pinned CRS image is
  `owasp/modsecurity-crs@sha256:0385a81159d5112c113eeeed01c3f6cf05113891b02addc23abeab180934911e`
  (NGINX `1.28.2`, ModSecurity `3.0.14`, connector `1.0.4`, CRS `3.3.8`).
  The controlled real-IP fix moves the directives to HTTP context because the
  image's generated location include did not rewrite `$remote_addr` before
  ModSecurity observed the request.
- WAF audit parts are now `AIJDEFHZ`; part `B` is excluded so raw request
  headers, including Cloudflare Access material, are not retained. The bridge
  and CRS correlation path passed without that part, and the three confirmed
  disposable local audit files were cleared after their writers were stopped.
- Local full backend regression: **703 passed, 32 skipped**. The latest
  focused source/integrity suite passed **189 tests**; the migration-focused
  run passed **2 tests** with one PostgreSQL-only test skipped locally; the
  executable SQLite migration cycle also passed.
- Disposable PostgreSQL 16 CI upgraded from `20260712_000020` to
  `20260715_000021`; **114 integration** and **39 migration** tests passed.
  The earlier local parent/head downgrade and re-upgrade cycle also passed;
  the final CI run exercised the updated constraint on the full chain.
- Compose rendered in a clean exported checkout with no `.env`: all **8**
  topology and hosted-persistence tests passed. The same pinned Gitleaks 8.24.3
  scan found no leaks.
- A real `ModelService` initialization smoke using Transformers `5.5.0` and
  the configured staged DistilBERT registry loaded
  `distilbert_v3_907k_cleaned_20260312_133755` as
  `DistilBertForSequenceClassification`; no new dependency error occurred.
  The separate model-packaging/classifier-head follow-up remains out of scope.
- Frontend lint, typecheck, **84 files / 480 Vitest tests**, and production
  build passed locally. No frontend source changed.
- Remote CI is recorded separately. Initial run `29384464612` failed backend
  because Compose tests required the absent developer `.env`, and secret-scan
  found one deterministic test fixture. Run `29393146395` fixed those failures
  but exposed backend dependency-audit findings. Run `29393701878` passed the
  earlier remediation head; final run `29428801740` passed **backend, postgres,
  frontend, auth-e2e, and secret-scan** after the database-invariant and driver
  corrections. Implementation head `6cfe67b` also passed all five required jobs
  after the Torch `2.13.0` security upgrade.
- Local controlled packet-path proof **passed on 2026-07-17**: Client A
  `172.30.10.4`, Client B `172.30.10.5`, and the direct forged-header client
  `172.30.11.4` remained distinct and persisted as `DIRECT_REMOTE_ADDR` with
  `UNVERIFIED` status; all three SQLi requests returned HTTP 403.
- Operator hosted proof also passed for home Wi-Fi and mobile data: each public
  egress source remained distinct and matched the ModSecurity, bridge, FastAPI,
  PostgreSQL, and dashboard records. Forged-header resistance, the fresh-audit
  credential-leakage check, and hosted restart/recreate proof also passed.
  Exact operator addresses are retained in private evidence rather than this
  repository.
- Hosted identity verification remains **Partial by design**. The remaining
  checks are Cloudflare Pseudo IPv4, Worker header behavior, direct-origin
  isolation, and independent confirmation that the configured `/32` is the
  immediate tunnel-side peer. `WAF_SOURCE_VERIFICATION_MODE` remains
  `unverified`; no hosted `VERIFIED` claim is made.

### PR #83 completed release checks

- Hosted migration through `20260712_000020`, live Resend delivery, Admin invitation/setup/password flow, TOTP enrollment, invalid-code rejection, MFA-authenticated Admin login, and User Management access are verified.
- The runtime feature-flag prerender defect is fixed with request-time server-side evaluation. Environment changes require container recreation or restart.

### Deferred / post-merge follow-up

- [ ] Redesign MFA enrollment UI.
- [ ] Redesign backup-code UI.
- [ ] Validate notification-worker retry, duplicate prevention, provider-failure handling, and required-worker health behavior.
- [ ] Audit MFA feature-flag behavior when enrollment is disabled.
- [ ] Investigate local-only Playwright null-session behavior if it reappears.
- [ ] Review the Auth.js beta upgrade in a separate PR.
- [ ] Evaluate passkeys/WebAuthn as a later enhancement.

### PR #83 validation snapshot

- Full backend suite with disposable PostgreSQL integration enabled: **650 passed**.
- PostgreSQL integration suite: **107 passed**.
- Migration-source suite: **37 passed**.
- Downgrade from `20260712_000020` to `20260711_000019` and re-upgrade: **passed**; the earlier `000019` plaintext compatibility gate was also exercised.
- Frontend lint and typecheck: **passed**.
- Frontend full Vitest: **83 files / 473 tests passed**.
- Frontend production build: **passed**.
- Managed authentication browser project: **5/5 Chromium journeys passed** with disposable PostgreSQL/PostgREST setup and cleanup; the same project is a required CI job.

### Latest local verification results

- PR2 SSE slice: backend full suite **717 passed, 32 skipped** with local
  notification-worker overrides; frontend full Vitest **87 files / 498 tests
  passed**; lint, typecheck, and production build passed. The named SSE edge
  matrix passed **97 backend tests** and **31 frontend tests**.
- Disposable real-stack SSE browser proof:
  `cd frontend && node scripts/run-sse-e2e.mjs` → **1/1 Chromium test passed**.
  The managed run applied the real Alembic chain to disposable PostgreSQL,
  seeded real password/TOTP auth through PostgREST, started loopback FastAPI and
  Next.js on ephemeral ports with generated keys, and proved a unique WAF alert
  was committed, signaled through the authenticated SSE BFF, refetched, and
  rendered without another main-frame navigation request. Cleanup left **0**
  labeled containers, **0** labeled networks, and **0** backend temp directories.
  Browser-native reconnect and named-domain hosted SSE proof were subsequently
  verified manually on 2026-07-19.
- Backend dependency integrity: `.venv\Scripts\python.exe -m pip check` → **pass**
- Click vulnerability remediation: `click==8.3.3`; `.venv\Scripts\python.exe -m pip_audit -r requirements.txt` → **no known vulnerabilities**
- Backend full suite with local worker flags disabled for SQLite tests: `.venv\Scripts\python.exe -m pytest -q` → **619 passed, 31 skipped**
- PostgreSQL integration suite: `.venv\Scripts\python.exe -m pytest -q tests/integration` → **76 passed, 31 skipped**
- Migration suite: `.venv\Scripts\python.exe -m pytest -q tests/migrations` → **37 passed**
- Backend PR #83 disposable-PostgreSQL run: `.venv\Scripts\python.exe -m pytest -q` with `CYBERTRACE_POSTGRES_TEST_URL` → **650 passed**
- Final-demo script tests: `.venv\Scripts\python.exe -m pytest -q tests/scripts/test_run_final_demo_smoke.py` → **16 passed**
- API abuse smoke tests: `.venv\Scripts\python.exe -m pytest -q tests/integration/test_api_abuse_smoke.py` → **4 passed**
- WAF ingest and inference queue tests: `.venv\Scripts\python.exe -m pytest -q tests/integration/test_waf_ingest_route.py tests/unit/test_inference_queue.py` → **25 passed**
- Request-context regression tests: `.venv\Scripts\python.exe -m pytest -q tests/unit/test_request_context_middleware.py` → **9 passed**
- App startup sanity: `.venv\Scripts\python.exe -c "from web_app.presentation.app import create_app; print(bool(create_app()))"` → **True**
- Frontend lint: `cd frontend && npm run lint` → **pass**
- Frontend typecheck: `cd frontend && npm run typecheck` → **pass**
- Frontend BFF-focused tests:
  - `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **96 passed**
- Frontend full suite: `cd frontend && npx vitest run --pool=threads` → **83 files / 473 tests passed**
- Managed authentication E2E: `cd frontend && npm run test:e2e:auth` → **5/5 passed** with unconditional disposable cleanup
- Frontend production build: `cd frontend && npm run build` → **pass**
- PR #79 exposed an intermittent Ubuntu 24.04 / Node `24.18.0` native `Napi::Error` during threaded Vitest. PR #81 removes accidental native Argon2 loading from non-hashing auth/provisioning tests, retains real Argon2id coverage in `password-hash.test.ts`, and passed the full frontend CI job twice. Vitest remains on `threads`; package scripts, CI workflow, production Argon2id, and auth behavior are unchanged.
- Promotion pipeline unit tests: `.venv\Scripts\python.exe -m pytest -q tests/unit/test_promote_final_training_run.py` → **21 passed**
- Dependency gates: `pip-audit -r requirements.txt` found no known vulnerabilities after the `click` patch; `npm audit --audit-level=high` passed with two transitive moderate PostCSS findings and no high/critical findings. The forced npm fix is breaking and was not applied.
- Promotion dry-run command (April DistilBERT source path) → **pass** (planned actions printed, no writes)
- Promotion real-run command (April DistilBERT source path) → **failed closed** with strict checkpoint architecture incompatibility:
  - `package_serving_artifact.py` strict load expects DistilBERT classification head shapes (`768`) but final-training checkpoint head uses `256`-dim layers
  - rollback behavior verified: active staged run restored; archive target not left behind

### Verified WAF ingest proof

Evidence file: `reports/modsecurity-live-proof/e2e-proof.md`
Audit-log policy file: `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`

- WAF proof path uses `localhost:8088`.
- Backend is internal-only in Docker Compose and shows `8000/tcp`; do not use `localhost:8000` unless backend port 8000 is explicitly published.
- Backend transaction lookup proof uses Docker-internal `docker compose exec -e TXID=$txid backend ...`.
- `/healthz` through `localhost:8088` returned HTTP 200.
- `/api/health` through `localhost:8088` returned HTTP 200 and `{"status":"healthy","database":"connected"}`.
- SQLi probe `/api/health?id=17%27%20OR%2017%3D17--` through WAF returned HTTP 403.
- ModSecurity audit log contained transaction `17821639659.909603`, source IP `172.21.0.1`, and request URI `/api/health?id=17%27%20OR%2017%3D17--`.
- Bridge posted `status=200 transaction_id=17821639659.909603 rule_ids=['942100', '949110']`.
- Docker-internal lookup returned `found=true`, `prediction=SQL Injection`, `confidence_level=HIGH`, `action_taken=BLOCKED`, `source_ip=172.21.0.1`, `request_path=/api/health`, URL-encoded `query_string`, `crs_score=5`, and CRS rules `942100`, `949110`.
- Targeted WAF checks: bridge tests `47 passed`, WAF ingest route tests `12 passed`, WAF ingest use-case tests `4 passed`; the combined boundary set is `63 passed`.
- Current-marker live proof passed on 2026-07-05 for both `localhost:8088` and the optional `localhost:8089` demo target, including audit-log and Docker-internal backend correlation. The smoke waits boundedly for audit flush and bridge persistence rather than accepting stale evidence.
- ModSecurity audit-log policy is documented; automatic rotation and production retention remain TODO.
- Bridge follow-mode transient `readline()` `OSError` resilience is implemented and unit-tested in `tests/scripts/test_waf_audit_bridge.py`; the follow loop preserves the last safe file position, warns, sleeps briefly, reopens, and continues processing later lines.

### Observability and traceability

- FastAPI responses include `X-Request-ID`; safe incoming IDs are preserved and missing or invalid IDs are replaced. Generic unhandled `500` responses also return the request ID without exposing raw exception details.
- Valid W3C version-00 `traceparent` headers supply the request `trace_id` and `span_id`; otherwise the backend generates a local `trace_id` without inventing a span.
- Request completion/failure, WAF ingest outcomes, and direct prediction outcomes use single-line JSON logs through `web_app/observability/structured_logging.py`.
- The WAF bridge emits single-line JSON events for startup, configuration failures, follow mode, retry, post success/failure, duplicate skip, read errors, and summary counts; configuration failures use JSON stderr while normal operations remain on stdout.
- `transaction_id` correlates bridge and backend WAF events. Within FastAPI, `request_id` and `trace_id` correlate route and ingest/prediction events for one request.
- New structured-log fields are redacted recursively and case-insensitively for Authorization, cookies, API keys, tokens, passwords, secrets, sessions, credentials, and database connection values. Raw request bodies and query strings are not logged by the new request/route instrumentation.
- Minimal metrics remain the existing `/api/stats`, `/api/ml-health` queue health, and bridge summary log counts. No new metrics endpoint, Prometheus, tracing backend, or SIEM was added.
- Ops runbooks added as documentation-only artifacts:
  - `docs/project-ops/BACKUP_RESTORE_RUNBOOK.md`
  - `docs/project-ops/MIGRATION_ROLLBACK_RUNBOOK.md`
  - `docs/project-ops/RETENTION_POLICY.md`
  - `docs/project-ops/SUPABASE_RLS_HARDENING.md`
  - Historical task reconciliation is archived under `docs/archive/`; it is not an operational asset.
- These docs do not implement production deployment, backup automation, restore automation, database migrations, retention/archive jobs, Supabase dashboard changes, RLS policies, Wazuh export, or SIEM deployment.

### Automated final demo and abuse smoke proof

- `scripts/run_final_demo_smoke.py` provides explicit `backend`, `waf-8088`,
  and `demo-target-8089` modes with unique current-run markers, bounded HTTP
  timeouts, PASS/WARN/FAIL output, parseable `--json` output, and optional
  required Docker-internal backend correlation.
- Script tests cover parseable JSON output, controlled timeout/unavailable
  failures, and redaction of secret-like values and Authorization headers.
- The script does not read or emit the backend API secret, Authorization
  headers, database URLs, or raw request payloads. Connection failures use
  fixed safe messages without tracebacks.
- `tests/scripts/test_run_final_demo_smoke.py` is deterministic and requires no
  Docker, live network, Supabase, or sibling portal checkout.
- `tests/integration/test_api_abuse_smoke.py` adds malformed JSON, auth
  correlation/token non-leakage, and invalid triage input proof. Existing tests
  remain the source for body limits, invalid alert IDs, duplicate/unknown WAF
  transactions, model unavailable behavior, and queue overflow.
- Queue-full WAF proof now explicitly asserts `X-Request-ID`,
  `waf_ingest.queue_full`, `transaction_id`, `queue_depth`, `Retry-After`, and
  API-secret non-leakage.
- The `8088` and `8089` CLI modes remain opt-in local checks. Without
  `--require-backend-lookup`, successful audit-only proof is explicitly `WARN`;
  full proof requires the same marker and a current timestamp in the backend row.
- Starlette `TestClient` now uses pinned `httpx2==2.5.0` without the deprecated plain-`httpx` warning path; `httpx==0.28.1` remains for current consumers such as `huggingface_hub`.

### CRS baseline and demo-target proof

- CRS-only baseline is documented in `reports/modsecurity-live-proof/crs-baseline.md`.
- Demo-target WAF proof exists at `reports/modsecurity-live-proof/demo-target-crs-proof.md`; the demo-target service uses the pinned CRS image and the narrow proxy-backend template, while hosted real-IP directives are added only by the hosted override.
- The demo-target Compose profile is optional for normal developer startup and required for the final realistic WAF demonstration.
- Demo-target WAF path is `localhost:8089 -> demo-target-modsecurity -> demo-portal`.
- Demo-target CyberTrace ingest uses `demo-target-bridge`, which watches `logs/modsecurity/demo-target/modsec_audit.jsonl` separately from the default `8088` audit log.
- `demo-portal` is built from the separate land-records portal repo path by the demo-target Compose profile; the portal source remains outside this repo, runs internally on Compose port `3010`, and is not host-published by default.
- Observed demo-target evidence was captured through `localhost:8089`, including normal portal traffic and controlled SQLi/XSS checks with CRS transaction IDs, rule IDs, and matched messages where available.
- Verified demo-target bridge evidence: SQLi marker `SMOKE002945` returned HTTP 403, audit transaction `178249138618.813428` had host `localhost:8089` and path `/records/search`, `demo-target-bridge` posted `status=200`, backend lookup returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, and `crs_score=15`.

### Dashboard screenshot evidence

- Dashboard evidence is documented in `reports/modsecurity-live-proof/dashboard-evidence.md`.
- Reviewed replacement screenshots exist under `reports/modsecurity-live-proof/screenshots/`: dashboard overview variants, `8089` `/records/search` alerts table with WAF/ML rows, default `8088` WAF alert detail drawer, and ML health overview.
- The latest ML health screenshot is an overview capture; queue-health fields are available through `/api/ml-health`, but a queue-specific UI screenshot is not claimed.
- Capture target was `http://localhost:3000` only; no auth state, cookies, session headers, or secrets were written.

### Promotion Workflow Commands

- Dry-run (no writes):
  - `.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run --source-run-dir "ml_model\results\benchmarks\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" --active-run-dir "ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" --archive-root "ml_model\model_registry\archive" --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" --archive-suffix "pre_20260420" --dry-run`
- Real promotion:
  - `.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run --source-run-dir "ml_model\results\benchmarks\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" --active-run-dir "ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" --archive-root "ml_model\model_registry\archive" --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" --archive-suffix "pre_20260420"`
- Rollback behavior:
  - If failure occurs after archive, the promotion script restores the archived active run automatically.

### Current API/BFF state

- Implemented backend routes:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/stream`
  - `GET /api/alerts/{id}`
  - `PATCH /api/alerts/{id}/triage`
  - `GET /api/stats`
  - `GET /api/ml-health`
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`
- Reservation-first triage flow is active (`PROCESSING` placeholders, lease reclaim support, winner/loser behavior).
- `PROCESSING` rows are excluded from normal alerts and stats reads.
- New visible alerts publish a minimal post-commit `alert.created` signal to a
  bounded in-process broadcaster. The authenticated Next.js SSE BFF streams it
  to one dashboard EventSource, which invalidates canonical alert and stats
  queries on events and reconnect `open`.
- Frontend boundary remains:
  - `Browser -> Next.js route handlers/BFF -> FastAPI`
- Route protection and proxy entrypoint:
  - Auth checks are enforced in BFF handlers.
  - Next.js edge entrypoint uses `frontend/proxy.ts`.
  - Local `next start` validation requires `AUTH_TRUST_HOST=true` in `frontend/.env.local`.
- Alert confidence-tier naming:
  - Current tiers remain `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`.
  - Preferred query/filter naming is `confidence_tier`.
  - Legacy `severity` query compatibility is retained for existing URLs and callers.
  - Persisted backend field remains `confidence_level`.
  - `CRITICAL >=90%` is implemented as the high-confidence threshold.
  - Historical rows are not retroactively reclassified.
  - Persisted-alert dashboard counts and confidence styling use backend-emitted `confidence_level`, not raw-score reclassification.
  - Confidence distributions include all predictions; enforcement-policy counts exclude `Normal`, which remains `ALLOWED` for every valid tier.
  - Confidence-tier badges display the canonical tier and do not replace it with `Benign`.

---

## Important Notes For Operators

- CI may show four checks on branch updates because both `push` and `pull_request` workflows run for frontend and backend.
- `requirements.train.txt` is laptop/training-only and should not be treated as required for CI/backend runtime verification.
- Supabase is now part of the current runtime truth. Do not document it as merely planned.
- ModSecurity audit log policy is documented in `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`.
- Current ModSecurity audit log path is JSONL at `logs/modsecurity/modsec_audit.jsonl`.
- Bridge and selected backend boundary logs are structured JSON; legacy startup and unrelated application logs are not claimed to be converted repo-wide.
- Local WAF proof evidence remains under `reports/modsecurity-live-proof/`.
- Dashboard screenshot evidence remains under `reports/modsecurity-live-proof/dashboard-evidence.md` and `reports/modsecurity-live-proof/screenshots/`.
- Demo-target proof is separate from the default `localhost:8088` WAF proof path and requires `demo-target-bridge` when `8089` events must appear in CyberTrace.
- Automatic audit log rotation is not implemented.
- Production retention and full Wazuh/SIEM deployment are not implemented.

---

## Open Gaps (Current, Not Historical)

Previous prose items were normalized into stable IDs in
[`IMPLEMENTATION_GAP_REGISTER.md`](IMPLEMENTATION_GAP_REGISTER.md); the complete
current inventory lives there. Highest-priority current items are `BLOCK-001`,
`BLOCK-002`, `BUG-001`, and the remaining portion of `GAP-002`. This status snapshot does not
replace the register or restate its full entries.

---

## Source-of-Truth Docs

- Implementation snapshot: `docs/CONTEXT.md`
- Architecture boundaries: `docs/architecture.md`
- Local setup: `docs/SETUP.md`
- Client requirements: `docs/client-requirements.md`
- Historical system snapshots: `docs/archive/system-snapshots/`; current state is maintained in `STATUS.md` and `CONTEXT.md`.
- Implementation gaps: `docs/project-ops/IMPLEMENTATION_GAP_REGISTER.md`
- Operational/demo checklist: `docs/project-ops/LIVING_CHECKLIST.md`
- ModSecurity audit log policy: `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`
