# PD1 Backend — Living Task Checklist (Step 8)
> Location: `docs/project-ops/LIVING_CHECKLIST.md`
> Paste this alongside the Context Block at the start of every new AI session.
> Check off items as you complete them. Keep this file updated after every session.
> This is your memory across sessions — never skip updating it.

Status note:
- This file is a working implementation checklist, not the live runtime source of truth.
- Some unchecked historical tasks below have since been implemented in code; use `docs/project-ops/STATUS.md`, `docs/CONTEXT.md`, and the codebase itself for current repo truth.

---

## How to Use This File

1. After every session, open this file and check off what you completed
2. Paste the updated checklist into the next AI session alongside the context block
3. The AI reads your checklist and knows exactly where you left off
4. Never start a session without an up-to-date checklist

---

## Checklist (Copy From Here)

```
=== TASK CHECKLIST — UPDATE EVERY SESSION ===

## PRE-REQUISITES
- [ ] PRE-A: Confirmed dev-now artifact exists in ml_model/model_registry/staging/
- [x] PRE-B: Checked frontend/features/alerts/types.ts — label crosswalk locked and documented
- [x] PRE-C: Normalization map constants file written and documented
      - Canonical frontend contract now derives from `frontend/features/alerts/contract.ts`
      - Locked `prediction`: `SQL Injection`, `Code Injection`, `Other Attacks`, `Normal`
      - Locked current backend-aligned `action_taken`: `BLOCKED`, `THROTTLED`, `ALLOWED`
      - Display-only aliases are separate from canonical transport values

## P-2 BACKEND

### Config + Migration
- [ ] web_app/config.py extended:
      - MODEL_REGISTRY_PATH added as new field (model_path NOT overloaded)
      - Locked constants added (thresholds, MAX_SEQ_LEN)
      - Env-aware failure flag added
- [ ] database.py ORM updated — missing columns added:
      - transaction_id (String, unique constraint, nullable)
      - request_path (String, nullable)
      - request_method (String, nullable)
      - crs_score (Integer, nullable)
      - crs_rule_ids (JSON/Text, nullable)
      - inference_latency_ms (Float, nullable — named with units)
      - NOTE: source_ip already exists — NOT re-added
      - NOTE: payload_snippet NOT added — derivable from http_request
      - NOTE: ORM comment added documenting request_headers/request_body folding decision
- [ ] Alembic initialized (alembic init run, alembic.ini configured for DATABASE_URL from env)
- [ ] Migration generated (alembic revision --autogenerate)
- [ ] Migration manually reviewed and corrected
- [ ] Migration applied (alembic upgrade head)
- [ ] Current unit/integration suite still passes after migration

### Repository
- [ ] get_by_id(alert_id) added — returns domain object or None
- [ ] get_stats_summary() added — aggregated counts, total count, avg inference_latency_ms
- [ ] get_alert_list(page, page_size, severity?, time_range?, search?) added:
      - Returns items AND total count in one query (COUNT subquery — not separate call)
      - Filter params included from day one
- [ ] get_by_transaction_id(transaction_id) added

### Model Service
- [ ] web_app/services/model_service.py created
- [ ] predict() method is synchronous
- [ ] predict() is threadpool-ready (called via run_in_threadpool at all call sites)
- [ ] Loads from MODEL_REGISTRY_PATH
- [ ] Returns: prediction, confidence, confidence_tier, inference_latency_ms, model_version
- [ ] Does NOT decide BLOCKED/THROTTLED/LOGGED — that stays in TriageUseCase
- [ ] Environment-aware failure: fails fast in non-dev, explicit mock fallback in dev/test with warning log

### App Wiring
- [ ] Lifespan context manager wired in app.py (not deprecated @app.on_event)
- [ ] Model service attached to app.state in lifespan
- [ ] Fail fast on missing artifact in non-dev — descriptive error
- [ ] Explicit mock fallback in dev/test with loud warning — never silent

### Auth
- [ ] web_app/presentation/dependencies/auth.py created
- [ ] verify_internal_token uses HTTPBearer from fastapi.security
- [ ] Token compared against @lru_cache cached Pydantic settings api_secret_key
- [ ] Applied to internal routers via router-level dependency:
      router = APIRouter(dependencies=[Depends(verify_internal_token)])
- [ ] /health and /api/health remain public — no auth required
- [ ] Returns 401 on missing token
- [ ] Returns 401 on invalid token (not 403)

### Pydantic Schemas
- [ ] StatsResponse created — total_requests field required
- [ ] MLHealthResponse created
- [ ] AlertDetailResponse created — matches IncidentDetailPanel contract
- [ ] AlertListResponse created — { items, total, page, page_size }

### Endpoints
- [ ] GET /api/stats implemented:
      - Calls get_stats_summary() from repository
      - total_requests field present (fixes MetricCards Copilot bug)
      - Labeled honestly — not "false-positive reduction" without CRS baseline
      - Returns zeroed metrics on empty table — not 500
- [ ] GET /api/ml-health implemented:
      - Reads from app.state.model_service — no DB call
      - Returns: model_version, status, average_latency_ms, traffic_processed,
        drift_detected (placeholder), confidence thresholds from config
- [ ] GET /api/alerts (list) implemented:
      - Calls get_alert_list() with filter params forwarded from request
      - Returns AlertListResponse with pagination
      - Normalization map applied
- [ ] GET /api/alerts/{id} implemented:
      - Calls get_by_id() from repository
      - Normalization map applied
      - Returns 404 on unknown ID
- [ ] POST /api/triage implemented:
      - Route handler is thin — validates, calls TriageUseCase, returns response
      - Reservation-first dedup: placeholder INSERT with `status=PROCESSING` happens before inference
      - Winner is determined by `INSERT ... ON CONFLICT DO NOTHING` rowcount on `transaction_id`
      - Winner runs `await run_in_threadpool(model_service.predict, payload)` and updates row to `COMPLETED`
      - Loser returns the existing completed alert or a retriable response while row is still `PROCESSING`
      - Stale `PROCESSING` rows return `503` with `Retry-After`
      - request_headers + request_body folded into http_request at write time
      - Returns 503 if model not ready
      - Returns 401 if no token
- [ ] ALLOWED → LOGGED fixed at source in TriageUseCase (not a BFF remap)
      - Current frontend contract intentionally preserves today's backend-emitted values:
        `BLOCKED`, `THROTTLED`, `ALLOWED`
      - Do not normalize this in BFF/frontend; resolve only when backend source changes
- [ ] Auth applied to all internal routers (triage_router and BFF-facing data routes)

### Backend Tests
- [ ] Startup fail — missing artifact, non-dev: lifespan raises clearly
- [ ] Startup warn — missing artifact, dev mode: mock fallback, warning logged
- [ ] Auth 401 — no token: internal route rejects request
- [ ] Auth 200 — valid token: internal route passes through
- [ ] Model 503 — bridge returns 503 when model not ready
- [ ] Alert detail 404 — unknown ID returns 404
- [ ] Empty stats — zeroed response on empty table, not 500
- [ ] Duplicate ingest — same transaction_id twice, one DB record, second returns existing
- [ ] Dedup PostgreSQL — reservation-first ON CONFLICT DO NOTHING atomic on transaction_id
- [ ] Placeholder rows do not leak into `/api/alerts` or `/api/stats`

## P-3 BFF + FRONTEND

### Pre-Checks
- [ ] Checkpoint Mark: CRSComparisonPanel — cut or keep? (Do NOT wire stats until answered)
- [x] MetricCards.tsx — total_requests binding fixed:
      data?.crs_comparison.total_crs_flagged → data?.crs_comparison?.total_requests ?? 0

### BFF Utility
- [x] frontend/lib/bff-client.ts created:
      - Reads INTERNAL_API_KEY and FASTAPI_BASE_URL from process.env
      - Injects Authorization: Bearer header
      - Handles upstream failures with structured error response
      - Propagates upstream HTTP status code where reasonable
      - All four route handlers use this utility — no scattered raw fetch calls
      - `USE_MOCK_API` is the single centralized server-only mock toggle

### BFF Route Handlers
- [x] alerts/route.ts — real wiring:
      - Filter params (severity, time_range, search, page, page_size) read from searchParams and forwarded
      - Response normalized to frontend pagination shape
      - Normalization map applied for field remapping
- [x] alerts/[id]/route.ts — real wiring:
      - Returns real data or clean 404 (no more mock-only `501`)
      - Normalization map applied
      - NOTE: Next.js 15 params Promise fix already done in this file
- [x] stats/route.ts — real wiring:
      - Upstream GET /api/stats is used
      - `total_requests` flows correctly to the frontend shape
      - Metric labels stay honest; no invented false-positive semantics
- [x] ml-health/route.ts — real wiring:
      - Calls real upstream in non-mock mode
      - Shape matches the frontend ML health component contract
- [x] USE_MOCK_API consolidated:
      - Single server-only flag (not NEXT_PUBLIC_)
      - One flag, one place to check, shared via bff-client.ts

### Env
- [x] frontend/.env.example restored/updated with required vars:
      - FASTAPI_BASE_URL=
      - INTERNAL_API_KEY=
      - USE_MOCK_API=

### Frontend Tests
- [x] BFF alerts list: shape correct, pagination fields present, filters forwarded, normalization applied
- [x] BFF alert detail: normalization map applied, 404 propagated cleanly
- [x] BFF stats: total_requests field present, shape matches MetricCards contract
- [x] BFF ml-health: response shape matches ML health component contract
- [x] Missing env returns `500` + `BFF_MISCONFIGURED`
- [x] Upstream failure returns structured error
- [x] Existing session auth pattern is still applied to all BFF handlers

### TypeScript
- [ ] Sidebar.tsx:34 type error fixed:
      unknown not assignable to number | undefined — specific type annotation fixed
- [x] npm run typecheck — clean pass, zero errors

=== END CHECKLIST ===
```

---

## Quick Status Summary

**Last updated:** [x] 2026-03-15 — confirmed cloud `master` includes backend read APIs, internal bearer auth, and reservation-first triage ingest; locally wired all four Next.js BFF handlers through `frontend/lib/bff-client.ts`, centralized `USE_MOCK_API`, verified frontend/backend checks, and confirmed backend test baseline is `84 passed`

**Current focus:** [x] BFF wiring is complete; next work is backend contract enrichment for richer dashboard stats and ML health details if needed

**Next up:** [x] Clean remaining stale docs/prompts and decide whether dashboard-only stats fields should stay BFF-derived defaults or be added at backend source

**Blockers:** [x] Applied environments must be migrated so `created_at`, `status`, and nullable placeholder result columns match the current reservation-first triage code

**Completed today:** [x] Added shared server-only BFF fetch/normalization/error handling, real upstream wiring for alerts/detail/stats/ml-health, centralized mock mode, focused frontend tests, and doc updates based on pushed cloud baseline plus current local BFF work
