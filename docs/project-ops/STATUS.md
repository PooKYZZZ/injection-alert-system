# Project Ops Status

**Scope:** operator-only session status  
**Defense:** May 2026  
**Last updated:** 2026-03-15

---

## Current verified repo state

- Remote `origin/master` currently includes:
  - `#39` `fix: add reservation-first triage ingest`
  - `#38` `feat: implement internal authentication with bearer token for API endpoints`
  - `#37` `Codex/feat/backend read api batch`
- Backend tests currently pass locally: `84 passed`
- Frontend typecheck currently passes locally: `npm run typecheck`
- Focused frontend BFF tests currently pass locally:
  - `cd frontend && npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts`
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
- Frontend BFF current workspace state:
  - all four route handlers are wired through `frontend/lib/bff-client.ts`
  - `USE_MOCK_API` is the single centralized server-only mock toggle
  - missing `FASTAPI_BASE_URL` or `INTERNAL_API_KEY` in non-mock mode returns structured `BFF_MISCONFIGURED`
- Docker Compose, runnable ModSecurity wiring, and full Supabase or Redis integration are not in the repo yet

## Open implementation gaps

- The reservation-first triage flow still depends on applied DB migrations for:
  - `created_at`
  - `status`
  - nullable result columns on placeholder rows
- The backend still uses async SQLAlchemy locally and is not fully wired to live Supabase behavior
- Some docs and prompts still need cleanup to remove stale verification commands and old partial-mock descriptions
- Data scripts still hardcode workstation-specific paths
- Dashboard stats and ML health still rely on some BFF-side normalization because backend payloads are thinner than the frontend dashboard contract

## Operator notes

- Canonical implementation docs live in:
  - `docs/CONTEXT.md`
  - `docs/architecture.md`
  - `docs/SETUP.md`
- Treat cloud `origin/master` as the pushed baseline and this working tree as the latest local integration state.
- This file is intentionally shorter than the old root status file and should stay focused on current operator truth, not future planning prose.
