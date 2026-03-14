# Project Context

Updated: 2026-03-14  
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

### Checks run on 2026-03-14

- Backend tests: `.venv\Scripts\python.exe -m pytest -q` -> `44 passed`
- Frontend types: `frontend\npm run typecheck` -> passed

### Backend

- App entrypoint: `web_app.presentation.app:create_app`
- Current API routes:
  - `POST /api/predict`
  - `GET /api/alerts`
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`
- Model loading is handled by `web_app/services/model_service.py`
- In production mode, the backend requires an explicit `MODEL_REGISTRY_PATH`
- In development or testing, missing model artifacts fall back to a mock model service with a warning

### Frontend

- Dashboard routes exist under `frontend/app/(dashboard)/`
- Authentication is implemented with Auth.js credentials auth
- Demo login uses a password-only credentials flow
- Current BFF status:
  - `frontend/app/api/stats/route.ts` can proxy to FastAPI
  - `frontend/app/api/alerts/route.ts` still returns mock data
  - `frontend/app/api/alerts/[id]/route.ts` is mock-first and returns `501` if mocks are disabled
  - `frontend/app/api/ml-health/route.ts` still returns mock data

### Database

- Runtime database access uses async SQLAlchemy
- The backend supports PostgreSQL and SQLite connection strings
- Tests currently use SQLite
- Supabase remains the target production database boundary, but the repo is not yet wired to a live Supabase deployment path

## Not Yet Implemented

- Root `docker-compose.yml`
- Dockerfiles for frontend and backend
- Runnable ModSecurity or CRS config under the repo
- Backend routes for:
  - `GET /api/stats`
  - `GET /api/ml-health`
  - `GET /api/alerts/{id}`
- Full BFF wiring for alerts, alert detail, and ML health
- Redis-backed enforcement and review queue behavior
- Confirmed Supabase RLS enforcement in runtime code

## Important Truths To Keep Straight

- The active model artifact path is `ml_model/model_registry/`.
- The repo already has more backend startup work and frontend structure than the older docs suggested.
- The repo is not yet an end-to-end WAF deployment. It is a documented application codebase with ML assets and partial proxy wiring.
