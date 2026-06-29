# Local Setup

Last updated: 2026-06-27

This guide reflects the repo as it exists now. It supports direct local development, a Docker-based CyberTrace smoke path, and a final realistic WAF demo path. Docker Compose and ModSecurity now exist in the repo. The dashboard browser boundary remains `Browser -> Next.js -> FastAPI`; the technical CyberTrace WAF proof path uses `localhost:8088`, and the realistic protected demo website path uses `localhost:8089` with the separate land-records portal built as the `demo-portal` service.

Client-stated PD2 requirements are recorded in `docs/client-requirements.md`. The `CRITICAL >=90%` confidence tier is implemented; the current setup still uses demo-oriented credentials auth, while secure login, RBAC, 2FA, timely alerts, and email notification remain final client-scope gaps.

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

### Promote the staged DistilBERT artifact safely

Use the promotion CLI to replace the active staged artifact via archive-and-recreate while preserving the active path name.

Dry-run first:

```powershell
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run ^
  --source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" ^
  --active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" ^
  --archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" ^
  --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" ^
  --archive-suffix "pre_20260420" ^
  --dry-run
```

Real promotion (remove `--dry-run`):

```powershell
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run ^
  --source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" ^
  --active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" ^
  --archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" ^
  --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" ^
  --archive-suffix "pre_20260420"
```

This workflow writes sidecar provenance files (`provenance.json`, `MODEL_CARD.md`) and does not rename the active staged run directory.

### Run tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

As of 2026-04-20, this passes with **336 backend tests**.

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
- Client requirements call for this demo login to be replaced or extended with real user access management, RBAC, strong account security, and 2FA.

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

- Production-grade ModSecurity-fronted deployment
- Redis-backed review queue or enforcement state
- Richer backend-native dashboard stats and ML-health payloads beyond the current BFF normalization layer
- Automatic repo-managed export of Supabase policies and operational guardrails
- Real user access management with secure login, RBAC, and 2FA
- Email notification after detection

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
- `modsecurity` publishes the WAF proof path on `http://localhost:8088`
- `backend` is internal only and should show `8000/tcp`
- `frontend` talks to `backend` using `FASTAPI_BASE_URL=http://backend:8000`
- `modsecurity` proxies to `backend` using `BACKEND=http://backend:8000`

This means:

- Browser path today: `Browser -> frontend -> backend`
- WAF proof path today: `localhost:8088 -> modsecurity -> backend`
- Backend transaction lookup proof: `docker compose exec backend ...`

Do not use `localhost:8000` for Docker proof unless backend port 8000 is explicitly published.

### Final realistic demo-target stack

For normal developer startup, the demo-target profile is not required. For the final realistic WAF demonstration, start this repo with the demo-target profile:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml --profile demo-target up -d --build
```

By default, the profile builds the protected demo website from the sibling path `../../land-records-portal`, which resolves to `G:\AI\land-records-portal` from this repo layout. If your portal checkout is elsewhere, set `DEMO_PORTAL_CONTEXT` before running Compose.

Expected path:

```text
localhost:8089
-> demo-target-modsecurity
-> demo-portal on the Compose network port 3010
-> logs/modsecurity/demo-target/modsec_audit.jsonl
-> demo-target-bridge
-> FastAPI internal WAF ingest
-> ML triage
-> dashboard/backend lookup
```

The land-records-portal source stays separate from this repository. This repo's Compose override references it as a build context; it does not merge the portal source into CyberTrace. The portal runs as a production Next.js standalone container with `HOSTNAME=0.0.0.0` and `PORT=3010`, and port `3010` is internal to the Compose network unless explicitly changed for debugging. `demo-target-bridge` is required when `8089` events must appear in CyberTrace.

Latest verified local proof: `/records/search` SQLi marker `SMOKE002945` returned HTTP 403 through `localhost:8089`; `demo-target-bridge` posted transaction `178249138618.813428`; backend lookup returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, and `crs_score=15`.

### Backend health checks in Docker

The backend image does not include `curl`, so use Python from inside the container:

```powershell
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)"
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').status)"
```

### Verified WAF proof flow

Use these commands for the ModSecurity/OWASP CRS proof path:

```powershell
Invoke-WebRequest -UseBasicParsing "http://localhost:8088/healthz"
Invoke-WebRequest -UseBasicParsing "http://localhost:8088/api/health"
Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck "http://localhost:8088/api/health?id=17%27%20OR%2017%3D17--"
```

Expected proof result:

- `/healthz` through `localhost:8088` returns HTTP 200.
- `/api/health` through `localhost:8088` returns HTTP 200.
- SQLi probe through `localhost:8088` returns HTTP 403.
- ModSecurity writes JSON audit evidence to `logs/modsecurity/modsec_audit.jsonl`.
- The bridge posts to `http://backend:8000/api/internal/waf-events`.

Backend transaction lookup is Docker-internal:

```powershell
$txid = "<paste transaction.unique_id>"
if ([string]::IsNullOrWhiteSpace($txid)) { throw "txid missing" }
docker compose exec -e TXID=$txid backend python -c "import os, urllib.request; txid=os.environ['TXID']; secret=os.environ['API_SECRET_KEY']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', headers={'Authorization': 'Bearer ' + secret}); print(urllib.request.urlopen(req).read().decode())"
```

Verified result for transaction `17821639659.909603`: `found=true`, `prediction=SQL Injection`, `confidence_level=HIGH`, `action_taken=BLOCKED`, `source_ip=172.21.0.1`, `request_path=/api/health`, URL-encoded `query_string`, `crs_score=5`, and rules `942100`, `949110`.

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
