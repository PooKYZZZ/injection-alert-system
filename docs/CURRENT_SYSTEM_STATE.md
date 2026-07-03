# Current System State - Comprehensive Overview

**Last Updated:** 2026-07-03

This document provides detailed answers about the current state of the Injection Alert System codebase.

Client-stated PD2 requirements are tracked in `docs/client-requirements.md`. The `CRITICAL >=90%` confidence tier and the named-account/server-side RBAC foundation are implemented. Alert UI role affordances are also implemented in the dashboard. MFA/2FA, password recovery, timely alerts, and email notifications after detection remain incomplete.

Verified WAF proof is tracked in `reports/modsecurity-live-proof/e2e-proof.md` and `docs/project-ops/DEMO_TARGET_WAF_PROOF.md`. The technical CyberTrace WAF proof path uses `localhost:8088`. The realistic protected demo website path uses `localhost:8089` with the separate land-records-portal running on host port `3010`. Backend remains internal-only in Docker Compose and should be queried with `docker compose exec`, not `localhost:8000` unless backend port 8000 is explicitly published.

---

## 1. Seed Data / Database Schema

### Traffic Logs Table Schema (from migrations)

The `traffic_logs` table contains:

| Column | Type | Nullable | Notes |
|--------|------|----------|-------|
| `id` | Integer | No | Primary key |
| `transaction_id` | String(128) | Yes | Unique constraint |
| `timestamp` | DateTime | No | Server default now() |
| `source_ip` | String(45) | Yes | IPv4/IPv6 |
| `request_path` | String(512) | Yes | |
| `request_method` | String(16) | Yes | GET, POST, etc. |
| `http_request` | Text | No | Full HTTP request |
| `crs_score` | Integer | Yes | ModSecurity CRS score |
| `crs_rule_ids` | JSON | Yes | Array of rule IDs |
| `prediction` | String(50) | Yes | SQL Injection, Code Injection, Other Attacks, Normal |
| `confidence` | Float | Yes | 0.0-1.0 |
| `confidence_level` | String(10) | Yes | LOW, MEDIUM, HIGH, CRITICAL |
| `inference_latency_ms` | Float | Yes | |
| `model_version` | String(50) | Yes | |
| `action_taken` | String(50) | Yes | BLOCKED, THROTTLED, ALLOWED |
| `analyst_label` | String(50) | Yes | Analyst correction (ML feedback) |
| `labeled_at` | DateTime | Yes | |
| `labeled_by` | String(100) | Yes | |
| `created_at` | DateTime | No | Added in migration 20260315 |
| `status` | String(16) | No | Default `COMPLETED` |
| `triage_status` | String(32) | Yes | `new`, `in_review`, `escalated`, `resolved`, `false_positive` |

### Key Observations

- `triage_status` exists in the database
- Triage is backend-synced via PATCH
- The frontend uses the BFF to sync triage status, not localStorage
- Runtime app data now lives behind a Supabase-backed PostgreSQL boundary
- Tests still use SQLite

---

## 2. Current Dashboard Page Rendering

**File**: `frontend/app/(dashboard)/dashboard/page.tsx`

The dashboard page renders:

1. `DashboardAlertAnalyticsSection`
2. `RecentAlertsTable`

`DashboardAlertAnalyticsSection` contains metric cards, hero activity strip, and the main chart section. `RecentAlertsTable` is the compact dashboard preview table.

---

## 3. Current Alerts Page Rendering

**File**: `frontend/app/(dashboard)/alerts/page.tsx`

The alerts page currently renders:

- `FilterBar`
- `AlertsTable`
- `AlertDrawer`
- Role-aware alert affordances now hide dense-row mutation controls for viewers, keep triage controls for analysts, and keep the full control set for admins.

### Current Triage Implementation

- Storage: backend database via `PATCH /api/alerts/{id}/triage`
- BFF endpoint: `frontend/app/api/alerts/[id]/triage/route.ts`
- Status options: `new`, `in_review`, `escalated`, `resolved`, `false_positive`
- Persistence: backend-synced via BFF

---

## 4. Current ML Health Page Rendering

**File**: `frontend/app/(dashboard)/ml-health/page.tsx`

The page renders `MLHealthDetail`, which currently shows:

- model version and status
- latency metrics and trend
- drift score and status
- traffic processed count
- confidence thresholds
- macro F1 and ECE when available
- per-class F1 chart
- reliability diagram
- prediction distribution
- confidence drift chart

The confidence drift chart is currently presented as simulated trend data and should be treated as such unless backed by stored historical telemetry.

---

## 5. Current BFF Stats Response Shape

The backend and frontend both support:

- total requests
- blocked / throttled / allowed counts
- average inference latency
- average confidence
- top source IPs
- top targeted paths
- attack distribution
- activity buckets
- time window filtering

---

## 6. Current BFF Alerts Response Shape

The alert flow currently includes:

- persisted alert ID
- timestamp
- source IP
- request path and method
- prediction
- confidence
- confidence level
- action taken
- triage status
- analyst feedback metadata
- CRS score and rule IDs
- WAF transaction metadata for ModSecurity-ingested alerts, including transaction ID, source IP, request path, query string, matched rule messages, and matched rule tags

Confidence-tier naming note:

- LOW, MEDIUM, HIGH, and CRITICAL currently represent model confidence tiers, not business/security severity
- persisted backend field remains `confidence_level`
- preferred filter/query naming is `confidence_tier`
- legacy `severity` query compatibility is retained for existing URLs and callers
- `CRITICAL >=90%` is implemented as the high-confidence threshold
- no retraining, recalibration, or model artifact change was required
- historical rows are not retroactively reclassified
- persisted-alert confidence grouping and styling use backend-emitted `confidence_level`
- enforcement-policy counts exclude Normal predictions; Normal remains `ALLOWED` for all valid tiers
- confidence-tier badges always display the canonical tier and do not substitute `Benign`

The frontend still prefixes IDs for display (`ALT-...`) while preserving backend IDs internally for route calls and triage mutations.

---

## 7. Current ML Health Response

The frontend ML health flow currently supports:

- `model_version`
- `status`
- `latency_ms`
- `latency_trend`
- `drift_score`
- `drift_status`
- `traffic_processed`
- `thresholds`
- optional eval metadata:
  - `macro_f1`
  - `ece`
  - `per_class_f1`
  - `calibration_bins`
  - `prediction_distribution`
- optional inference queue health:
  - `max_size`
  - `depth`
  - `available_capacity`
  - `worker_running`
  - `total_enqueued`
  - `total_processed`
  - `total_failed`
  - `overflow_count`

---

## 8. Current Zustand Stores

The main shared dashboard store remains `frontend/store/dashboardStore.ts`, which manages:

- selected alert IDs
- active incident ID
- selection toggling
- bulk selection
- selection clearing

---

## 9. Existing Dashboard Components

The dashboard component set currently includes:

- metric cards
- hero activity strip
- alert analytics section
- incident detail panel
- alerts table
- bulk action bar
- recent alerts table
- top source IPs
- top targeted paths
- confidence and distribution charts

The route and chart composition is now stable enough that docs should treat it as live implementation, not proposed UI.

---

## 10. Current Sidebar and Layout

The dashboard layout:

- uses `getSession()` / session helpers for auth gating
- redirects unauthenticated users to `/login`
- renders the sidebar, top bar, and child dashboard content

Current sidebar navigation includes Dashboard, Alerts, and ML Health as the active primary paths. Additional destinations remain planned rather than fully implemented.

### Current Auth State and Remaining Gaps

- Current state: Auth.js uses named `AUTH_USERS_JSON` accounts with scrypt password hashes, eight-hour JWT sessions, `ADMIN`/`ANALYST`/`VIEWER` claims, per-account `authz_version`, local login throttling, and safe JSON login and route-guard audit events.
- All six BFF routes enforce server-side permissions and fresh registry role/version checks.
- Remaining client-required work includes MFA/2FA and password recovery. Managed identity, distributed throttling, and persistent audit storage remain future hardening.
- This password-only foundation is AAL1-style and is not an AAL2 compliance claim.

---

## 11. How Triage Currently Works (End-to-End)

### Current State: Backend-Synced

#### Triage Status
- Endpoint: `PATCH /api/alerts/{id}/triage`
- BFF Route: `frontend/app/api/alerts/[id]/triage/route.ts`
- Purpose: analyst workflow tracking
- Persistence: backend database, synced via BFF

#### Analyst Label
- Endpoint: `POST /api/feedback`
- Purpose: correct ML predictions and persist analyst feedback
- This is separate from triage workflow state

---

## 12. Current USE_MOCK_API State

**Current setting:** `USE_MOCK_API=false`

This means:

- the BFF hits the real FastAPI backend
- app data comes from the backend unless explicitly toggled
- mock data is only used when `USE_MOCK_API=true`

---

## 13. Test Baseline (2026-07-03)

| Test Suite | Result |
|------------|--------|
| pytest | 489 passed |
| lint | PASSED |
| typecheck | PASSED |
| vitest (full) | 288 passed |
| build | PASSED |

---

## Summary: What's Implemented (2026-07-03)

| Feature | Status |
|---------|--------|
| `triage_status` column in database | ✅ Implemented |
| PATCH endpoint for triage updates | ✅ Implemented |
| Backend sync for triage status | ✅ Implemented |
| BFF route for triage PATCH | ✅ Implemented |
| Multi-select confidence_level filter | ✅ Implemented |
| Extended stats | ✅ Implemented |
| ML eval metadata in BFF response | ✅ Implemented |
| USE_MOCK_API toggle | ✅ Implemented |
| Auth boundary on all BFF handlers | ✅ Implemented |
| Supabase-backed app runtime | ✅ Implemented |
| Internal WAF ingest endpoint | Verified local proof; `POST /api/internal/waf-events` and transaction lookup returned `found=true` with source/request metadata and `crs_score=5` |
| WAF JSONL bridge tooling | Verified local proof; `scripts/waf_audit_bridge.py` followed the live ModSecurity JSON audit log and posted `status=200` |
| Demo-target WAF bridge tooling | Verified local proof; `demo-target-bridge` posted transaction `178249138618.813428` from `localhost:8089` and backend lookup returned `/records/search`, `SQL Injection`, `BLOCKED`, `crs_score=15` |
| Bounded WAF inference queue | Implemented; `web_app/application/inference_queue.py` gates synchronous WAF inference and `/api/ml-health` exposes queue health |
| Request/trace correlation | Implemented; handled and generic unhandled `500` responses return `X-Request-ID`, and valid W3C version-00 `traceparent` IDs are preserved |
| Structured observability logs | Implemented for backend request/WAF/prediction boundaries, bridge operational/configuration events, and login/route-guard audit events; recursive sensitive-field redaction is tested |
| Action policy values | Partial; actions are recorded, not proven as live request-path enforcement |

## Summary: Verified WAF Proof (2026-06-22)

| Check | Result |
|-------|--------|
| WAF public proof path | `localhost:8088` |
| Backend Docker exposure | internal-only, shown as `8000/tcp` |
| WAF `/healthz` | HTTP 200 |
| WAF `/api/health` | HTTP 200; `{"status":"healthy","database":"connected"}` |
| SQLi probe | `/api/health?id=17%27%20OR%2017%3D17--` returned HTTP 403 |
| ModSecurity transaction | `17821639659.909603` |
| Bridge post | `status=200`, rules `942100`, `949110` |
| Backend lookup | `found=true`, `prediction=SQL Injection`, `confidence_level=HIGH`, `action_taken=BLOCKED` |
| Correlation metadata | `source_ip=172.21.0.1`, `request_path=/api/health`, URL-encoded `query_string` present |
| CRS score | `5` |
| Targeted tests | bridge `37 passed`, WAF ingest route `11 passed`, WAF ingest use-case `4 passed`; combined `52 passed` |
| Follow-mode resilience | transient bridge `readline()` `OSError` recovery is implemented and unit-tested |

## Summary: Verified Demo-Target WAF Proof (2026-06-25)

| Check | Result |
|-------|--------|
| Realistic demo WAF path | `localhost:8089` |
| Protected demo target | separate land-records-portal on host port `3010` |
| Home request | HTTP 200 |
| SQLi marker | `SMOKE002945` returned HTTP 403 |
| Demo-target audit transaction | `178249138618.813428` |
| Demo-target audit host | `localhost:8089` |
| Demo-target audit request path | `/records/search` |
| Bridge post | `demo-target-bridge` posted `status=200` |
| Backend lookup | `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `crs_score=15` |
| Regression check | `localhost:8088` SQLi smoke still returned HTTP 403 |

## Summary: Client Requirements

| Requirement | Current Status |
|-------------|----------------|
| Secure login with named user accounts | Implemented for the env-backed capstone foundation |
| Admin/Analyst/Viewer RBAC | Server-side BFF enforcement implemented; alerts UI role affordances are implemented for viewers, analysts, and admins |
| 2FA | Planned |
| Timely push-style dashboard alerts | Planned |
| Email notification after detection | Planned |
| `CRITICAL >=90%` confidence tier | Implemented |

## Summary: Deferred Or Conditional

| Item | Current Status |
|------|----------------|
| Redis-backed enforcement state | Conditional; use only if shared runtime state is required |
| Wazuh full SIEM deployment | Deferred; export-only compatibility is the PD2-sized path |
| Kubernetes/Helm/Terraform | Deferred for PD2 |
| Kafka/Celery/Elasticsearch | Deferred for PD2 |
