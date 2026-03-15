# Project Context

Updated: 2026-03-15  
Defense: May 2026  
Client: LARES (Land Registration Systems, Inc.)

## What This Repo Is Today

The repository currently contains:

- A FastAPI backend built around a Clean Architecture split:
  - `domain -> application -> infrastructure -> presentation`
- A Next.js 15 dashboard using the App Router, Auth.js credentials auth, route handlers, Zod, TanStack Query, and Zustand
- ML lifecycle assets under `ml_model/`, including staged transformer artifacts and an inference wrapper
- Migration scaffolding and one migration under `migrations/`
- Documentation and academic deliverables under `docs/`

This is not yet the finished 3-container PD1 demo stack. The codebase is still in a local integration and documentation-hardening phase.

## Verified Status

### Checks run on 2026-03-15

- Backend tests: `.venv\Scripts\python.exe -m pytest -q` -> `84 passed`
- Frontend types: `frontend\npm run typecheck` -> passed
- Focused frontend BFF tests:
  - `cd frontend && npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts` -> passed

### Cloud baseline

Latest pushed work on `origin/master` includes:

- `#39` reservation-first `POST /api/triage` ingest
- `#38` shared internal bearer-token auth for internal API routes
- `#37` backend read APIs for alerts, alert detail, stats, and ML health

### Backend

- App entrypoint: `web_app.presentation.app:create_app`
- Current API routes:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `GET /api/stats`
  - `GET /api/ml-health`
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
- Current BFF status in the working tree:
  - `frontend/lib/bff-client.ts` is the shared server-only BFF client
  - `frontend/app/api/alerts/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/alerts/[id]/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/stats/route.ts` proxies to FastAPI in non-mock mode
  - `frontend/app/api/ml-health/route.ts` proxies to FastAPI in non-mock mode
  - `USE_MOCK_API` is the single centralized server-only mock toggle
  - all four handlers apply the same existing session auth pattern via `auth()`

### Database

- Runtime database access uses async SQLAlchemy
- The backend supports PostgreSQL and SQLite connection strings
- Tests currently use SQLite
- Supabase remains the target production database boundary, but the repo is not yet wired to a live Supabase deployment path

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
