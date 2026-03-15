# Local Setup

Last updated: 2026-03-15

This guide reflects the repo as it exists now. It supports local backend and frontend development. It does not assume Docker Compose, ModSecurity, Redis, or Supabase are already wired in this repository.

## Prerequisites

- Windows PowerShell
- Python 3.10+
- Node.js 20+
- npm

## 1. Clone And Enter The Repo

```powershell
git clone <your-remote-url>
cd injection-alert-system
```

## 2. Backend Setup

### Create a virtual environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, either adjust execution policy for the current user or call the venv executables directly.

### Install Python dependencies

```powershell
.venv\Scripts\pip.exe install -r requirements.txt
```

### Create `.env`

The backend currently reads settings from `.env`. A minimal local development file looks like this:

```dotenv
DATABASE_URL=sqlite+aiosqlite:///./dev.db
APP_ENV=development
LOG_LEVEL=INFO
MODEL_PATH=ml_model/models/mock_model.py
MODEL_REGISTRY_PATH=
API_SECRET_KEY=local-dev-secret
GROQ_API_KEY=
ALLOWED_ORIGINS=["http://localhost:3000"]
```

Notes:

- `MODEL_PATH` still exists in config for compatibility.
- `MODEL_REGISTRY_PATH` controls the real runtime model service.
- If `MODEL_REGISTRY_PATH` is empty or missing in development, startup falls back to the mock model service with a warning.
- If you want the real staged model, use an explicit run directory such as:

```dotenv
MODEL_REGISTRY_PATH=ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755
```

### Run tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

As of 2026-03-15, this passes with `84` tests.

### Start the backend

```powershell
uvicorn web_app.presentation.app:create_app --reload
```

Backend entrypoint:

- `http://localhost:8000/health`
- `http://localhost:8000/api/health`

Current API surface:

- `POST /api/predict`
- `POST /api/triage`
- `GET /api/alerts`
- `GET /api/alerts/{id}`
- `GET /api/stats`
- `GET /api/ml-health`
- `POST /api/feedback`

## 3. Frontend Setup

### Install dependencies

```powershell
cd frontend
npm install
```

### Create `frontend/.env.local`

Use a local file with the variables the current frontend actually reads:

```dotenv
AUTH_SECRET=replace-me
SOC_DEMO_PASSWORD=demo1234
FASTAPI_BASE_URL=http://localhost:8000
INTERNAL_API_KEY=local-dev-secret
GROQ_API_KEY=
USE_MOCK_API=false
NEXT_PUBLIC_APP_ENV=development
NEXT_PUBLIC_APP_VERSION=0.0.0-LOCAL
```

Notes:

- `AUTH_SECRET` is the Auth.js signing secret.
- The login flow currently checks a password only.
- `SOC_DEMO_PASSWORD` is preferred. The code also falls back to `DEMO_PASSWORD`, then `demo1234` in development.
- `INTERNAL_API_KEY` must match backend `API_SECRET_KEY` for BFF-to-FastAPI requests.
- `USE_MOCK_API` is the only server-side mock toggle for alerts, alert detail, stats, and ML health.
- Keep backend-only values unprefixed. Do not add `NEXT_PUBLIC_` to server-only secrets.

### Start the frontend

```powershell
cd frontend
npm run dev
```

### Validate types

```powershell
cd frontend
npm run typecheck
```

As of 2026-03-15, typecheck passes cleanly.

### Run focused frontend BFF tests

```powershell
cd frontend
npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts
```

## 4. Current Frontend Data Reality

Be explicit about the current BFF status:

- `/api/stats`
  - Wired through `frontend/lib/bff-client.ts`
  - Calls real FastAPI in non-mock mode
- `/api/alerts`
  - Wired through `frontend/lib/bff-client.ts`
  - Calls real FastAPI in non-mock mode
- `/api/alerts/[id]`
  - Wired through `frontend/lib/bff-client.ts`
  - Calls real FastAPI in non-mock mode
- `/api/ml-health`
  - Wired through `frontend/lib/bff-client.ts`
  - Calls real FastAPI in non-mock mode

So the current local dashboard can run fully against the backend, with optional centralized mock mode via `USE_MOCK_API=true`.

## 5. What This Setup Does Not Cover

The following are not yet available as runnable repo-level setup paths:

- `docker compose up --build`
- ModSecurity + CRS local runtime
- Redis-backed review queue or enforcement state
- Live Supabase wiring
- Richer backend-native dashboard stats and ML-health payloads beyond the current BFF normalization layer

## 6. Troubleshooting

### Backend starts with a mock model unexpectedly

- Check `MODEL_REGISTRY_PATH`
- In development, a missing path falls back to mock mode
- In production mode, a missing path raises at startup

### Frontend cannot reach backend

- Check `FASTAPI_BASE_URL`
- Check that `INTERNAL_API_KEY` matches backend `API_SECRET_KEY`
- If you intentionally want UI-only local work, set `USE_MOCK_API=true`
- Make sure the backend is running before starting full-stack local work

### Typecheck or test results differ from this doc

Re-run:

```powershell
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run typecheck
npx vitest run app/api/bff-routes.test.ts lib/bff-client.test.ts
```

If those outputs change, update this file and `docs/CONTEXT.md` in the same change.
