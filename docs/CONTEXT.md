# Project Context

Updated: 2026-03-24  
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

This is not yet the finished Docker/ModSecurity/Redis local stack. The codebase now includes Dockerfiles and a `docker-compose.yml` for local smoke work, but the browser-facing runtime path is still the Next.js BFF path, not a completed ModSecurity-fronted deployment.

## Verified Status (2026-03-24)

### Checks run on 2026-03-24

- Backend tests: `python3 -m pytest -q` → **294 passed**
- Frontend lint: `cd frontend && npm run lint` → **passed**
- Frontend types: `cd frontend && npm run typecheck` → **passed**
- Focused frontend BFF tests:
  - `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **74 passed**
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
    - `POST /api/internal/waf-events`
    - `GET /api/alerts`
    - `GET /api/alerts/{id}`
    - `PATCH /api/alerts/{id}/triage`
    - `GET /api/stats`
    - `GET /api/ml-health`
  - Public backend endpoints:
    - `POST /api/feedback`
    - `GET /health`
    - `GET /api/health`
- Model loading is handled by `web_app/services/model_service.py`
- In production mode, the backend requires an explicit `MODEL_REGISTRY_PATH`
- In development or testing, missing model artifacts fall back to a mock model service with a warning
- Internal backend routes are protected by bearer-token auth using `API_SECRET_KEY`
- WAF ingress now uses a dedicated internal route (`POST /api/internal/waf-events`) and delegates to the existing triage policy path.

### Frontend

- Dashboard routes exist under `frontend/app/(dashboard)/`
- Authentication is implemented with Auth.js credentials auth
- Demo login uses a password-only credentials flow
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
  - alert normalization includes optional WAF evidence metadata fields (`ingest_source`, `matched_rule_messages`, `matched_rule_tags`)

### Database

- Runtime database access uses async SQLAlchemy
- Tests currently use SQLite
- Isolated local work can still use SQLite if desired
- The app runtime is wired to a Supabase-backed PostgreSQL boundary
- Supabase policy and operational hardening steps are still partly external to repo automation

## Present But Not Yet The Primary Runtime

- Root `docker-compose.yml`
- Dockerfiles for frontend and backend
- Internal Compose ModSecurity wiring that proxies to `backend`
- Compose bridge service and fixture path for WAF ingest smoke verification (`scripts/waf_audit_bridge.py`)

## Not Yet Implemented

- ModSecurity as the browser-facing runtime boundary
- Redis-backed enforcement and review queue behavior
- Richer backend-native dashboard stats and ML health payloads beyond the current BFF normalization layer

## Important Truths To Keep Straight

- The active model artifact path is `ml_model/model_registry/`.
- The repo already has more backend startup work and frontend structure than older docs suggested.
- The repo is not yet an end-to-end WAF deployment. It is a documented application codebase with ML assets, working BFF-to-FastAPI wiring, a live Supabase-backed data boundary, and a local Docker smoke path.
- Stale `PROCESSING` reservations are automatically reclaimed via lease expiry (`lease_expires_at`). A later request can claim ownership when the lease has expired.
