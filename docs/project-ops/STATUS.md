# Project Ops Status

**Scope:** operator-only session status  
**Defense:** May 2026  
**Last updated:** 2026-03-22

---

## Current verified repo state

- Remote `origin/master` currently includes:
  - `#39` `fix: add reservation-first triage ingest`
  - `#38` `feat: implement internal authentication with bearer token for API endpoints`
  - `#37` `Codex/feat/backend read api batch`
- Backend tests currently pass locally: `256 passed`
- Frontend typecheck currently passes locally: `npm run typecheck`
- Frontend tests currently pass locally: `102 passed`
- All frontend BFF tests pass:
  - `cd frontend && npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts`
- Backend routes currently implemented:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `PATCH /api/alerts/{id}/triage`
  - `GET /api/stats` (with window=1h|6h|24h|7d filtering, activity buckets, top source IPs, top targeted paths, attack distribution)
  - `GET /api/ml-health` (with eval metadata: macro_f1, ece, per_class_f1, calibration_bins, prediction_distribution)
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`
- Triage ingest is reservation-first on `transaction_id`:
  - placeholder row inserted with `status="PROCESSING"`
  - winner determined by atomic claim-or-reclaim behavior on the reservation row
  - expired leases can be reclaimed safely by a later request
  - current owner completes the row to `status="COMPLETED"` after inference
  - loser returns existing completed data or a conflict while processing is in flight
- `PROCESSING` placeholder rows are excluded from normal alerts and stats reads
- Frontend BFF current workspace state:
  - all five route handlers are wired through `frontend/lib/bff-client.ts`
  - `USE_MOCK_API` is the single centralized server-only mock toggle
  - missing `FASTAPI_BASE_URL` or `INTERNAL_API_KEY` in non-mock mode returns structured `BFF_MISCONFIGURED`
  - all five handlers require an Auth.js session and return `401` without one
- Current auth split:
  - protected backend routes: `POST /api/predict`, `POST /api/triage`, `GET /api/alerts`, `GET /api/alerts/{id}`, `GET /api/stats`, `GET /api/ml-health`
  - public backend routes: `POST /api/feedback`, `GET /health`, `GET /api/health`
- Docker Compose, runnable ModSecurity wiring, and full Supabase or Redis integration are not in the repo yet

## 2026-03-20 Database-to-Frontend Audit Findings

### Database State
- DB file: `injection_alerts.db` (local SQLite)
- Migration status: 3 migrations exist (head: `20260319_000003`), DB has tables but no version stamp
- `/api/stats` returns real data: 18 total requests, BLOCKED=12, THROTTLED=3, ALLOWED=3
- `triage_status` column exists and is nullable

### Backend Endpoint Verification
| Endpoint | Status | Notes |
|---|---|---|
| GET /api/alerts | OK | Returns persisted records |
| GET /api/stats | EXISTS | Shape correct, real data |
| GET /api/ml-health | EXISTS | Shape correct, eval fields null (no eval artifacts) |
| GET /api/alerts/{id} | OK | Returns alert detail |
| PATCH /api/alerts/{id}/triage | OK | Persists triage status |

### BFF Layer Audit
- `USE_MOCK_API = false` - BFF is hitting real FastAPI, no mock data leaking
- Auth boundary: all 5 BFF handlers call `auth()` before data fetch ✓
- CalibrationBin schema: correct field names (`bin_center`, `accuracy`) ✓
- Multi-select confidence_level: correct end-to-end (FilterBar uses `delete()` + `append()`) ✓

### Hardcoded Values Fixed
| File | Fix |
|---|---|
| `frontend/app/(dashboard)/dashboard/page.tsx` | Removed derived claims: `'↑ +3 vs prev 6h'`, `'50–80% confidence'`, `'↓ Model stable'` |
| `frontend/components/ml-health/ModelHeader.tsx` | Changed `value="Temp-scaled"` to `value="—"` |

### Validation Results
- pytest: 168 passed ✓
- typecheck: PASSED ✓
- vitest (BFF slice): 46 passed ✓

Full audit report: `docs/project-ops/DATA_AUDIT.md`

## Open implementation gaps

- The reservation-first triage flow still depends on applied DB migrations for:
  - `created_at`
  - `status`
  - nullable result columns on placeholder rows
- The backend still uses async SQLAlchemy locally and is not fully wired to live Supabase behavior
- Some docs and prompts still need cleanup to remove stale verification commands and old partial-mock descriptions
- Data scripts still hardcode workstation-specific paths
- Dashboard stats now include throttled_count, top_source_ips, top_targeted_paths, attack_distribution with window filtering
- ML health now exposes optional eval metadata (macro_f1, ece, per_class_f1, calibration_bins, prediction_distribution) when model registry eval artifacts are present
- `PROCESSING` reservations now use lease ownership fields (`lease_expires_at`, `processing_owner_token`, `processing_attempt`) and can be reclaimed on demand when expired
- `app.state.model` alias has been removed; all routes use `app.state.model_service` directly
- `/api/alerts` now returns persisted records correctly - DB schema aligned

## Operator notes

- Canonical implementation docs live in:
  - `docs/CONTEXT.md`
  - `docs/architecture.md`
  - `docs/SETUP.md`
- Full audit findings in: `docs/project-ops/DATA_AUDIT.md`
- Treat cloud `origin/master` as the pushed baseline and this working tree as the latest local integration state.
- This file is intentionally shorter than the old root status file and should stay focused on current operator truth, not future planning prose.
