# Project Context

Updated: 2026-07-13
Defense: May 2026
Client: LARES (Land Registration Systems, Inc.)

## What This Repo Is Today

The repository currently contains:

- A FastAPI backend built around a Clean Architecture split:
  - `domain -> application -> infrastructure -> presentation`
- A Next.js 16 dashboard using the App Router, Auth.js credentials auth, route handlers, Zod, TanStack Query, and Zustand
- ML lifecycle assets under `ml_model/`, including staged transformer artifacts and an inference wrapper
- Migration scaffolding and the current migration set under `migrations/`
- Documentation and academic deliverables under `docs/`
- A live Supabase-backed PostgreSQL runtime path for application data
- A verified local ModSecurity/OWASP CRS -> bridge -> FastAPI WAF ingest proof path through Docker Compose
- A demo-target WAF profile for `localhost:8089`, with a separate `demo-target-bridge` that forwards protected demo website audit events to CyberTrace. The profile is optional for normal developer startup and required for the final realistic WAF demonstration.

This is not yet a production Docker/Redis deployment. The codebase includes Dockerfiles and a `docker-compose.yml`; the technical CyberTrace backend WAF proof path uses `localhost:8088`, the protected demo website WAF path uses profile port `localhost:8089`, and the dashboard browser path remains the Next.js BFF path.

Client-stated PD2 requirements are tracked in `docs/client-requirements.md`. They include secure login, RBAC, strong account security with 2FA, timely threat alerts, email notification after detection, and a `CRITICAL >=90%` confidence tier.

## Verified Status

### Live WAF ingest proof (2026-06-22)

Evidence file: `reports/modsecurity-live-proof/e2e-proof.md`

- WAF proof path uses `localhost:8088`.
- Backend service is internal-only in Docker Compose and shows `8000/tcp`; do not use `localhost:8000` unless backend port 8000 is explicitly published.
- Backend transaction lookup proof uses Docker-internal `docker compose exec -e TXID=$txid backend ...`.
- `/healthz` through `localhost:8088` returned HTTP 200.
- `/api/health` through `localhost:8088` returned HTTP 200 with `{"status":"healthy","database":"connected"}`.
- SQLi probe `/api/health?id=17%27%20OR%2017%3D17--` through WAF returned HTTP 403.
- ModSecurity audit log contained `transaction.unique_id=17821639659.909603`, `transaction.client_ip=172.21.0.1`, and request URI `/api/health?id=17%27%20OR%2017%3D17--`.
- Bridge posted `status=200 transaction_id=17821639659.909603 rule_ids=['942100', '949110']`.
- Docker-internal backend lookup returned `found=true`, `prediction=SQL Injection`, `confidence_level=HIGH`, `action_taken=BLOCKED`, `source_ip=172.21.0.1`, `request_path=/api/health`, URL-encoded `query_string`, `crs_score=5`, and CRS rules `942100`, `949110`.
- Targeted checks passed: bridge tests `47 passed`, WAF ingest route tests `12 passed`, WAF ingest use-case tests `4 passed`; the combined boundary set passed `63` tests.
- Bridge follow-mode transient `readline()` `OSError` resilience is implemented and unit-tested in `tests/scripts/test_waf_audit_bridge.py`; it preserves the last safe file position, warns, sleeps, and resumes follow processing after reopen.

### Realistic demo-target WAF proof (2026-06-27)

- The land-records-portal source stays separate. The demo-target Compose profile builds and runs it as `demo-portal` from the sibling portal repo path, with the production standalone server bound to `0.0.0.0:3010` inside the Compose network.
- `localhost:8089` returned HTTP 200 for the demo-target home request.
- Fresh SQLi marker `SMOKE002945` against `/records/search` returned HTTP 403.
- Demo-target audit log path: `logs/modsecurity/demo-target/modsec_audit.jsonl`.
- Demo-target transaction: `178249138618.813428`, host `localhost:8089`, request path `/records/search`.
- `demo-target-bridge` posted `status=200` for transaction `178249138618.813428`.
- Backend lookup returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, and `crs_score=15`.
- `localhost:8088` SQLi smoke still returned HTTP 403 after the demo-target bridge fix.

### Historical checks through 2026-07-05

- Backend tests: `.venv\Scripts\python.exe -m pytest -q` → **528 passed**
- Frontend lint: `cd frontend && npm run lint` → **passed**
- Frontend types: `cd frontend && npm run typecheck` → **passed**
- Focused frontend BFF tests:
  - `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **passed**
- Full frontend suite:
  - `cd frontend && npx vitest run` → **333 passed**
- Frontend build:
  - `cd frontend && npm run build` → **passed**
- PR #79 GitHub CI:
  - First Ubuntu 24.04 / Node `24.18.0` frontend attempt aborted during `npx vitest run` with native `Napi::Error` exit 134.
  - PR #81 replaced accidental partial/native Argon2 imports in auth and provisioning control-flow tests with pure mocks. Real Argon2id coverage remains in `password-hash.test.ts`.
- The full frontend CI job passed twice after the repair. Vitest remains on `threads`; package scripts, CI workflow, and production auth/Argon2id code are unchanged.

### PR #83 remediation state (2026-07-13)

- Additive migration head: `20260712_000020`, after deployed revision
  `20260710_000014`.
- Database-authoritative MFA/recovery, recent step-up, protected notification
  payloads, durable worker accounting/readiness, required authentication E2E
  CI, and restricted break glass are implemented. Availability flags fail
  closed when absent and are evaluated at request time.
- Disposable PostgreSQL validation passed: 650 full backend tests, 107
  integration tests, 37 migration tests, and downgrade/re-upgrade of the two
  final security revisions.
- Frontend lint, typecheck, Vitest, production build, and remote authentication
  E2E are passing. Local-only browser session behavior is deferred if it
  reappears; current operator status is maintained in
  `docs/project-ops/STATUS.md`.
- Active credential-equivalent notification payloads use versioned AES-GCM
  envelopes and terminal rows are scrubbed. Hosted Supabase is migrated through
  `20260712_000020`, the public app is active through Cloudflare Tunnel,
  `target.cybertracesystems.com` is protected by Cloudflare Access, and live
  Resend delivery is verified.

### Backend

- App entrypoint: `web_app.presentation.app:create_app`
- Current API routes:
  - Protected by backend bearer auth:
    - `POST /api/predict`
    - `POST /api/triage`
    - `GET /api/alerts`
    - `GET /api/alerts/stream`
    - `GET /api/alerts/{id}`
    - `PATCH /api/alerts/{id}/triage`
    - `GET /api/stats`
    - `GET /api/ml-health`
  - Internal bearer-token protected backend endpoints:
    - `POST /api/feedback`
  - Public backend endpoints:
    - `GET /health`
    - `GET /api/health`
- Model loading is handled by `web_app/services/model_service.py`
- WAF ingest inference is gated by `web_app/application/inference_queue.py`,
  a bounded in-process `asyncio.Queue`; callers still await the completed
  `TriageIngestResponse`
- In production mode, the backend requires an explicit `MODEL_REGISTRY_PATH`
- In development or testing, missing model artifacts fall back to a mock model service with a warning
- Internal backend routes and WAF lookup are protected by bearer-token auth
  using `API_SECRET_KEY`; WAF submission uses the distinct
  `WAF_INGEST_API_KEY` and rejects the general internal key
- New WAF events canonicalize source IPs, persist explicit provenance and
  ingest-time verification status, and use a deterministic factual fingerprint
  for duplicate integrity. Historical rows retain `LEGACY_UNKNOWN` metadata
  and a null fingerprint. The fingerprint excludes derived verification status
  and generated receive time.
- Request context middleware preserves or generates safe request IDs, supports W3C version-00 `traceparent`, and returns `X-Request-ID` on handled and generic unhandled `500` responses
- Structured JSON logs cover request completion/failure, WAF ingest outcomes, direct prediction outcomes, and bridge operational/configuration events; sensitive keyed fields are recursively redacted with case/separator-insensitive key matching and cycle/depth bounds
- A finalized visible alert publishes a coalesced `alert.created` signal through
  `web_app/application/alert_events.py`. Publication happens after repository
  commit; duplicate completed ingests do not republish. The in-process
  broadcaster is intentionally limited to the current single-backend-process
  runtime and is not durable replay or multi-instance fan-out.

### Frontend

- Dashboard routes exist under `frontend/app/(dashboard)/`
- Authentication is implemented with Auth.js credentials auth
- Supabase `auth_accounts` login, approved Argon2id PHC parameter verification, and DB-backed role/`authz_version`/`mfa_required` freshness checks are implemented in repo; hosted account invitation, setup, password, TOTP, and MFA login flows are verified
- Client requirements call for secure login, RBAC, strong account security, and 2FA; the DB-backed Auth.js flow includes encrypted TOTP enrollment, replay-safe MFA completion, recovery-only claims, and password recovery behind fail-closed server-side availability flags
- Alerts UI role affordances are implemented in the dashboard: viewers are read-only, analysts keep triage controls, and admins keep the full control set
- `frontend/app/(dashboard)/layout.tsx` redirects unauthenticated dashboard requests to `/login`
- `frontend/proxy.ts` additionally matches `/dashboard`, `/alerts`, and `/ml-health`
- Local `next start` validation requires `AUTH_TRUST_HOST=true` in `frontend/.env.local`
- Current BFF status in the working tree:
  - `frontend/lib/bff-client.ts` is the shared server-only BFF client
  - `frontend/app/api/alerts/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/alerts/stream/route.ts` authenticates and streams the FastAPI SSE response with private/no-store, no-transform, no-buffer, and nosniff response controls
  - `frontend/app/api/alerts/[id]/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/alerts/[id]/triage/route.ts` handles PATCH triage
  - `frontend/app/api/stats/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/ml-health/route.ts` proxies to FastAPI in non-mock mode
  - `USE_MOCK_API` is the single centralized server-only mock toggle (currently **false**)
  - all seven handlers await the central DB-backed permission guard before downstream work
  - one dashboard-level `AlertStreamSync` connection invalidates the existing
    alert and stats TanStack Query families on `alert.created` and `open`; the
    latter provides canonical REST catch-up after native EventSource reconnect
  - backend streams recycle after five minutes so reconnect re-runs the BFF's
    DB-backed account and permission checks; backend connection establishment
    is capped at ten seconds and upstream redirects are rejected
  - canonical alert contract values live in `frontend/features/alerts/contract.ts`:
    - `prediction`: `SQL Injection`, `Code Injection`, `Other Attacks`, `Normal`
    - `confidence_level`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`
    - `action_taken`: `BLOCKED`, `THROTTLED`, `ALLOWED`
  - persisted-alert confidence distributions and styling use backend-emitted `confidence_level`, not raw-score reclassification
  - enforcement-policy counts exclude `Normal`; Normal predictions remain `ALLOWED` for every valid confidence tier
  - confidence-tier badges always render the canonical tier and do not substitute `Benign`

### Database

- Runtime database access uses async SQLAlchemy
- Tests currently use SQLite
- Isolated local work can still use SQLite if desired
- The app runtime is wired to a Supabase-backed PostgreSQL boundary
- Supabase policy and operational hardening steps are still partly external to repo automation

## Present But Not Yet The Primary Runtime

- Root `docker-compose.yml`
- Dockerfiles for frontend and backend
- Compose ModSecurity/OWASP CRS proof path on `localhost:8088` behind the
  opt-in `technical-waf` profile
- Internal WAF ingest endpoint, WAF ingest use case, JSONL bridge, replay harness, and demo-target bridge. The demo-target profile is optional for normal startup and required for the final realistic WAF demonstration.
- Hosted source correlation is verified through operator home/mobile evidence:
  distinct public sources matched ModSecurity, bridge, FastAPI, PostgreSQL, and
  dashboard records, and forged-header resistance passed. Hosted identity
  verification is still Partial: Workers, Pseudo IPv4, origin isolation, and
  independent immediate-peer confirmation remain open. Hosted mode remains
  `unverified`.

## Not Yet Implemented

- Production-grade ModSecurity-fronted deployment
- Redis-backed enforcement and review queue behavior; use only if shared runtime state is required. PR4 now has a bounded, database-backed shadow recommendation path without Redis.
- Richer backend-native dashboard stats and ML health payloads beyond the current BFF normalization layer
- Notification-worker failure/retry operational testing, MFA flag-semantics audit, Auth.js upgrade, and passkeys/WebAuthn
- Wazuh export-only integration

## Important Truths To Keep Straight

- The active model artifact path is `ml_model/model_registry/`.
- The repo already has more backend startup work and frontend structure than older docs suggested.
- The repo has a verified local WAF ingest proof. It is not a production-grade WAF deployment.
- Stale `PROCESSING` reservations are automatically reclaimed via lease expiry (`lease_expires_at`). A later request can claim ownership when the lease has expired.
- `action_taken` remains the existing alert metadata (`BLOCKED`, `THROTTLED`, or `ALLOWED`). PR4 `recommended_action` is a versioned, expiring future intent; `actual_decision` is always `ALLOW` and is not proof of live block/throttle enforcement.
- Current confidence tiers are LOW, MEDIUM, HIGH, and CRITICAL. CRITICAL is a confidence tier for model confidence `>=90%`, not business/security severity. This contract change required no retraining, recalibration, or model artifact update; historical rows are not retroactively reclassified, and legacy `severity` remains a query compatibility alias.
- Frontend policy displays keep prediction, confidence tier, and `action_taken` separate: confidence tier alone does not imply an action, and `CRITICAL` is never an `action_taken` value.
- Bridge follow-mode retry handling belongs to the local WAF ingest proof path, not to production audit-log rotation or retention.
