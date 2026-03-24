# Project Ops Status

**Scope:** operator-only session status  
**Defense:** May 2026  
**Last updated:** 2026-03-24

---

## Current Verified Repo State

- Active branch baseline: `master`
- Python runtime target: `3.14+`
- Local venv currently recreated and verified on: `Python 3.14.3`
- Frontend runtime: Next.js `16.2.1`, React `19.2.4`, TypeScript `5.9`, Zod `4.3.6`
- Backend runtime: FastAPI `0.135.1`, Pydantic `2.12.5`, SQLAlchemy `2.0.48` (async)
- Model/runtime artifacts boundary: `ml_model/model_registry/`
- Data/runtime boundary: Supabase-backed PostgreSQL for app runtime, SQLite for tests

### Latest local verification results

- Backend dependency integrity: `.venv\Scripts\python.exe -m pip check` → **pass**
- Backend tests: `python3 -m pytest -q` → **294 passed**
- App startup sanity: `.venv\Scripts\python.exe -c "from web_app.presentation.app import create_app; print(bool(create_app()))"` → **True**
- Frontend lint: `cd frontend && npm run lint` → **pass**
- Frontend typecheck: `cd frontend && npm run typecheck` → **pass**
- Frontend BFF-focused tests:
  - `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **74 passed**
- Frontend full suite: `cd frontend && npx vitest run` → **122 passed**
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
  - `POST /api/internal/waf-events`
  - `GET /health`
  - `GET /api/health`
- Reservation-first triage flow is active (`PROCESSING` placeholders, lease reclaim support, winner/loser behavior).
- WAF ingest vertical slice is active: bridge payload -> internal route -> ML triage -> `traffic_logs` persistence.
- `PROCESSING` rows are excluded from normal alerts and stats reads.
- Frontend boundary remains:
  - `Browser -> Next.js route handlers/BFF -> FastAPI`
- Route protection and proxy entrypoint:
  - Auth checks are enforced in BFF handlers.
  - Next.js edge entrypoint uses `frontend/proxy.ts`.
  - Local `next start` validation requires `AUTH_TRUST_HOST=true` in `frontend/.env.local`.

---

## Important Notes For Operators

- CI may show four checks on branch updates because both `push` and `pull_request` workflows run for frontend and backend.
- `requirements.train.txt` is laptop/training-only and should not be treated as required for CI/backend runtime verification.
- Supabase is now part of the current runtime truth. Do not document it as merely planned.

---

## Open Gaps (Current, Not Historical)

- Docker Compose includes a bridge service for WAF ingest smoke flow, but ModSecurity is not yet the browser-facing runtime boundary.
- Redis-backed enforcement and queue behavior is still not implemented in the repo runtime.
- Some Supabase policy and operational hardening steps remain outside automated repo verification/export.

---

## Source-of-Truth Docs

- Implementation snapshot: `docs/CONTEXT.md`
- Architecture boundaries: `docs/architecture.md`
- Local setup: `docs/SETUP.md`
- Detailed current-state snapshot: `docs/CURRENT_SYSTEM_STATE.md`
- Operator checklist: `docs/project-ops/LIVING_CHECKLIST.md`
