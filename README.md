# Injection Alert System

Injection Alert System is an academic capstone project for SQL injection detection and analyst triage. The repository combines a FastAPI backend, a Next.js dashboard, transformer-based ML artifacts, and a Supabase-backed app runtime for a hybrid WAF-plus-ML workflow.

## Status

This repository is active in its current app-plus-BFF form and now has a verified local ModSecurity/OWASP CRS proof path for WAF ingest. It is still not a finished production Docker/Redis deployment target.

- Backend tests currently pass: `.venv\Scripts\python.exe -m pytest -q`
- Frontend tests currently pass: `cd frontend && npx vitest run`
- Frontend typecheck currently passes: `cd frontend && npm run typecheck`
- Frontend lint currently passes: `cd frontend && npm run lint`
- Frontend build currently passes: `cd frontend && npm run build`
- Latest verification counts are recorded in [docs/project-ops/STATUS.md](docs/project-ops/STATUS.md).
- PR #84 is frozen at trusted WAF source correlation. CI, controlled proof,
  hosted Wi-Fi/mobile source correlation, forged-header resistance, and
  restart/recreate proof passed; hosted `VERIFIED` mode intentionally remains
  disabled pending final Cloudflare/origin trust checks. Later roadmap work is
  not part of this PR.
- PR #85 SSE synchronization is implemented and manually verified for
  no-refresh alerts, browser reconnect/catch-up, and the named hosted domain.
  It remains single-process and in-memory with no durable replay, multi-worker
  fan-out, or latency benchmark.
- The dashboard BFF routes for alerts, alert detail, triage, stats, ML health, and the authenticated alert SSE stream are wired to FastAPI in non-mock mode
- Supabase is the active hosted database boundary for the app runtime
- Docker Compose and local container smoke paths exist
- Verified WAF proof path: `localhost:8088` -> ModSecurity/OWASP CRS -> JSON audit log -> bridge -> FastAPI internal WAF ingest
- Verified realistic demo-target path: `localhost:8089` -> demo-target ModSecurity/OWASP CRS -> `demo-target-app` built from the separate land-records portal repo -> demo-target audit log -> demo-target-bridge -> FastAPI internal WAF ingest
- Verified SQLi proof: `/api/health?id=17%27%20OR%2017%3D17--` through `localhost:8088` returned HTTP 403
- Verified backend lookup result for transaction `17821639659.909603`: `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `crs_score=5`, rules `942100` and `949110`, with `source_ip`, `request_path`, and URL-encoded `query_string` present
- In Compose, the backend is internal-only (`8000/tcp`). Do not use `localhost:8000` for WAF proof unless port 8000 is explicitly published.
- PR5 controlled local/test enforcement uses PostgreSQL fixed-window state and server-side Turnstile for LOW/MEDIUM `/records/search`; hosted/production `ENFORCE` remains disabled, and Redis/global enforcement are not implemented.

If you need the current implementation truth rather than the thesis target architecture, start with [docs/CONTEXT.md](docs/CONTEXT.md) and [docs/architecture.md](docs/architecture.md).

Client-stated PD2 requirements are tracked in [docs/client-requirements.md](docs/client-requirements.md). They include secure login, RBAC, 2FA, timely alerts, email notifications after detection, and the client confidence standard `CRITICAL >=90%`.

## What The Project Does

The current system boundary is:

```text
Browser -> Next.js route handlers -> FastAPI -> model service -> database
```

The broader capstone goal is:

- inspect flagged HTTP requests
- classify likely attack traffic with an ML model
- apply a confidence tier
- surface alerts to a dashboard for review and feedback

Current naming note: LOW, MEDIUM, HIGH, and CRITICAL are model confidence tiers. The preferred filter/query name is `confidence_tier`, the persisted backend field remains `confidence_level`, legacy `severity` URLs are kept for compatibility, `CRITICAL >=90%` is implemented as a confidence threshold, no retraining/recalibration/model artifact change was required, and historical rows are not retroactively reclassified. Persisted-alert dashboard grouping and confidence styling use the backend-emitted `confidence_level`; enforcement-policy counts exclude `Normal` predictions, which remain `ALLOWED` at every valid tier; confidence-tier badges always display the canonical tier rather than substituting prediction terminology.

In the current repo, the application code, model-loading path, tests, dashboard shell, Supabase-backed runtime path, Docker smoke setup, and local WAF ingest proof are present. The dashboard browser path remains `Browser -> Next.js -> FastAPI`; the technical WAF proof path is `localhost:8088`; the realistic final demo WAF path is `localhost:8089`, with the separate land-records portal built as the `demo-target-app` service from the sibling portal repo.

## Current Repository Scope

### Implemented now

- FastAPI app factory and health endpoints
- Backend routes for:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/stream`
  - `GET /api/alerts/{id}`
  - `PATCH /api/alerts/{id}/triage`
  - `GET /api/stats`
  - `GET /api/ml-health`
  - `POST /api/feedback`
- Next.js 16 dashboard app with Auth.js credentials authentication
- Route-handler BFF layer for dashboard data access
- Runtime model loading through `web_app/services/model_service.py`
- Staged model artifacts under `ml_model/model_registry/`
- Alembic scaffolding and the current triage-processing migration set
- Hosted PostgreSQL/Supabase runtime boundary for application data
- Verified local ModSecurity/OWASP CRS ingest proof through `localhost:8088`
- Verified local demo-target WAF ingest proof through `localhost:8089`
- Internal WAF ingest and transaction lookup endpoints protected by bearer auth
- Bounded in-process WAF inference queue and queue health visibility in ML health
- Structured JSON logs for backend request/WAF/prediction boundaries and bridge operations, with request/trace/transaction correlation and recursive sensitive-field redaction
- Safe `X-Request-ID` propagation on handled responses and generic unhandled `500` responses
- Supabase-backed named accounts with approved Argon2id PHC verification and
  fail-closed DB-backed RBAC freshness checks
- Marker-correlated final-demo smoke with optional required Docker-internal
  backend lookup
- Real-time dashboard cache synchronization: a finalized alert publishes a
  minimal `alert.created` SSE signal through the authenticated Next.js BFF;
  TanStack Query then refetches canonical alert and stats REST state. The
  broadcaster is in-process and supports the current single-backend-process
  runtime only.

### Not fully implemented yet

- Production-grade ModSecurity-fronted deployment
- Redis-backed enforcement state
- Client-required two-factor authentication
- Client-required email notification after threat detection

## Tech Stack

| Layer | Current stack |
|---|---|
| Frontend | Next.js 16, TypeScript 5, Auth.js, TanStack Query, Zustand, Zod |
| Backend | FastAPI 0.138.0, SQLAlchemy 2.0, Pydantic 2.12, Python 3.14 |
| ML | PyTorch, Hugging Face Transformers |
| Data | SQLite for tests and isolated local work, PostgreSQL/Supabase as the active hosted runtime boundary |
| Docs | Markdown in-repo docs under `docs/` |

## Repository Layout

```text
frontend/     Next.js dashboard and BFF route handlers
web_app/      FastAPI backend
ml_model/     training, inference, export, and staged artifacts
config/       model and environment configuration
docs/         maintained project documentation
tests/        backend unit and integration tests
migrations/   Alembic migrations
```

Important note:

- The active runtime model artifact path is `ml_model/model_registry/`

## Getting Started

Use [docs/SETUP.md](docs/SETUP.md) for the full setup guide. The short version is below.

### Prerequisites

- Python 3.14+ (tested with 3.14.3)
- Node.js 20+
- npm
- PowerShell or a compatible shell

### Backend

If you are using **Command Prompt (`cmd.exe`)**:

```cmd
py -3.14 -m venv .venv
call .\.venv\Scripts\activate.bat
python -m pip install -r requirements.txt
python -m pytest -q
python -m uvicorn web_app.presentation.app:create_app --reload
```

If you are using **PowerShell**:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe -m uvicorn web_app.presentation.app:create_app --reload
```

Before starting the backend, create a root `.env` file using the current variable guidance in [docs/SETUP.md](docs/SETUP.md).

### Frontend

If you are using **Command Prompt (`cmd.exe`)**:

```cmd
cd frontend
npm install
npm run lint
npm run typecheck
npm run dev
```

If you are using **PowerShell**:

```powershell
cd frontend
npm install
npm run lint
npm run typecheck
npm run dev
```

Before starting the frontend, create `frontend/.env.local` using the current variable guidance in [docs/SETUP.md](docs/SETUP.md).

### Docker smoke setup

The repo also supports a local Docker smoke path:

```powershell
docker compose up --build -d
docker compose ps
```

That default command starts only `backend` and `frontend`. Start the historical
technical WAF proof pair explicitly with:

```powershell
docker compose --profile technical-waf up --build -d
```

Important constraints:

- The frontend is published on `http://localhost:3000`
- The backend is internal to the Compose network and is not published to the host
- The opt-in technical WAF profile publishes its proof path on `http://localhost:8088`
- The realistic demo-target WAF path is published on `http://localhost:8089` when the `demo-target` profile is enabled; the profile also starts `demo-target-app` from the separate land-records portal repo
- The active browser path remains `Browser -> Next.js -> FastAPI`
- Backend transaction lookup proof should use `docker compose exec`, not `localhost:8000`

For the current container workflow, use [docs/SETUP.md](docs/SETUP.md) and [docs/project-ops/SMOKE_TEST_RUNBOOK.md](docs/project-ops/SMOKE_TEST_RUNBOOK.md).

## Usage

### Health check

```text
GET /health
GET /api/health
```

### Prediction example

```bash
curl -X POST "http://localhost:8000/api/predict" \
  -H "Authorization: Bearer <API_SECRET_KEY>" \
  -H "Content-Type: application/json" \
  -d "{\"http_request\":\"GET /login?id=1 OR 1=1 HTTP/1.1\"}"
```

### Current backend API surface

- Protected by backend bearer auth:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `PATCH /api/alerts/{id}/triage`
  - `GET /api/stats`
  - `GET /api/ml-health`
- Internal bearer-token protected backend endpoints:
  - `POST /api/feedback`
- Public backend endpoints:
  - `GET /health`
  - `GET /api/health`

### Current auth split

- Frontend dashboard routes under `frontend/app/(dashboard)/` are session-protected.
- `frontend/proxy.ts` additionally matches `/dashboard`, `/alerts`, and `/ml-health`.
- Next.js BFF handlers under `frontend/app/api/alerts`, `frontend/app/api/stats`, and `frontend/app/api/ml-health` also call `auth()` and return `401` without a session.
- Backend internal data routes use `Authorization: Bearer <API_SECRET_KEY>` via the Next.js BFF client.
- Local `next start` validation also requires `AUTH_TRUST_HOST=true` in `frontend/.env.local`.
- Client requirements now call for real user access management with RBAC, secure login, strong account security, and 2FA. The current password-only demo flow is not the final requirement state.

### Current limitations

- Stale `PROCESSING` triage reservations are automatically reclaimed via lease expiry (`lease_expires_at`); a later request can claim ownership when the lease has expired.
- The dashboard still derives some stats and ML-health display fields in the BFF because backend payloads are intentionally thinner than the UI contract.

## Documentation

- [docs/CONTEXT.md](docs/CONTEXT.md)
  - current project status and implementation snapshot
- [docs/architecture.md](docs/architecture.md)
  - current architecture and planned gaps
- [docs/SETUP.md](docs/SETUP.md)
  - local setup and environment guidance
- [docs/client-requirements.md](docs/client-requirements.md)
  - client-stated security, alerting, and confidence-tier requirements
- [CONTRIBUTING.md](CONTRIBUTING.md)
  - contributor workflow and validation steps
- [docs/CURRENT_SYSTEM_STATE.md](docs/CURRENT_SYSTEM_STATE.md)
  - detailed runtime and UI snapshot
- [docs/README.md](docs/README.md)
  - docs index

## Support

- For local setup and environment questions, start with [docs/SETUP.md](docs/SETUP.md)
- For implementation status and known gaps, use [docs/CONTEXT.md](docs/CONTEXT.md)
- For architecture questions, use [docs/architecture.md](docs/architecture.md)
- For contribution workflow, use [CONTRIBUTING.md](CONTRIBUTING.md)

## Development Notes

- Keep implementation docs aligned with code and tests
- Use relative links inside repository documentation
- Do not document planned behavior as if it is already live
- Do not hardcode secrets in code or docs

## Maintainers

This repository is maintained as part of Team 13's capstone work for the Injection Alert System project.

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

At minimum, run:

```powershell
# Backend tests
.venv\Scripts\python.exe -m pytest -q

# Frontend quality gates
cd frontend
npm run lint
npm run typecheck
npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts
npx vitest run
npm run build
```

## License

No repository license file is currently present. Do not assume the project is MIT-licensed just because older drafts said so.
