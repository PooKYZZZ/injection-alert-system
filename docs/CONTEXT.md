# Project Context

Updated: 2026-06-29
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
- Targeted checks passed: bridge tests `34 passed`, WAF ingest route tests `8 passed`, WAF ingest use-case tests `4 passed`, and `docker compose config --quiet`.
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

### Checks run through 2026-06-30

- Backend tests: `.venv\Scripts\python.exe -m pytest -q` → **447 passed**
- Frontend lint: `cd frontend && npm run lint` → **passed**
- Frontend types: `cd frontend && npm run typecheck` → **passed**
- Focused frontend BFF tests:
  - `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **passed**
- Full frontend suite:
  - `cd frontend && npx vitest run --pool=threads` → **206 passed**
- Frontend build:
  - `cd frontend && npm run build` → **passed**

### Backend

- App entrypoint: `web_app.presentation.app:create_app`
- Current API routes:
  - Protected by backend bearer auth:
    - `POST /api/predict`
    - `POST /api/triage`
    - `GET /api/alerts`
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
- Internal backend routes are protected by bearer-token auth using `API_SECRET_KEY`

### Frontend

- Dashboard routes exist under `frontend/app/(dashboard)/`
- Authentication is implemented with Auth.js credentials auth
- Demo login uses a password-only credentials flow
- Client requirements call for real user access management with secure login, RBAC, strong account security, and 2FA; the current demo password flow is not the final requirement state
- `frontend/app/(dashboard)/layout.tsx` redirects unauthenticated dashboard requests to `/login`
- `frontend/proxy.ts` additionally matches `/dashboard`, `/alerts`, and `/ml-health`
- Local `next start` validation requires `AUTH_TRUST_HOST=true` in `frontend/.env.local`
- Current BFF status in the working tree:
  - `frontend/lib/bff-client.ts` is the shared server-only BFF client
  - `frontend/app/api/alerts/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/alerts/[id]/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/alerts/[id]/triage/route.ts` handles PATCH triage
  - `frontend/app/api/stats/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/ml-health/route.ts` proxies to FastAPI in non-mock mode
  - `USE_MOCK_API` is the single centralized server-only mock toggle (currently **false**)
  - all five handlers apply the same existing session auth pattern via `auth()`
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
- Compose ModSecurity/OWASP CRS proof path on `localhost:8088`
- Internal WAF ingest endpoint, WAF ingest use case, JSONL bridge, replay harness, and demo-target bridge. The demo-target profile is optional for normal startup and required for the final realistic WAF demonstration.

## Not Yet Implemented

- Production-grade ModSecurity-fronted deployment
- Redis-backed enforcement and review queue behavior; use only if shared runtime state is required
- Richer backend-native dashboard stats and ML health payloads beyond the current BFF normalization layer
- Client-required real user accounts / secure login replacement for demo auth
- Client-required Admin/Analyst RBAC
- Client-required 2FA
- Client-required email notification after detection
- Client-required real-time/SSE dashboard alerts
- Wazuh export-only integration
- Backup/restore, migration rollback, and archive/hide retention runbooks

## Important Truths To Keep Straight

- The active model artifact path is `ml_model/model_registry/`.
- The repo already has more backend startup work and frontend structure than older docs suggested.
- The repo has a verified local WAF ingest proof. It is not a production-grade WAF deployment.
- Stale `PROCESSING` reservations are automatically reclaimed via lease expiry (`lease_expires_at`). A later request can claim ownership when the lease has expired.
- `BLOCKED`, `THROTTLED`, and `ALLOWED` are currently recorded action values, not proof of live request-path enforcement.
- Current confidence tiers are LOW, MEDIUM, HIGH, and CRITICAL. CRITICAL is a confidence tier for model confidence `>=90%`, not business/security severity. This contract change required no retraining, recalibration, or model artifact update; historical rows are not retroactively reclassified, and legacy `severity` remains a query compatibility alias.
- Frontend policy displays keep prediction, confidence tier, and `action_taken` separate: confidence tier alone does not imply an action, and `CRITICAL` is never an `action_taken` value.
- Bridge follow-mode retry handling belongs to the local WAF ingest proof path, not to production audit-log rotation or retention.
