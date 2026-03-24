# Local Setup

Last updated: 2026-03-24

This guide reflects the repo as it exists now. It supports both direct local development and a Docker-based smoke path. Docker Compose and ModSecurity now exist in the repo, but the browser-facing runtime boundary still remains `Browser -> Next.js -> FastAPI`, not `Browser -> ModSecurity -> FastAPI`.

## Prerequisites

- Windows PowerShell
- Python 3.14+
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
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, either adjust execution policy for the current user or call the venv executables directly.

### Install Python dependencies

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Create `.env`

The backend currently reads settings from `.env`. Use your current Supabase PostgreSQL connection string for normal app runtime work. A minimal local development file looks like this:

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:<password>@<project-ref>.supabase.co:6543/postgres
APP_ENV=development
LOG_LEVEL=INFO
MODEL_PATH=ml_model/models/mock_model.py
MODEL_REGISTRY_PATH=
API_SECRET_KEY=local-dev-secret
GROQ_API_KEY=
ALLOWED_ORIGINS=["http://localhost:3000"]
CONFIDENCE_LOW_THRESHOLD=0.50
CONFIDENCE_HIGH_THRESHOLD=0.80
STALE_PROCESSING_TIMEOUT_SECONDS=30
MAX_SEQ_LEN=128
TEMPERATURE=0.596868
```

Notes:

- `MODEL_PATH` still exists in config for compatibility.
- `MODEL_REGISTRY_PATH` controls the real runtime model service.
- If `MODEL_REGISTRY_PATH` is empty or missing in development, startup falls back to the mock model service with a warning.
- `CONFIDENCE_LOW_THRESHOLD`, `CONFIDENCE_HIGH_THRESHOLD`, and `STALE_PROCESSING_TIMEOUT_SECONDS` are supported env overrides with locked current defaults.
- `MAX_SEQ_LEN`, `TEMPERATURE`, `LABEL_NAMES`, and `MODEL_VERSION` are also accepted by settings, but the repo currently relies on their defaults unless you are doing targeted backend or artifact validation work.
- SQLite is still fine for isolated local testing, but it is no longer the primary runtime path documented for the app.
- If you want the real staged model, use an explicit run directory such as:

```dotenv
MODEL_REGISTRY_PATH=ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755
```

### Run tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

As of 2026-03-23, this passes with **264 backend tests**.

### Start the backend

```powershell
.venv\Scripts\python.exe -m uvicorn web_app.presentation.app:create_app --reload
```

Backend entrypoint:

- `http://localhost:8000/health`
- `http://localhost:8000/api/health`

Current API surface:

- Protected by backend bearer auth:
  - `POST /api/predict`
  - `POST /api/triage`
  - `POST /api/internal/waf-events`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `PATCH /api/alerts/{id}/triage`
  - `GET /api/stats`
  - `GET /api/ml-health`
- Public backend endpoints:
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`

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
AUTH_TRUST_HOST=true
SOC_DEMO_PASSWORD=demo1234
DEMO_PASSWORD=
FASTAPI_BASE_URL=http://localhost:8000
INTERNAL_API_KEY=local-dev-secret
USE_MOCK_API=false
NEXT_PUBLIC_APP_ENV=development
NEXT_PUBLIC_APP_VERSION=0.0.0-LOCAL
```

Notes:

- `AUTH_SECRET` is the Auth.js signing secret. Keep `NEXTAUTH_SECRET` unset to avoid split secret sources.
- `AUTH_TRUST_HOST=true` is required for local `next start` validation so Auth.js trusts the local host.
- The login flow currently checks a password only.
- `SOC_DEMO_PASSWORD` is preferred. The code also falls back to `DEMO_PASSWORD`, then `demo1234` in development.
- `INTERNAL_API_KEY` must match backend `API_SECRET_KEY` for BFF-to-FastAPI requests.
- `USE_MOCK_API` is the only server-side mock toggle for alerts, alert detail, triage, stats, and ML health.
- Keep backend-only values unprefixed. Do not add `NEXT_PUBLIC_` to server-only secrets.

### Start the frontend

```powershell
cd frontend
npm run dev
```

### Validate types and lint

```powershell
cd frontend
npm run lint
npm run typecheck
```

As of 2026-03-23, both pass cleanly.

### Run focused frontend BFF tests

```powershell
cd frontend
npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts
```

### Run full frontend test suite

```powershell
cd frontend
npx vitest run
```

As of 2026-03-23, full suite passes with **122 frontend tests**.

### Validate production build

```powershell
cd frontend
npm run build
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
- `/api/alerts/[id]/triage` (PATCH)
  - Wired through `frontend/app/api/alerts/[id]/triage/route.ts`
  - Calls real FastAPI in non-mock mode
- `/api/ml-health`
  - Wired through `frontend/lib/bff-client.ts`
  - Calls real FastAPI in non-mock mode

So the current local dashboard can run fully against the backend, with optional centralized mock mode via `USE_MOCK_API=true`.

**Current state:** `USE_MOCK_API=false` - the dashboard is hitting the real FastAPI backend.

### Current frontend protection split

- `/login` is the public sign-in page.
- `/` redirects to `/login` or `/dashboard` based on session state.
- `frontend/app/(dashboard)/layout.tsx` protects the dashboard route group with a session check.
- `frontend/proxy.ts` additionally matches `/dashboard`, `/alerts`, and `/ml-health`.
- All five BFF handlers also call `auth()` and return `401` without a session.

## 5. What This Setup Does Not Cover

The following are not yet available as runnable repo-level setup paths:

- ModSecurity as the browser-facing runtime boundary
- Redis-backed review queue or enforcement state
- Richer backend-native dashboard stats and ML-health payloads beyond the current BFF normalization layer
- Automatic repo-managed export of Supabase policies and operational guardrails

## 5A. Docker Smoke Setup

### Required files

- Root `.env`
- `frontend/.env.local`

Those files are mounted into the containers via `docker-compose.yml`.

### Start the stack

```powershell
docker compose up --build -d
docker compose ps
```

Expected services:

- `frontend`
- `backend`
- `modsecurity`
- `bridge`

### Current Docker network truth

- `frontend` is published on `http://localhost:3000`
- `backend` is internal only
- `modsecurity` is published on `http://localhost:8088` for replay and smoke testing
- `frontend` talks to `backend` using `FASTAPI_BASE_URL=http://backend:8000`
- `modsecurity` proxies to `backend` using `BACKEND=http://backend:8000`

This means:

- Browser path today: `Browser -> frontend -> backend`
- Host replay path today: `localhost:8088 -> modsecurity -> backend`
- WAF ingest bridge path today: `bridge -> backend (/api/internal/waf-events)`

ModSecurity is connected to the backend, but it is not currently in front of browser traffic.

### WAF ingest bridge smoke check

The bridge reads JSON-lines events (fixture included at `scripts/fixtures/waf_event.jsonl`) and posts sanitized payloads to the internal ingest endpoint.

```powershell
docker compose logs bridge
```

Expected bridge output pattern:

- `bridge summary: total=... success=... failed=...`

Direct local unit validation without Compose:

```powershell
python3 -m pytest tests/scripts/test_waf_audit_bridge.py -q
python3 -m pytest tests/integration/test_waf_ingest_route.py -q
```

Important phase-1 limitation:

- This is detect-and-forward ingest only. No live blocking or throttling is enforced by the bridge.

### Backend health checks in Docker

The backend image does not include `curl`, so use Python from inside the container:

```powershell
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)"
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').status)"
```

### Frontend smoke check

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:3000 | Select-Object -ExpandProperty StatusCode
```

Expected result: `200`

### Running the demo seeder

The repo does track `seed_demo.py`, but it currently targets `http://127.0.0.1:8000`.

Implications:

- From the host machine, it will fail against Docker because the backend is not published to host port `8000`
- From inside the `backend` container, it talks directly to FastAPI and bypasses ModSecurity
- It does not currently exercise the ModSecurity path

To run it against the backend container directly:

```powershell
docker compose exec backend python seed_demo.py
```

### Stop the stack

```powershell
docker compose down
```

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
npm run lint
npm run typecheck
npx vitest run
npm run build
```

If those outputs change, update this file and `docs/CONTEXT.md` in the same change.
