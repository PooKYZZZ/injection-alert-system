# Project Ops Status

**Scope:** operator-only session status  
**Defense:** May 2026  
**Last updated:** 2026-03-15

---

## Current verified repo state

- Backend tests currently pass: `82 passed`
- Frontend typecheck currently passes: `npm run typecheck`
- Backend routes currently implemented:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `GET /api/stats`
  - `GET /api/ml-health`
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`
- Triage ingest is reservation-first on `transaction_id`:
  - placeholder row inserted with `status="PROCESSING"`
  - winner determined by `INSERT ... ON CONFLICT DO NOTHING` rowcount
  - winner completes the row to `status="COMPLETED"` after inference
  - loser returns existing completed data or a retriable response while processing is in flight
- `PROCESSING` placeholder rows are excluded from normal alerts and stats reads
- Docker Compose, runnable ModSecurity wiring, and full Supabase or Redis integration are not in the repo yet

## Open implementation gaps

- The reservation-first triage flow now depends on the applied DB migration for:
  - `created_at`
  - `status`
  - nullable result columns on placeholder rows
- The backend still uses async SQLAlchemy locally and is not fully wired to live Supabase behavior
- The frontend still has mock-backed route handlers that need real upstream wiring
- Data scripts still hardcode workstation-specific paths

## Operator notes

- Canonical implementation docs live in:
  - `docs/CONTEXT.md`
  - `docs/architecture.md`
  - `docs/SETUP.md`
- This file is intentionally shorter than the old root status file and should stay focused on current operator truth, not future planning prose.
