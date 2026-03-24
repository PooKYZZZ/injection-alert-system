# Living Checklist
> Location: `docs/project-ops/LIVING_CHECKLIST.md`
> Keep this file updated after every meaningful implementation or verification session.
> This is a working checklist, not the full runtime source of truth.

**Last updated:** 2026-03-24

Status note:
- Current test baseline: pytest 294 passed, focused vitest 74 passed, typecheck passed, lint passed
- Current source-of-truth runtime docs are `docs/CONTEXT.md`, `docs/architecture.md`, and `docs/SETUP.md`

---

## Current Verified State (2026-03-23)

### Test Baseline
- Backend: `python3 -m pytest -q` → **294 passed**
- Frontend lint: `cd frontend && npm run lint` → **PASSED**
- Frontend typecheck: `cd frontend && npm run typecheck` → **PASSED**
- Frontend BFF: `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **74 passed**
- Frontend full suite: `cd frontend && npx vitest run` → **122 passed**
- Frontend build: `cd frontend && npm run build` → **PASSED**

### Backend Routes
- `POST /api/predict` ✓
- `POST /api/triage` ✓
- `GET /api/alerts` ✓
- `GET /api/alerts/{id}` ✓
- `PATCH /api/alerts/{id}/triage` ✓
- `GET /api/stats` ✓
- `GET /api/ml-health` ✓
- `POST /api/feedback` ✓
- `POST /api/internal/waf-events` ✓
- `GET /health` ✓
- `GET /api/health` ✓

### Frontend/BFF Truths
- `USE_MOCK_API` is the single centralized server-only mock toggle ✓
- All BFF handlers require Auth.js session ✓
- `frontend/proxy.ts` is the active edge entrypoint ✓
- Local `next start` validation requires `AUTH_TRUST_HOST=true` ✓
- Transport contract values remain `BLOCKED`, `THROTTLED`, `ALLOWED` ✓

### Data Boundary
- App runtime uses Supabase-backed PostgreSQL ✓
- Tests use SQLite ✓
- Async SQLAlchemy remains the only DB access path ✓

---

## Open Backlog

- [ ] Put ModSecurity in the real browser-facing path without violating `Browser -> Next.js -> FastAPI`
- [ ] Redis-backed enforcement or review-queue state
- [ ] Repo-managed export and verification of Supabase policy / RLS state
- [ ] Re-assess any remaining chart container sizing warnings only after stable UI reproduction

---

## WAF Ingest Slice (Phase 1)

- [x] Internal WAF ingest schema and sanitization path
- [x] WAF ingest use case integrated with existing triage policy (`BLOCKED`, `THROTTLED`, `ALLOWED`)
- [x] WAF metadata persisted in `traffic_logs` (`ingest_source`, `matched_rule_messages`, `matched_rule_tags`)
- [x] Internal endpoint `POST /api/internal/waf-events` with bearer auth
- [x] BFF normalization extended to carry WAF metadata
- [x] Analyst alerts table verified to render CRS score and compact rule IDs
- [x] Bridge script + compose bridge service added for local smoke wiring

---

## Quick Reference Commands

```powershell
# Backend tests
.venv\Scripts\python.exe -m pytest -q

# Frontend lint + typecheck
cd frontend && npm run lint && npm run typecheck

# BFF-focused tests
cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts

# Full frontend tests
cd frontend && npx vitest run

# Frontend build
cd frontend && npm run build

# Start backend
.venv\Scripts\python.exe -m uvicorn web_app.presentation.app:create_app --reload

# Start frontend
cd frontend && npm run dev
```
