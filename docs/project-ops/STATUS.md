# Project Ops Status

**Scope:** operator-only session status  
**Defense:** May 2026  
**Last updated:** 2026-03-14

---

## Current verified repo state

- Backend tests currently pass: `50 passed`
- Frontend typecheck currently passes: `npm run typecheck`
- Backend routes currently implemented:
  - `POST /api/predict`
  - `GET /api/alerts`
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`
- The dashboard exists, but the BFF is still mixed:
  - `stats` can proxy to FastAPI
  - `alerts`, `alert detail`, and `ml-health` are still mock-first or stubbed
- Docker Compose, runnable ModSecurity wiring, and full Supabase or Redis integration are not in the repo yet

## Open implementation gaps

- Backend routes still missing for:
  - `GET /api/stats`
  - `GET /api/ml-health`
  - `GET /api/alerts/{id}`
- The backend still uses async SQLAlchemy locally and is not fully wired to live Supabase behavior
- The frontend still has mock-backed route handlers that need real upstream wiring
- Data scripts still hardcode workstation-specific paths

## Operator notes

- Canonical implementation docs live in:
  - `docs/CONTEXT.md`
  - `docs/architecture.md`
  - `docs/SETUP.md`
- This file is intentionally shorter than the old root status file and should stay focused on current operator truth, not future planning prose.
