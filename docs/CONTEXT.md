# Project Context

Updated: 2026-03-23  
Defense: May 2026  
Client: LARES (Land Registration Systems, Inc.)

## What This Repo Is Today

The repository currently contains:

- A FastAPI backend built around a Clean Architecture split:
  - `domain -> application -> infrastructure -> presentation`
- A Next.js 16 dashboard using the App Router, Auth.js credentials auth, route handlers, Zod, TanStack Query, and Zustand
- ML lifecycle assets under `ml_model/`, including staged transformer artifacts and an inference wrapper
- Migration scaffolding and three migrations under `migrations/`
- Documentation and academic deliverables under `docs/`

This is not yet the finished 3-container PD1 demo stack. The codebase is still in a local integration and documentation-hardening phase.

## Verified Status (2026-03-22)

### Checks run on 2026-03-22

- Backend tests: `.venv\Scripts\python.exe -m pytest -q` → **259 passed**
- Frontend types: `frontend\npm run typecheck` → **passed**
- Frontend lint: `cd frontend && npm run lint` → **passed**
- Focused frontend BFF tests:
  - `cd frontend && npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **passed**
- Full frontend suite:
  - `cd frontend && npx vitest run` → **107 passed**

### Cloud baseline

Latest pushed work on `origin/master` includes:

- `#39` reservation-first `POST /api/triage` ingest
- `#38` shared internal bearer-token auth for internal API routes
- `#37` backend read APIs for alerts, alert detail, stats, and ML health

### Backend

- App entrypoint: `web_app.presentation.app:create_app`
- Current API routes:
  - Protected by backend bearer auth:
    - `POST /api/predict`
    - `POST /api/triage`
    - `GET /api/alerts`
    - `GET /api/alerts/{id}`
    - `PATCH /api/alerts/{id}/triage` (NEW)
    - `GET /api/stats` (window filtering)
    - `GET /api/ml-health` (eval metadata optional)
  - Public backend endpoints:
    - `POST /api/feedback`
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
- `frontend/app/(dashboard)/layout.tsx` redirects unauthenticated dashboard requests to `/login`
- `frontend/middleware.ts` additionally matches `/dashboard`, `/alerts`, and `/ml-health`
- Current BFF status in the working tree:
  - `frontend/lib/bff-client.ts` is the shared server-only BFF client
  - `frontend/app/api/alerts/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/alerts/[id]/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/alerts/[id]/triage/route.ts` handles PATCH triage (NEW)
  - `frontend/app/api/stats/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/ml-health/route.ts` proxies to FastAPI in non-mock mode
  - `USE_MOCK_API` is the single centralized server-only mock toggle (currently **false** - hitting real FastAPI)
  - all five handlers apply the same existing session auth pattern via `auth()`
  - canonical alert contract values live in `frontend/features/alerts/contract.ts`:
    - `prediction`: `SQL Injection`, `Code Injection`, `Other Attacks`, `Normal`
    - `action_taken`: `BLOCKED`, `THROTTLED`, `ALLOWED`

### Database

- Runtime database access uses async SQLAlchemy
- Local SQLite DB at `injection_alerts.db`
- Current row counts: 18 total, BLOCKED=12, THROTTLED=3, ALLOWED=3
- Tests currently use SQLite
- Supabase remains the target production database boundary, but the repo is not yet wired to a live Supabase deployment path

### 2026-03-20 Audit Findings

- BFF layer verified: auth boundary correct, CalibrationBin schema correct, multi-select params correct
- Hardcoded values fixed:
  - Dashboard: removed `'↑ +3 vs prev 6h'`, `'50–80% confidence'`, `'↓ Model stable'`
  - ML Health: changed `value="Temp-scaled"` to `value="—"`
- Verified: `/api/alerts` returns persisted records correctly

## Not Yet Implemented

- Root `docker-compose.yml`
- Dockerfiles for frontend and backend
- Runnable ModSecurity or CRS config under the repo
- Redis-backed enforcement and review queue behavior
- Confirmed Supabase RLS enforcement in runtime code
- Richer backend-native dashboard stats and ML health payloads beyond the current BFF normalization layer

## Important Truths To Keep Straight

- The active model artifact path is `ml_model/model_registry/`.
- The repo already has more backend startup work and frontend structure than older docs suggested.
- The repo is not yet an end-to-end WAF deployment. It is a documented application codebase with ML assets and working BFF-to-FastAPI wiring.
- Stale `PROCESSING` reservations are automatically reclaimed via lease expiry (`lease_expires_at`). A later request can claim ownership when the lease has expired.

- Full audit findings in `docs/project-ops/DATA_AUDIT.md`.
