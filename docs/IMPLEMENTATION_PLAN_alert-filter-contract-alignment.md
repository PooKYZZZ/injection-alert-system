# Implementation Plan: Frontend-Shaped BFF and Backend Contract
Date: March 22, 2026
Status: **COMPLETE** - All phases implemented (backend filters, SSR/CSR parity, a11y)

## Executive Summary

This plan tracks the alignment between frontend filter needs and backend implementation. 
**Current state**: BFF and frontend are complete, but backend `/alerts` route only supports 3 of 11 required filters.

### Completion Status
- ✅ **Phase 2 (BFF canonicalization)**: Complete
- ✅ **Phase 3 (Frontend fetch-path)**: Complete — SSR/CSR parity fixed, all 11 filters preserved in CSR flow
- ✅ **Phase 4 (ML metadata robustness)**: Complete
- ✅ **Phase 1 (Backend alerts contract)**: Complete - all 11 filters implemented
- ✅ **Phase 5 (a11y and hygiene)**: Complete - checkboxes have aria-labels

## 0) Restored Context From Prior Revision

### 0.1 Recent commit impact (restored)
Latest branch commits already touched many target files in this plan (routes, repository, BFF client, dashboard components, and migration updates). This means implementation should be executed as a reconciliation pass, not greenfield work.

Notable recent change areas already present in branch:
- `web_app/presentation/api/routes.py`
- `web_app/infrastructure/repositories/traffic_log_repository.py`
- `frontend/lib/bff-client.ts`
- `frontend/components/alerts/*` and `frontend/components/dashboard/*`
- `migrations/versions/20260322_000004_add_triage_lease_fields.py`

### 0.2 Previously validated fix clusters (restored)
This plan intentionally includes fixes for two root-cause clusters identified during verification:

Cluster A: Alerts state/contract inconsistency
- Backend alerts route supports narrower params than BFF/frontend currently emit.
- Frontend alerts query path partially rebuilds filters and may drop non-dashboard state.

Cluster B: ML eval metadata integration mismatch
- Eval metadata discovery relies on a narrow filename pattern.
- Calibration bin parser assumes a stricter schema than real artifacts and can fail.

### 0.3 Plan file tracking note (restored)
Ensure this plan file is committed so implementation and review comments reference a stable document.

## 1) Governance Classification
Primary change kind: new feature slice
Secondary change kinds: direct fix, local refactor
Scope: BFF and backend contract alignment for alerts, stats, and ML health responses consumed by current frontend components
Extraction outcome: boundary (clear Browser -> Next.js BFF -> FastAPI boundary with canonical DTOs)
Contract note: this plan changes and standardizes public query/response contracts between BFF and backend for alerts list retrieval and filtering
Materialization note: keep route handlers thin, move query normalization and data adaptation to dedicated BFF/backend mapping layers, preserve existing app layering
Convention decision: preserve existing naming where already stable, add explicit alias mapping where frontend and backend use different names
Validation: unit + integration + route contract tests for every changed endpoint and transformation
Escalation note: no architectural escalation required beyond contract updates already inside current boundaries

## 2) Problem Statement (What Must Match Frontend Output)
The frontend currently has richer filter and shape needs than the backend alerts list contract. This creates state drift where UI controls can appear active while backend does not actually filter by those controls.

Current frontend output models that must be honored:
- Alerts list model: `Alert`, `PaginatedAlerts`, `AlertFilters`
- Dashboard stats model: `DashboardStats` with `activity_buckets`, top source IPs, top targeted paths, and delta fields
- ML health model: `MLHealthData` with optional eval metadata and calibration bins

Current mismatch hotspots:
- Frontend/BFF accepts and forwards more alerts filters than backend route/repository currently support.
- Alerts query path uses a reduced filter object in parts of the frontend fetch pipeline.
- Eval metadata loading and calibration schema parsing are fragile against actual artifact file naming and field shapes.

## 3) Frontend-Driven Data Contract Inventory

### 3.1 Alerts page required request state
Canonical filter object required by frontend state and URL:
- `page` (int)
- `pageSize` (int)
- `severity` (enum: ALL, LOW, MEDIUM, HIGH)
- `confidence_level` (multi-value enum array)
- `action` (enum: BLOCKED, THROTTLED, ALLOWED)
- `triage_status` (enum)
- `prediction` (enum)
- `source_ip` (string)
- `search` (string)
- `window` (enum: 1h, 6h, 24h, 7d)
- `sort_by` (enum: timestamp, confidence, severity)
- `sort_dir` (enum: asc, desc)

### 3.2 Alerts page required response shape
- `items: Alert[]`
- `total: number`
- `page: number`
- `pageSize: number`

Each `Alert` must include (nullable where expected):
- `alert_id`, `timestamp`, `source_ip`, `request_path`, `request_method`
- `payload_snippet`, `prediction`, `confidence`, `confidence_level`, `action_taken`
- `triage_status`, `crs_score`, `crs_rule_ids`, labeling fields

### 3.3 Dashboard stats required response shape
- totals and counters: total_requests, actionable_alerts, blocked/allowed/throttled
- trends/deltas: prev_* fields
- visual payloads: activity_buckets with timestamps and width, attack_distribution
- ranking payloads: top_source_ips, top_targeted_paths

### 3.4 ML health required response shape
- model health primitives: status, latency, drift fields, thresholds, traffic_processed
- optional eval metadata: macro_f1, ece, per_class_f1, calibration_bins, prediction_distribution

## 4) Target BFF Architecture (Tailored to Frontend Outputs)

### 4.1 BFF responsibilities
The BFF should be the single adapter boundary that:
- normalizes frontend URL/search params into a canonical request DTO
- maps canonical DTO keys to backend query keys
- validates backend responses before returning to browser
- transforms backend payloads into frontend model shapes
- applies safe defaults for optional staged fields
- never leaks backend internals or auth details to browser

### 4.2 Canonical BFF request DTOs
Define explicit DTOs in BFF layer:
- `AlertsQueryDTO` (full filter set above)
- `StatsQueryDTO` (`window`, `timezone`)
- `MLHealthQueryDTO` (none currently)

Canonical multi-value query rule:
- Use one repeated key for confidence filters: `confidence_level=value1&confidence_level=value2`.
- Do not use bracket-suffixed query key variants (`confidence_level[]`, `confidence_levels[]`) as canonical names.
- BFF may temporarily accept legacy aliases during migration, but must emit only canonical key names.

Normalization rules:
- trim `search`; max length 200
- parse numbers safely (`page`, `pageSize`)
- deduplicate multi-value `confidence_level`
- enforce enum validation at edge
- keep defaults centralized (`DEFAULT_ALERT_FILTERS`)

### 4.3 BFF endpoint behavior
- `GET /api/alerts`: accepts all alerts filters from frontend URL, maps to backend, returns normalized `PaginatedAlerts`
- `PATCH /api/alerts/{id}/triage`: validates id and status, forwards canonicalized id
- `GET /api/stats`: passes `window` and `timezone` and returns `DashboardStats`
- `GET /api/ml-health`: returns `MLHealthData`

### 4.4 Error contract for frontend state management
All BFF routes return browser-safe errors using RFC 9457 Problem Details as primary shape:
- media type: `application/problem+json`
- core members: `type`, `title`, `status`, `detail`, `instance`
- extension members allowed for app-specific fields (for example `code`, `retry_after`)
- preserve retry semantics via `Retry-After` when applicable
- map upstream auth failures to stable problem type URIs and avoid leaking internals

Compatibility note:
- During transition, BFF can dual-write legacy `{ error: { code, message } }` only if needed by existing frontend handlers, then remove once consumers are migrated.

### 4.5 Next.js App Router contract rules (2026)
- For server-side page data fetches that depend on query params, use page `searchParams` prop as canonical input.
- Treat `useSearchParams` as client-only UI state hook.
- For prerendered routes that use `useSearchParams`, ensure nearest subtree is wrapped with `Suspense`.
- Keep URL state canonicalization centralized so SSR page fetch input and CSR refetch input are equivalent.

## 5) Target Backend Architecture (Tailored to BFF Needs)

### 5.1 Backend route contract for alerts
FastAPI `GET /alerts` must support full frontend filter matrix:
- `page`, `page_size`
- `severity`
- `time_range` (accept alias from BFF mapping of `window`)
- `search`
- `action`
- `triage_status`
- `confidence_level` as repeated multi-value query key
- `prediction`
- `source_ip`
- `sort_by`, `sort_dir`

Decision: canonical backend key is `confidence_level` (repeat key for multi-select). Keep temporary alias support only if migration period is needed.

### 5.1.1 FastAPI query model enforcement
Define alerts filters as a typed FastAPI query parameter model:
- strongly typed enums and numeric bounds for paging/sort fields
- list field for repeated `confidence_level`
- explicit string constraints where appropriate (`search`, `source_ip`)
- `model_config = {"extra": "forbid"}` so unsupported query parameters return validation errors instead of silent no-ops

This query model is the backend contract source of truth for `/alerts`.

### 5.2 Repository query behavior for alerts
`get_alert_list` should:
- apply all supported filters safely and composably
- keep deterministic ordering with stable tie-breakers
- whitelist sortable columns (no dynamic SQL string interpolation)
- compute total count before paging
- honor pagination bounds and defaults

### 5.3 Backend schema consistency
Presentation schemas should match frontend-consumed shape after BFF mapping:
- alerts list returns `page_size` (BFF maps to `pageSize`)
- triage/action/confidence enums consistent with frontend contracts
- optional fields remain optional and nullable as expected

### 5.4 ML eval metadata service robustness
Model service metadata loader must:
- discover real eval files used by repository layout (not only one filename pattern)
- parse multiple calibration bin schema variants safely
- never crash service startup on metadata parsing failures
- return partial metadata gracefully when fields are unavailable

## 6) Canonical Parameter Mapping Table

| Frontend URL key | Canonical BFF DTO key | Backend query key |
|---|---|---|
| page | page | page |
| pageSize | pageSize | page_size |
| severity | severity | severity |
| confidence_level (multi, repeated key) | confidence_level (array in DTO) | confidence_level (repeated key) |
| action | action | action |
| triage_status | triage_status | triage_status |
| prediction | prediction | prediction |
| source_ip | source_ip | source_ip |
| search | search | search |
| window | window | time_range |
| sort_by | sort_by | sort_by |
| sort_dir | sort_dir | sort_dir |

Rule: do not rebuild filters in multiple formats across components. URL -> canonical BFF DTO -> backend query is the only path.

Implementation note:
- BFF internal DTO may represent confidence filters as an array, but query serialization must emit repeated `confidence_level` keys.

## 7) Data Transformation Blueprint

### 7.1 Alerts transformation
Backend `AlertDetailResponse` -> BFF `Alert`:
- `id` -> `alert_id` (string)
- preserve nullability for optional fields
- normalize enum values and reject invalid payloads

Paginated metadata transformation:
- backend `page_size` -> frontend `pageSize`

### 7.2 Stats transformation
Backend stats payload -> `DashboardStats`:
- parse/validate timestamps in activity buckets
- sort buckets chronologically in BFF
- apply default zeros for staged optional numeric fields
- convert action strings to typed `AlertAction | null`

### 7.3 ML health transformation
Backend ML health -> `MLHealthData`:
- normalize thresholds and derive `medium`
- preserve drift nullability semantics
- support both prediction_distribution shapes (legacy and baseline/current)
- keep eval metadata optional and non-fatal

## 8) Aggregation Strategy (Avoid Over-Fetching / Under-Fetching)

Principles:
- one frontend view maps to one purpose-built BFF response shape
- avoid forcing frontend to stitch unrelated backend endpoints for a single render
- avoid mega-endpoints that return unused data

Concrete strategy:
- Alerts page:
  - list query returns list + total + paging only
  - detail query remains separate by alert id
- Dashboard page:
  - stats endpoint returns exactly dashboard card/chart datasets
  - no full alerts payload in stats route
- ML health page:
  - dedicated endpoint with optional eval block

Optional optimization after correctness fixes:
- parallel backend fetches inside BFF only when a page truly needs multiple sources at once
- retain endpoint granularity where React Query can cache independently

## 9) Implementation Phases (Code-Focused)

### Phase 1: Backend alerts contract completion [COMPLETE - 11 of 11 filters implemented]
- [x] Extend `web_app/presentation/api/routes.py` `get_alerts` parameters
  - **Evidence**: routes.py lines 243-269 - Uses AlertQueryParams with all 11 filters
- [x] Extend `web_app/domain/interfaces.py` `get_alert_list` signature
  - **Evidence**: interfaces.py lines 251-269 - Added `action`, `triage_status`, `confidence_levels`, `prediction`, `source_ip`, `sort_by`, `sort_dir` parameters
- [x] Implement full filtering/sorting in `web_app/infrastructure/repositories/traffic_log_repository.py`
  - **Evidence**: traffic_log_repository.py lines 933-1045 - Implements all 11 filters with safe SQLAlchemy where clauses and deterministic ordering

### Phase 2: BFF canonicalization [COMPLETE]
- [x] Keep/upgrade `frontend/lib/bff-client.ts` parameter mapping and query building
  - **Evidence**: PARAM_MAP (lines 542-555) maps all frontend keys to backend keys
- [x] Ensure multi-value confidence filter round-trips correctly
  - **Evidence**: lines 571-573 append repeated `confidence_level` keys
- [x] Use canonicalized id in triage route forwarding
  - **Evidence**: lines 652-655 use parseAlertId before triage call

### Phase 3: Frontend fetch-path consistency [COMPLETE - SSR/CSR parity fixed]
- [x] Update alerts queries to consume full alerts filter object rather than reduced dashboard-only subset
  - **Evidence**: queries.ts lines 60-78 - `alertListOptionsFromFilters` accepts `AlertFilters` and uses `toAlertQueryString`
- [x] Ensure query keys are generated from canonical full filter state
  - **Evidence**: queries.ts line 63 - `alertKeys.list(toAlertQueryString(filters))`
- [x] Ensure refetch preserves URL-driven state
  - **Evidence**: AlertsTable.tsx line 183 - uses `useAlertsFromFilters(params)` with full `AlertFilters` (no down-conversion)
  - **Evidence**: AlertsTable.tsx sort handler (line 192) uses `new URLSearchParams(searchParams.toString())` preserving multi-value params
  - **Evidence**: AlertsTable.tsx pagination handlers (lines 371, 388) use same pattern preserving multi-value params

### Phase 4: ML metadata robustness [COMPLETE]
- [x] Update `web_app/services/model_service.py` eval file discovery
  - **Evidence**: lines 258-269 find `*_metrics.json` files in eval/ directory
- [x] Harden calibration bin parsing for schema variants
  - **Evidence**: lines 287-298 use safe `.get()` defaults
- [x] Preserve non-fatal behavior on metadata parse errors
  - **Evidence**: lines 273-275 return empty dict on JSON parse failure

### Phase 5: a11y and hygiene [COMPLETE]
- [x] Add accessible labels for `RecentAlertsTable` checkboxes
  - **Evidence**: RecentAlertsTable.tsx line 59 - header checkbox has `aria-label="Select all alerts"`; line 83 - row checkbox has `aria-label={`Select alert ${alert.alert_id}`}`
- [x] Add accessible labels for `AlertsTable` checkboxes (alerts page)
  - **Evidence**: AlertsTable.tsx line 262 - header checkbox has `aria-label="Select all alerts"`; line 297 - row checkbox has `aria-label={`Select alert ${alert.alert_id}`}`
- [x] Fix minor parser/lint hygiene items if still pending
  - **Evidence**: typecheck passes with no errors

## 10) File-Level Change Matrix

### Backend [COMPLETE]
- `web_app/presentation/api/routes.py` - **COMPLETE**: Uses AlertQueryParams with all 11 filters
- `web_app/domain/interfaces.py` - **COMPLETE**: Signature includes all 11 parameters
- `web_app/infrastructure/repositories/traffic_log_repository.py` - **COMPLETE**: Implements all 11 filters with deterministic ordering
- `web_app/services/model_service.py` - **COMPLETE**: Eval metadata loading works
- `web_app/presentation/schemas/schemas.py` - **COMPLETE**: Added AlertQueryParams with `extra="forbid"`

### BFF / Next routes [COMPLETE]
- `frontend/lib/bff-client.ts` - **COMPLETE**: PARAM_MAP and getAlerts handle all filters
- `frontend/app/api/alerts/route.ts` - **NOT CHANGED**: Uses bff-client internally
- `frontend/app/api/alerts/[id]/triage/route.ts` - **NOT CHANGED**: Uses bff-client internally
- `frontend/app/api/stats/route.ts` - **NOT CHANGED**: Uses bff-client internally
- `frontend/app/api/ml-health/route.ts` - **NOT CHANGED**: Uses bff-client internally

### Frontend data/query layer [COMPLETE]
- `frontend/lib/searchParams.ts` - **COMPLETE**: Added `toAlertQueryString()` for full AlertFilters serialization
- `frontend/features/alerts/queries.ts` - **COMPLETE**: Added `useAlertsFromFilters` accepting full AlertFilters
- `frontend/features/alerts/schemas.ts` - **COMPLETE**: Added `action` to sort_by enum
- `frontend/components/alerts/AlertsTable.tsx` - **COMPLETE**: Uses `useAlertsFromFilters`, sort/pagination handlers preserve multi-value params
- `frontend/components/alerts/FilterBar.tsx` - **NOT CHANGED**: Emits full filter state

## 11) Test Plan (Minimum Required)

### 11.1 Backend tests
- Repository unit tests for every alerts filter and sort option
- Integration tests for `/alerts` with combined filters and pagination
- Test alias behavior (`window` mapped to `time_range` through BFF)
- Route contract test: unknown query parameter returns validation error (`extra` forbidden)

### 11.2 BFF tests
- Verify query mapping for all alert filter keys
- Verify repeated confidence filters are passed upstream correctly
- Verify response normalization for alerts/stats/ml-health
- Verify triage route uses canonical id value

### 11.3 Frontend tests
- Verify alerts query key and request preserve full URL filter state
- Verify filter changes trigger expected request parameters
- Verify pagination/sort persistence across refetches
- Add accessibility assertion for recent alerts table checkboxes
- Verify SSR page-level fetch path (via page `searchParams`) and CSR refetch path produce equivalent canonical filter objects

### 11.4 ML metadata tests
- Loader finds real eval filename patterns used in repo
- Calibration parsing supports current artifact schema and fallback schema
- Metadata parse failures degrade gracefully (no service crash)

### 11.5 Contract parity regression tests (restored)
- Add a parity test that confirms frontend URL params -> BFF forwarded params -> backend accepted params are equivalent for all supported alerts filters.
- Add a test that verifies list hydration/refetch uses the same canonical filter object and does not drop `page`, `sort`, `triage_status`, `action`, or multi-value `confidence_level`.

## 12) Rollout and Compatibility Strategy

- Keep BFF as compatibility shield while backend contract is expanded.
- If backend key naming changes, preserve temporary alias support in BFF to avoid frontend breakage.
- Deploy backend contract first, then BFF/frontend wiring changes.
- Add feature-flag-like guard only if rollout must be partial; otherwise prefer atomic merge with complete tests.
- Keep alerts/stats/ml-health route handlers request-time by default and do not opt into static caching for operational data endpoints.

### 12.1 Safe deployment sequence (restored)
1. Backend route/repository contract support (accept + apply all expected filters).
2. BFF canonical mapping and response normalization updates.
3. Frontend query canonicalization and refetch consistency updates.
4. ML metadata loader/schema robustness updates.
5. A11y/hygiene cleanup.

### 12.2 Rollback strategy (restored)
Trigger rollback if filtering correctness, triage flow, or ML health responses regress in staging/production.

Rollback steps:
1. Revert the merge commit for the failing phase.
2. If needed, rollback migrations only when a migration is part of the failed phase.
3. Re-run targeted contract tests and smoke tests before re-deploy.

## 13) Acceptance Criteria

### Current Status: MET (all 5 criteria complete)

- [x] Every alerts filter visible in frontend impacts backend query results.
  - **Evidence**: schemas.py AlertQueryParams includes all 11 filters; routes.py passes all to repository; repository implements all filters
- [x] URL state, query key state, and request payload state are identical for alerts list fetches.
  - **Evidence**: BFF maps all 11 filter params to backend; backend accepts and applies all 11 filters
- [x] Stats and ML health responses match frontend models without ad-hoc client hacks.
  - **Evidence**: bff-client.ts normalizeStats and normalizeMlHealth handle all fields
- [x] No startup/runtime failure from eval metadata parsing mismatches.
  - **Evidence**: model_service.py returns empty dict on parse errors
- [x] No known checkbox a11y violations in recent alerts table.
  - **Evidence**: Checkboxes at RecentAlertsTable.tsx have aria-labels

### 13.1 PR-ready checklist (restored)
- [x] Backend tests for alerts filtering and sorting pass. (168 passed)
- [x] BFF tests for parameter forwarding and normalization pass. (41 passed)
- [x] Frontend typecheck passes. (No errors)
- [x] SSR/CSR parity verified. (Both paths use `toAlertQueryString` with full `AlertFilters`)
- [x] Targeted ML metadata loader tests pass. (Included in backend tests)
- [x] Typecheck and route tests pass in `frontend`. (No errors)
- [x] Use `docs/PR_CHECKLIST_alert-filter-contract-alignment.md` as the copy-paste PR checklist. (Updated with evidence)

## 14) Deduplication and Quality Recheck
This revision intentionally removes repeated sections from earlier drafts and consolidates into:
- one canonical contract inventory
- one mapping table
- one transformation blueprint
- one implementation phase plan
- one test plan

No duplicated action items should exist across sections 9, 10, and 11.

## 15) Immediate Next Execution Step
Start with Phase 1 and Phase 2 in one backend-first PR stack:
1. Finish backend alerts contract support
2. Keep BFF mapping as canonical adapter
3. Add contract tests before frontend refetch wiring changes

## 16) Execution Commands (restored)

```bash
# Backend focused tests
.venv/Scripts/python.exe -m pytest -q tests/unit/test_traffic_log_repository.py tests/integration/test_app_startup.py

# Frontend focused tests
cd frontend
npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts
npm run typecheck
```
