# Project Ops Status

**Scope:** operator-only session status  
**Defense:** May 2026  
**Last updated:** 2026-03-23

---

## Current Verified Repo State

- Active integration branch used for final checks: `frontend-adaptation`
- Python runtime target: `3.14+`
- Local venv currently recreated and verified on: `Python 3.14.3`
- Frontend runtime: Next.js `16.2.1`, React `19.2.4`, TypeScript `5.9`, Zod `4.3.6`
- Backend runtime: FastAPI `0.135.1`, Pydantic `2.12.5`, SQLAlchemy `2.0.48` (async)
- Model/runtime artifacts boundary: `ml_model/model_registry/`

### Latest local verification results

- Backend dependency integrity: `.venv\Scripts\python.exe -m pip check` → **pass**
- Backend tests: `.venv\Scripts\python.exe -m pytest -q` → **259 passed**
- App startup sanity: `.venv\Scripts\python.exe -c "from web_app.presentation.app import create_app; print(bool(create_app()))"` → **True**
- Frontend typecheck: `cd frontend && npm run typecheck` → **pass**
- Frontend BFF-focused tests:
  - `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **69 passed**
- Frontend production build: `cd frontend && npm run build` → **pass**

### Current API/BFF state

- Implemented backend routes:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `PATCH /api/alerts/{id}/triage`
  - `GET /api/stats`
  - `GET /api/ml-health`
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`
- Reservation-first triage flow is active (`PROCESSING` placeholders, lease reclaim support, winner/loser behavior).
- `PROCESSING` rows are excluded from normal alerts and stats reads.
- Frontend boundary remains:
  - `Browser -> Next.js route handlers/BFF -> FastAPI`
- Route protection and proxy entrypoint:
  - Auth checks are enforced in BFF handlers.
  - Next.js edge entrypoint now uses `frontend/proxy.ts` (not `middleware.ts`).

---

## Important Notes For Operators

- CI may show four checks on branch updates because both `push` and `pull_request` workflows run for frontend and backend.
- The backend CI failure on Python 3.14 (`api_secret_key` required) is fixed by allowing an empty default in `web_app/config.py`, aligned with existing auth-bypass behavior in development-only scenarios.
- `requirements.train.txt` is laptop/training-only and should not be treated as required for CI/backend runtime verification.

---

## Open Gaps (Current, Not Historical)

- Docker Compose + runnable ModSecurity integration is still not implemented.
- Live Supabase operational hardening steps (RLS policy operations) remain outside automated repo verification.
- Some legacy planning docs under `docs/project-ops/` were stale and have been replaced by the current compact plan/task docs.

---

## Source-of-Truth Docs

- Implementation snapshot: `docs/CONTEXT.md`
- Architecture boundaries: `docs/architecture.md`
- Local setup: `docs/SETUP.md`
- Operator plan: `docs/project-ops/IMPLEMENTATION_PLAN.md`
- Operator task list: `docs/project-ops/TASKS.md`
