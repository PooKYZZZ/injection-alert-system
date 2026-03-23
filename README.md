# Injection Alert System

Injection Alert System is an academic capstone project for SQL injection detection and analyst triage. The repository combines a FastAPI backend, a Next.js dashboard, transformer-based ML artifacts, and a Supabase-backed app runtime for a hybrid WAF-plus-ML workflow.

## Status

This repository is active and deployable in its current app-plus-BFF form, but it is not yet the full Docker/ModSecurity/Redis local stack.

- Backend tests currently pass: `264 passed` (run with `.venv\Scripts\python.exe -m pytest -q`)
- Frontend tests currently pass: `122 passed` (run with `cd frontend && npx vitest run`)
- Frontend typecheck currently passes: `cd frontend && npm run typecheck`
- Frontend lint currently passes: `cd frontend && npm run lint`
- Frontend build currently passes: `cd frontend && npm run build`
- The dashboard BFF routes for alerts, alert detail, triage, stats, and ML health are wired to FastAPI in non-mock mode
- Supabase is the active hosted database boundary for the app runtime
- Docker Compose, runnable ModSecurity wiring, and Redis-backed enforcement are still in progress

If you need the current implementation truth rather than the thesis target architecture, start with [docs/CONTEXT.md](docs/CONTEXT.md) and [docs/architecture.md](docs/architecture.md).

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

In the current repo, the application code, model-loading path, tests, dashboard shell, and Supabase-backed runtime path are present, but the full WAF deployment path is not wired end to end yet.

## Current Repository Scope

### Implemented now

- FastAPI app factory and health endpoints
- Backend routes for:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
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

### Not fully implemented yet

- End-to-end ModSecurity or CRS bridge
- Docker Compose based local stack
- Redis-backed enforcement state

## Tech Stack

| Layer | Current stack |
|---|---|
| Frontend | Next.js 16, TypeScript 5, Auth.js, TanStack Query, Zustand, Zod |
| Backend | FastAPI 0.135, SQLAlchemy 2.0, Pydantic 2.12, Python 3.14 |
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
- Public backend endpoints:
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`

### Current auth split

- Frontend dashboard routes under `frontend/app/(dashboard)/` are session-protected.
- `frontend/proxy.ts` additionally matches `/dashboard`, `/alerts`, and `/ml-health`.
- Next.js BFF handlers under `frontend/app/api/alerts`, `frontend/app/api/stats`, and `frontend/app/api/ml-health` also call `auth()` and return `401` without a session.
- Backend internal data routes use `Authorization: Bearer <API_SECRET_KEY>` via the Next.js BFF client.
- Local `next start` validation also requires `AUTH_TRUST_HOST=true` in `frontend/.env.local`.

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

This repository is maintained as part of Team 13's capstone work for the Injection Alert System project. The academic design documents in [docs/feasibility_report.md](docs/feasibility_report.md) contain the broader project context.

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
