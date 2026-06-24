# Architecture

Last updated: 2026-06-23

This document describes the current repository architecture. It distinguishes between what is implemented now and what remains planned.

Client-stated security and alerting requirements are tracked in `docs/client-requirements.md`. They are architectural drivers for planned account security and alerting work, but not all are implemented in the current repository state.

## Current Topology

```mermaid
flowchart LR
    Browser["Browser"] --> Next["Next.js 16 App Router"]
    Next --> BFF["Route Handlers / BFF"]
    BFF --> FastAPI["FastAPI API"]
    FastAPI --> Model["ModelService"]
    FastAPI --> DB["Async SQLAlchemy DB"]
    Model --> Registry["ml_model/model_registry/"]
    DB --> Supabase["Supabase PostgreSQL"]

    SQLite["SQLite (tests / isolated local work)"] -. optional .-> DB
    WAFProof["localhost:8088 WAF proof path"] --> ModSec["ModSecurity + OWASP CRS"]
    ModSec --> Bridge["WAF audit bridge"]
    Bridge --> FastAPI
    Redis["Redis 7"] -. planned .-> FastAPI
```

## Feature State Matrix

| Feature | Current State | Evidence |
|---|---|---|
| Browser dashboard path | Implemented | `frontend/app/api/*`, `frontend/proxy.ts`, `frontend/lib/bff-client.ts` |
| FastAPI routes and BFF calls | Implemented | `web_app/presentation/api/routes.py`, `frontend/app/api/*` |
| ModelService runtime boundary | Implemented | `web_app/services/model_service.py` |
| WAF ingest endpoint | Verified local proof | `POST /api/internal/waf-events`, `GET /api/internal/waf-events/{transaction_id}`, targeted route tests `8 passed` |
| WAF JSONL bridge | Verified local proof | `scripts/waf_audit_bridge.py`; targeted bridge tests `34 passed`; live bridge posted `status=200` for transaction `17821639659.909603` |
| ModSecurity request path | Verified local proof | `localhost:8088` through ModSecurity/OWASP CRS blocked SQLi with HTTP 403 and wrote JSON audit log |
| Backend Compose exposure | Implemented | backend is internal-only in Compose and shown as `8000/tcp`; proof lookup uses `docker compose exec`, not `localhost:8000` |
| Inference queue | Planned | no runtime `asyncio.Queue(maxsize=N)` ingestion queue found |
| Real-time dashboard alerts | Planned | no SSE/EventSource implementation found |
| Email notifications | Planned | no transactional email integration found |
| RBAC secure login | Planned | current `frontend/auth.ts` is demo credentials auth without roles |
| 2FA/MFA | Planned | no factor enrollment/challenge/recovery flow found |
| `CRITICAL >=90%` confidence tier | Planned | current contracts expose LOW/MEDIUM/HIGH only |
| Runtime enforcement | Partial | `action_taken` is recorded; no request-path block/throttle/challenge enforcement found |
| Retraining pipeline | Planned | `ml_model/retraining/README.md` documents design-level only |
| Wazuh export | Planned | no Wazuh JSON/JSONL export implementation found |
| Full Wazuh/SIEM, Kubernetes, Kafka/Celery/Elasticsearch | Deferred | PD2 scope keeps these out unless explicitly approved |

## Backend

### Layering

The backend follows the intended Clean Architecture split:

- `web_app/domain/`
  - Domain contracts and entities
- `web_app/application/`
  - Use cases such as triage and feedback
- `web_app/infrastructure/`
  - Database setup and repository implementations
- `web_app/presentation/`
  - FastAPI app factory, route handlers, and request/response schemas

### Runtime entrypoint

- App factory: `web_app.presentation.app:create_app`
- Lifespan startup initializes the database and loads `ModelService`

### Current routes (2026-03-23)

- Protected by backend bearer auth:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `PATCH /api/alerts/{id}/triage`
  - `GET /api/stats`
  - `GET /api/ml-health`
- Internal bearer-token protected backend endpoints:
  - `POST /api/internal/waf-events`
  - `GET /api/internal/waf-events/{transaction_id}`
  - `POST /api/feedback`
- Public backend endpoints:
  - `GET /health`
  - `GET /api/health`

### Model loading behavior

- `web_app/services/model_service.py` is the runtime model boundary.
- In production mode, `MODEL_REGISTRY_PATH` must point to an explicit model run directory.
- In development and testing, the service can resolve the latest staged run from a broader directory, or fall back to a mock service if the configured path does not exist.
- The active model artifact tree is under `ml_model/model_registry/`.

## Frontend

### App structure

- Framework: Next.js 16 App Router
- Auth: Auth.js credentials provider with JWT sessions
- Data layer: TanStack Query + Zod
- Client state: Zustand

### Client-Required Account Security

The current Auth.js credentials flow is a demo-oriented foundation. Client requirements now call for:

- secure login backed by real user access management,
- RBAC for role-specific access such as Admin and Analyst,
- strong account security controls,
- 2FA.

These are planned requirements. They should be implemented by extending the existing Auth.js boundary or by selecting a managed auth provider, not by hand-rolling session handling.

### Security boundary

The intended boundary is:

```text
Browser -> Next.js Route Handler -> FastAPI
```

This remains the correct direction for the project. Browser-to-FastAPI direct calls are not part of the intended architecture.

Next.js route handlers remain the browser-facing boundary, but the implemented handlers are not anonymous: the dashboard BFF handlers call `auth()` and return `401` without a valid session. They are still the right place to proxy or reshape backend data for the dashboard.

### Current BFF status (2026-03-23)

- `frontend/lib/bff-client.ts` is the shared server-only BFF client.
- All five route handlers wired:
  - `frontend/app/api/alerts/route.ts` (GET list)
  - `frontend/app/api/alerts/[id]/route.ts` (GET detail)
  - `frontend/app/api/alerts/[id]/triage/route.ts` (PATCH triage)
  - `frontend/app/api/stats/route.ts`
  - `frontend/app/api/ml-health/route.ts`
- Those five handlers all require a valid Auth.js session via `auth()`.
- `USE_MOCK_API` is the single centralized server-only mock toggle (currently **false**).
- The BFF validates transport payloads with Zod and preserves backend-emitted `action_taken` values: `BLOCKED`, `THROTTLED`, `ALLOWED`.
- `frontend/proxy.ts` is the active edge entrypoint for protected dashboard routes.

## Data and Persistence

### Current database reality

- Async SQLAlchemy is the persistence layer today
- The ORM model is `TrafficLog`
- Tests use SQLite
- Isolated local work can still use SQLite when needed
- The current app runtime is wired to Supabase-backed PostgreSQL
- Some Supabase policy and operational guardrails still live outside repo automation

## ML Artifacts and Training Config

- Staged artifacts live under `ml_model/model_registry/staging/`
- Evaluation outputs live under `ml_model/model_registry/eval/`
- Model configs live under `config/models/`
- Current runtime defaults align with the DistilBERT staging path and the locked confidence thresholds

## What Is Present But Not Yet The Primary Runtime Path

- A local `docker-compose.yml`
- Backend and frontend Dockerfiles
- A verified local Compose ModSecurity + OWASP CRS proof path through `localhost:8088`
- Internal WAF event ingest route and JSONL bridge tooling

## What Is Planned, Not Implemented

- Production-grade ModSecurity-fronted deployment
- Bounded `asyncio.Queue` for WAF-event/inference burst protection
- Redis-backed IP blocklist, rate-limit state, and low-confidence queue only if shared runtime state is required
- Full repo-managed export and automation of Supabase policy state
- Client-required real user access management, RBAC, and secure login
- Client-required 2FA
- Client-required email notifications after detection
- Client-standard `CRITICAL >=90%` confidence tier
- Wazuh export-only JSON/JSONL integration
- Production edge checklist, backup/restore runbook, and archive/hide retention policy

## Current limitations

- `PROCESSING` placeholder rows are hidden from normal alerts and stats reads. Expired leases are automatically reclaimed via the `lease_expires_at` field when a later request finds the lease stale.
- `ModelService.predict()` still returns compatibility aliases such as `class` and `confidence_level` alongside the canonical `prediction` and `confidence_tier` fields.
- The dashboard still relies on BFF-derived display fields for some stats and ML-health cards because the backend payloads intentionally stay narrower than the frontend contract.
- Current confidence tier and frontend severity contracts do not include `CRITICAL`.
- Current action values are recorded metadata, not proof of live network enforcement.
- Bridge follow mode has a resilience TODO for a transient `OSError: [Errno 5] Input/output error` observed at `readline()`; the container restarted and successfully posted afterward.

## Architecture Notes For Future Edits

- Do not document planned infrastructure as shipped behavior.
- Keep the live path names exact. Runtime artifacts live under `ml_model/model_registry/`.
- Keep setup docs and architecture docs synchronized with the route handlers and tests, not with older planning files.
- Latest operator baseline is tracked in `docs/project-ops/STATUS.md`; do not copy old test counts forward without rerunning.
