# Render Deployment Runbook

This runbook is the fastest production path for the current repo shape:

Browser -> Next.js -> FastAPI -> Supabase Postgres

Use this when you want a public deployment quickly without redesigning the architecture.

The repo now also includes a Render blueprint in [render.yaml](render.yaml) plus production env templates in [.env.render.example](.env.render.example) and [frontend/.env.render.example](frontend/.env.render.example).

## Target Topology

- Frontend: Render Web Service using `frontend/Dockerfile`
- Backend: Render Web Service using root `Dockerfile`
- Database: existing Supabase PostgreSQL

Recommended public URLs:

- Frontend: `https://<frontend-service>.onrender.com`
- Backend: `https://<backend-service>.onrender.com`

## Before You Start

Have these values ready:

- Supabase Postgres connection string
- A strong `AUTH_SECRET`
- A strong `API_SECRET_KEY`
- A demo login password for `SOC_DEMO_PASSWORD`
- The deployed production model path for `MODEL_REGISTRY_PATH`

Current staged model paths available in this repo include:

- `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755`
- `ml_model/model_registry/staging/bert-base_v3_907k_cleaned_20260312_145113`
- `ml_model/model_registry/staging/minilm_v3_907k_cleaned_20260312_050427`

Important:

- `INTERNAL_API_KEY` on the frontend must exactly match backend `API_SECRET_KEY`
- `USE_MOCK_API` must be `false`
- `ALLOWED_ORIGINS` must use your frontend production origin, not localhost

## 1. Deploy The Backend

Create a Render Web Service from this repository.

Settings:

- Root directory: repository root
- Runtime: Docker
- Dockerfile path: `./Dockerfile`
- Health check path: `/health`

Backend environment variables:

```dotenv
DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>:<port>/postgres
APP_ENV=production
LOG_LEVEL=INFO
MODEL_PATH=ml_model/model_registry
MODEL_REGISTRY_PATH=ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755
API_SECRET_KEY=<strong-random-secret>
ALLOWED_ORIGINS=["https://<frontend-service>.onrender.com"]
CONFIDENCE_LOW_THRESHOLD=0.50
CONFIDENCE_HIGH_THRESHOLD=0.80
STALE_PROCESSING_TIMEOUT_SECONDS=30
MAX_SEQ_LEN=128
TEMPERATURE=0.596868
```

Notes:

- The backend container now runs `alembic upgrade head` on startup before launching uvicorn.
- The backend container now respects Render's `PORT` variable automatically.
- You can bootstrap both Render services from [render.yaml](render.yaml) if you prefer Blueprint setup.
- Do not leave `API_SECRET_KEY` empty in production.
- Do not point `MODEL_REGISTRY_PATH` at an empty path unless you intentionally want mock fallback behavior.

Verify after deploy:

- `https://<backend-service>.onrender.com/health`
- `https://<backend-service>.onrender.com/api/health`

## 2. Deploy The Frontend

Create a second Render Web Service from the same repository.

Settings:

- Root directory: `frontend`
- Runtime: Docker
- Dockerfile path: `./Dockerfile`

Frontend environment variables:

```dotenv
AUTH_SECRET=<strong-random-secret>
AUTH_TRUST_HOST=true
NEXTAUTH_URL=https://<frontend-service>.onrender.com
SOC_DEMO_PASSWORD=<demo-password>
DEMO_PASSWORD=
FASTAPI_BASE_URL=https://<backend-service>.onrender.com
INTERNAL_API_KEY=<same-value-as-backend-API_SECRET_KEY>
USE_MOCK_API=false
NEXT_PUBLIC_APP_ENV=production
NEXT_PUBLIC_APP_VERSION=1.0.0
```

Notes:

- The frontend container now binds to `0.0.0.0` and respects Render's `PORT` variable.
- Frontend environment values are also captured in [frontend/.env.render.example](frontend/.env.render.example).
- `AUTH_SECRET` is required in production.
- `FASTAPI_BASE_URL` must point to the deployed backend.
- `INTERNAL_API_KEY` must exactly match backend `API_SECRET_KEY`.

## 3. Smoke Test The Public App

Run these checks after both services are live:

1. Open the frontend URL.
2. Sign in with the configured demo password.
3. Load the dashboard.
4. Load alerts.
5. Open an alert detail page or drawer.
6. Perform one triage/action mutation.
7. Confirm the backend health endpoint still returns `200`.

## 4. Production Rules For This Repo

- Keep the browser talking to Next.js, not FastAPI directly.
- Keep Supabase as the database only.
- Keep `USE_MOCK_API=false`.
- Keep backend auth between Next.js and FastAPI via `Authorization: Bearer <INTERNAL_API_KEY>`.
- Keep production CORS restricted to the frontend origin.
- Do not change the confidence threshold values without explicit approval.

## 5. Common Failure Modes

Frontend loads but data calls fail:

- Check `FASTAPI_BASE_URL`
- Check `INTERNAL_API_KEY`
- Check backend health URL

Auth/login fails:

- Check `AUTH_SECRET`
- Check `NEXTAUTH_URL`
- Check `AUTH_TRUST_HOST`

Backend fails to boot:

- Check `DATABASE_URL`
- Check `MODEL_REGISTRY_PATH`
- Check migration compatibility with the target database

Backend rejects requests from the frontend:

- Check `ALLOWED_ORIGINS`
- Check that the frontend origin is HTTPS and matches exactly

## 6. Lowest-Risk Next Step

Deploy backend first, confirm health, then deploy frontend. Do not add ModSecurity, Redis, or architecture changes to the first public rollout.