# Injection Alert System

Injection Alert System is an academic capstone project for SQL injection detection and analyst triage. The repository combines a FastAPI backend, a Next.js dashboard, and transformer-based ML artifacts for a hybrid WAF-plus-ML workflow.

## Status

This repository is active, but it is not yet a full production deployment.

- Backend tests currently pass: `84 passed`
- Frontend typecheck currently passes: `npm run typecheck`
- The dashboard BFF routes for alerts, alert detail, stats, and ML health are wired to FastAPI in non-mock mode
- Docker Compose, runnable ModSecurity wiring, and full Supabase/Redis integration are still in progress

If you need the current implementation truth rather than the thesis target architecture, start with [docs/CONTEXT.md](docs/CONTEXT.md) and [docs/architecture.md](docs/architecture.md).

## What The Project Does

The target system is a CRS-first security workflow:

```text
Browser -> Next.js route handlers -> FastAPI -> model service -> database
```

The broader capstone goal is:

- inspect flagged HTTP requests
- classify likely attack traffic with an ML model
- apply a confidence tier
- surface alerts to a dashboard for review and feedback

In the current repo, the application code, model-loading path, tests, and dashboard shell are present, but the full WAF deployment path is not wired end to end yet.

## Current Repository Scope

### Implemented now

- FastAPI app factory and health endpoints
- Backend routes for:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `GET /api/stats`
  - `GET /api/ml-health`
  - `POST /api/feedback`
- Next.js 15 dashboard app with Auth.js credentials authentication
- Route-handler BFF layer for dashboard data access
- Runtime model loading through `web_app/services/model_service.py`
- Staged model artifacts under `ml_model/model_registry/`
- Alembic scaffolding and the current triage-processing migration set

### Not fully implemented yet

- End-to-end ModSecurity or CRS bridge
- Docker Compose based local stack
- Redis-backed enforcement state
- Fully wired Supabase production boundary

## Tech Stack

| Layer | Current stack |
|---|---|
| Frontend | Next.js 15, TypeScript 5, Auth.js, TanStack Query, Zustand, Zod |
| Backend | FastAPI, async SQLAlchemy |
| ML | PyTorch, Hugging Face Transformers |
| Data | SQLite for tests and local development, PostgreSQL/Supabase as target production boundary |
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

- Python 3.10+
- Node.js 20+
- npm
- PowerShell or a compatible shell

### Backend

```powershell
python -m venv .venv
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
uvicorn web_app.presentation.app:create_app --reload
```

Before starting the backend, create a root `.env` file using the current variable guidance in [docs/SETUP.md](docs/SETUP.md).

### Frontend

```powershell
cd frontend
npm install
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
  - `GET /api/stats`
  - `GET /api/ml-health`
- Public backend endpoints:
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`

### Current auth split

- Frontend dashboard routes under `frontend/app/(dashboard)/` are session-protected.
- `frontend/middleware.ts` additionally matches `/dashboard`, `/alerts`, and `/ml-health`.
- Next.js BFF handlers under `frontend/app/api/alerts`, `frontend/app/api/stats`, and `frontend/app/api/ml-health` also call `auth()` and return `401` without a session.
- Backend internal data routes use `Authorization: Bearer <API_SECRET_KEY>` via the Next.js BFF client.

### Current limitations

- Stale `PROCESSING` triage reservations return `503` with `Retry-After`; they are surfaced safely but not auto-reclaimed.
- The dashboard still derives some stats and ML-health display fields in the BFF because backend payloads are intentionally thinner than the UI contract.
- `app.state.model` remains as a compatibility alias for `app.state.model_service`.

## Documentation

- [docs/CONTEXT.md](docs/CONTEXT.md)
  - current project status and implementation snapshot
- [docs/architecture.md](docs/architecture.md)
  - current architecture and planned gaps
- [docs/SETUP.md](docs/SETUP.md)
  - local setup and environment guidance
- [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)
  - contributor workflow and validation steps
- [docs/DATASET_RELEASE_SR_BH_CLEAN_v3.1.0.md](docs/DATASET_RELEASE_SR_BH_CLEAN_v3.1.0.md)
  - dataset release note
- [docs/DATASET_BASELINE_SR_BH_v3.1.0.md](docs/DATASET_BASELINE_SR_BH_v3.1.0.md)
  - dataset baseline and training metadata

## Support

- For local setup and environment questions, start with [docs/SETUP.md](docs/SETUP.md)
- For implementation status and known gaps, use [docs/CONTEXT.md](docs/CONTEXT.md)
- For architecture questions, use [docs/architecture.md](docs/architecture.md)
- For contribution workflow, use [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md)

## Development Notes

- Keep implementation docs aligned with code and tests
- Use relative links inside repository documentation
- Do not document planned behavior as if it is already live
- Do not hardcode secrets in code or docs

## Maintainers

This repository is maintained as part of Team 13's capstone work for the Injection Alert System project. The academic design documents in [docs/feasibility_report.md](docs/feasibility_report.md) contain the broader project context.

## Contributing

See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md).

At minimum, run:

```powershell
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run typecheck
```

## License

No repository license file is currently present. Do not assume the project is MIT-licensed just because older drafts said so.
