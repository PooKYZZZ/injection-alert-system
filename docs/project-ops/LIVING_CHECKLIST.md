# PD1 Backend — Living Task Checklist
> Location: `docs/project-ops/LIVING_CHECKLIST.md`
> Paste this alongside the Context Block at the start of every new AI session.
> Check off items as you complete them. Keep this file updated after every session.
> This is your memory across sessions — never skip updating it.

**Last updated:** 2026-03-20

Status note:
- This file is a working implementation checklist, not the live runtime source of truth.
- Current test baseline: pytest 87 passed, vitest 74 passed, typecheck passed
- Full audit report: `docs/project-ops/DATA_AUDIT.md`

---

## How to Use This File

1. After every session, open this file and check off what you completed
2. Paste the updated checklist into the next AI session alongside the context block
3. The AI reads your checklist and knows exactly where you left off
4. Never start a session without an up-to-date checklist

---

## Current Verified State (2026-03-20)

### Test Baseline
- Backend: `.venv\Scripts\python.exe -m pytest -q` → **87 passed**
- Frontend: `cd frontend && npm run typecheck` → **PASSED**
- Frontend BFF: `cd frontend && npx vitest run` → **74 passed**

### Backend Routes (All Implemented)
- `POST /api/predict` ✓
- `POST /api/triage` ✓ (reservation-first)
- `GET /api/alerts` ✓
- `GET /api/alerts/{id}` ✓
- `PATCH /api/alerts/{id}/triage` ✓
- `GET /api/stats` ✓ (window filtering)
- `GET /api/ml-health` ✓ (eval metadata optional)
- `POST /api/feedback` ✓
- `GET /health` ✓
- `GET /api/health` ✓

### Frontend BFF Routes (All Implemented)
- `frontend/app/api/alerts/route.ts` ✓
- `frontend/app/api/alerts/[id]/route.ts` ✓
- `frontend/app/api/alerts/[id]/triage/route.ts` ✓ (NEW - PATCH triage)
- `frontend/app/api/stats/route.ts` ✓
- `frontend/app/api/ml-health/route.ts` ✓

### BFF Status
- `USE_MOCK_API` is the single centralized server-only mock toggle ✓
- All handlers require Auth.js session ✓
- CalibrationBin schema uses `bin_center` and `accuracy` ✓
- Multi-select confidence_level correctly uses `getAll()` + `append()` ✓

### Hardcoded Values Fixed (2026-03-20 Audit)
- `dashboard/page.tsx`: Removed hardcoded derived claims
- `ModelHeader.tsx`: Fixed hardcoded calibration claim

---

## 2026-03-20 Database-to-Frontend Audit Summary

### Database State
- DB: SQLite at `injection_alerts.db`
- Total rows: 18
- BLOCKED: 12, THROTTLED: 3, ALLOWED: 3

### Endpoint Status (Verified)
- `/api/alerts` - OK, returns persisted records
- `/api/alerts/{id}` - OK, returns alert detail
- PATCH `/api/alerts/{id}/triage` - OK, persists triage status

### Gap Items for Future Work
1. Implement automatic reclamation of stale `PROCESSING` reservations (returns 503 + Retry-After)
2. Add richer backend-native dashboard stats beyond BFF normalization
3. Wire live Supabase deployment
4. TrustedHostMiddleware / HTTPS redirect configuration

---

## Quick Reference Commands

```powershell
# Backend tests
.venv\Scripts\python.exe -m pytest -q

# Frontend typecheck
cd frontend && npm run typecheck

# Full frontend tests
cd frontend && npx vitest run

# BFF-focused tests
cd frontend && npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts

# Start backend
uvicorn web_app.presentation.app:create_app --reload

# Start frontend
cd frontend && npm run dev
```
