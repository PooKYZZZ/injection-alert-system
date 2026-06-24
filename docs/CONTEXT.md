# Project Context

Updated: 2026-06-23
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

This is not yet a production Docker/Redis deployment. The codebase includes Dockerfiles and a `docker-compose.yml`; the verified WAF proof path uses `localhost:8088`, while the dashboard browser path remains the Next.js BFF path.

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
- Remaining TODO: bridge follow mode once logged transient `OSError: [Errno 5] Input/output error` at `readline()`; the container restarted and posted successfully afterward.

### Checks run on 2026-03-23

- Backend tests: `.venv\Scripts\python.exe -m pytest -q` → **264 passed**
- Frontend lint: `cd frontend && npm run lint` → **passed**
- Frontend types: `cd frontend && npm run typecheck` → **passed**
- Focused frontend BFF tests:
  - `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **passed**
- Full frontend suite:
  - `cd frontend && npx vitest run` → **122 passed**
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
    - `action_taken`: `BLOCKED`, `THROTTLED`, `ALLOWED`

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
- Internal WAF ingest endpoint, WAF ingest use case, JSONL bridge, and replay harness

## Not Yet Implemented

- Production-grade ModSecurity-fronted deployment
- Bridge follow-mode resilience for transient `readline()` `OSError`
- Bounded inference queue and queue health visibility
- Redis-backed enforcement and review queue behavior; use only if shared runtime state is required
- Richer backend-native dashboard stats and ML health payloads beyond the current BFF normalization layer
- Client-required real user accounts / secure login replacement for demo auth
- Client-required Admin/Analyst RBAC
- Client-required 2FA
- Client-required email notification after detection
- Client-required real-time/SSE dashboard alerts
- Client-standard `CRITICAL >=90%` confidence tier
- Wazuh export-only integration
- Backup/restore, migration rollback, and archive/hide retention runbooks

## Important Truths To Keep Straight

- The active model artifact path is `ml_model/model_registry/`.
- The repo already has more backend startup work and frontend structure than older docs suggested.
- The repo has a verified local WAF ingest proof. It is not a production-grade WAF deployment.
- Stale `PROCESSING` reservations are automatically reclaimed via lease expiry (`lease_expires_at`). A later request can claim ownership when the lease has expired.
- `BLOCKED`, `THROTTLED`, and `ALLOWED` are currently recorded action values, not proof of live request-path enforcement.
- Current confidence tiers are LOW/MEDIUM/HIGH; the client-required `CRITICAL >=90%` tier is planned.
