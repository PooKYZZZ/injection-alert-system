# Local Setup

This guide covers direct local development, not hosted deployment or production
operations.

## Requirements

- Windows PowerShell
- Python 3.14
- Node.js 24 and npm
- Docker Desktop only for Compose or Docker-backed tests

Run commands from the repository root unless noted.

## Configure local environment

Copy each template only when its ignored local file does not already exist:

```powershell
New-Item -ItemType Directory -Force .local/env | Out-Null
if (-not (Test-Path .local/env/.env)) { Copy-Item .env.example .local/env/.env }
if (-not (Test-Path frontend/.env.local)) { Copy-Item frontend/.env.example frontend/.env.local }
```

Edit only these local copies. The backend template defaults to SQLite; local
Compose uses a private PostgreSQL service and requires `LOCAL_POSTGRES_PASSWORD`.
Do not connect local development to a shared or production database.

Dashboard sign-in requires a dedicated non-production Supabase project, its
server-only `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` in
`frontend/.env.local`, and an already provisioned test account. Never expose
the service-role key with a `NEXT_PUBLIC_` variable. `USE_MOCK_API` mocks data;
it does not bypass sign-in or create an account. Generate the Auth.js secret
after installing frontend dependencies with `npx auth secret`.

For real (non-mock) dashboard data, set a non-empty backend `API_SECRET_KEY`
in `.local/env/.env` and the identical frontend `INTERNAL_API_KEY` in
`frontend/.env.local`. Generate a local value with:

```powershell
py -3.14 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Keep it in the ignored files; never commit or share it. Direct local frontend
runs use `FASTAPI_BASE_URL=http://127.0.0.1:8000`; inside Docker, use the
backend service hostname instead of `localhost`.

## Run locally

Start the backend from the repository root:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m uvicorn --factory web_app.presentation.app:create_app --reload
```

Health endpoints: `http://localhost:8000/health` and
`http://localhost:8000/api/health`. The app reads `.local/env/.env`; startup is
not a method for migrating a hosted database.

In a second PowerShell window, start Next.js:

```powershell
cd frontend
npm ci
npx auth secret
npm run dev
```

Open `http://localhost:3000/login`. A valid account is still required when
mock dashboard data is enabled.

## Verify changes

From the repository root:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

From `frontend/`:

```powershell
npm run lint
npm run typecheck
npx vitest run
npm run build
```

The optional browser authentication suite (`npm run test:e2e:auth` from
`frontend/`) has additional local prerequisites. These are verification
commands, not claims that the current checkout passed; consult
[`project-ops/STATUS.md`](project-ops/STATUS.md) for dated results.

## Docker and related guides

Use the [Docker Compose guide](../docker/compose/README.md) for the ordinary
local stack and the [smoke-test runbook](project-ops/SMOKE_TEST_RUNBOOK.md) for
optional WAF/demo profiles. Local checks do not prove hosted routing or
production enforcement. Follow the [migration runbook](project-ops/MIGRATION_ROLLBACK_RUNBOOK.md)
for database changes and the [ML operations runbook](project-ops/ML_MODEL_OPERATIONS_RUNBOOK.md)
for model workflows.

## Troubleshooting

- **Compose PostgreSQL fails to start:** set `LOCAL_POSTGRES_PASSWORD` in the
  ignored backend environment file.
- **Dashboard data fails:** check `FASTAPI_BASE_URL` and ensure
  `INTERNAL_API_KEY` matches `API_SECRET_KEY` exactly.
- **Sign-in fails:** verify the non-production Supabase settings, Auth.js
  secret, and provisioned account. Mock data does not replace authentication.
- **WAF/demo check fails:** follow the selected profile's steps in the
  [smoke-test runbook](project-ops/SMOKE_TEST_RUNBOOK.md).
