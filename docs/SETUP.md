# Injection Alert System — Local Setup Guide

This document explains how to clone, configure, and run the Injection Alert System locally on a development machine (Windows / PowerShell). It covers both the backend (FastAPI) and the frontend (Next.js) plus helpful troubleshooting tips.

> Quick summary: backend runs on port `8000`, frontend runs on `3000`. Use `USE_MOCK_STATS=true` for frontend-only UI development.

---

## Prerequisites

- Git (https://git-scm.com/)
- Node.js v18+ (use nvm-windows: https://github.com/coreybutler/nvm-windows)
- Python 3.11+ (https://www.python.org/)
- (Optional) VS Code and Windows Terminal

---

## 1) Clone the repository

Open PowerShell and run:

```powershell
# replace the URL with your repo remote
git clone https://github.com/your-org/injection-alert-system.git
cd injection-alert-system
```

---

## 2) Backend (FastAPI) setup

The backend is in `web_app/` and uses FastAPI.

1. Create and activate a Python virtual environment

```powershell
python -m venv .venv
# Activate in PowerShell
.venv\Scripts\Activate.ps1
# If execution policy blocks activation (run as admin once):
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
```

2. Copy environment variables and edit `.env`

```powershell
Copy-Item .env.example .env
notepad .env  # or open in your editor
```

Recommended local `.env` adjustments for quick dev:

```
DATABASE_URL=sqlite+aiosqlite:///./dev.db
APP_ENV=development
LOG_LEVEL=DEBUG
MODEL_PATH=ml_model/models/mock_model.py
API_SECRET_KEY=local_insecure_key
GROQ_API_KEY=
ALLOWED_ORIGINS=["http://localhost:3000"]
```

3. Install Python dependencies

```powershell
pip install -r requirements.txt
```

4. Initialize DB & run the app

The application will create tables on first startup when `init_db()` runs.

```powershell
uvicorn web_app.presentation.app:app --reload --host 0.0.0.0 --port 8000
```

Verify the health endpoint:

```powershell
curl http://localhost:8000/health
```

---

## 3) Frontend (Next.js) setup

The frontend is in `frontend/` and uses Next.js (App Router) + TypeScript.

1. Install Node (recommended via nvm-windows)

```powershell
# install node 18 via nvm (if not already installed)
nvm install 18
nvm use 18
node -v
npm -v
```

2. Create frontend env file

```powershell
cd frontend
Copy-Item .env.example .env.local
notepad .env.local
```

Important values to set in `frontend/.env.local`:

- `AUTH_SECRET`: generate via `npx auth secret` or `openssl rand -hex 32`.
- `SOC_DEMO_PASSWORD`: e.g. `demo1234` (used by the demo credentials provider).
- `FASTAPI_BASE_URL`: `http://localhost:8000` (if using the local backend).
- `INTERNAL_API_KEY`: must match backend `API_SECRET_KEY` when front-end server routes call backend services.
- `USE_MOCK_STATS=true` to use local mock data for stats (safe for UI dev).

3. Install dependencies and run dev server

```powershell
npm install
npm run dev
```

Open your browser: http://localhost:3000

To sign in to the demo app use the demo password you set earlier (no username required).

---

## 4) Frontend <-> Backend modes

- Mock-only UI: set `USE_MOCK_STATS=true` in `frontend/.env.local`. Frontend will not depend on the backend for stats and alerts (fast for UI work).
- Full-stack local: set `USE_MOCK_STATS=false` and ensure:
  - `FASTAPI_BASE_URL=http://localhost:8000`
  - `INTERNAL_API_KEY` (in frontend) matches `API_SECRET_KEY` (in backend `.env`).

When using full-stack, the frontend's server-side routes (Next.js App Router) will proxy to the backend.

---

## 5) Run the full stack (recommended sequence)

Terminal 1 (backend):

```powershell
cd injection-alert-system
.venv\Scripts\Activate.ps1
uvicorn web_app.presentation.app:app --reload --port 8000
```

Terminal 2 (frontend):

```powershell
cd injection-alert-system\frontend
nvm use 18
npm install   # only once
npm run dev
```

Visit: http://localhost:3000

---

## 6) Common troubleshooting

- Activation issues (PowerShell execution policy):
  - Run as admin and use `Set-ExecutionPolicy RemoteSigned -Scope CurrentUser` or run: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process`.

- `uvicorn` fails or DB errors:
  - Confirm `DATABASE_URL` in backend `.env`. For local dev use SQLite as shown above.

- Frontend shows ligature names instead of icons (e.g. `notifications`):
  - Ensure `frontend/app/layout.tsx` includes the Google Material Symbols / Icons stylesheet. The project restores it by default.

- Frontend cannot call backend (CORS or 401):
  - Check backend `ALLOWED_ORIGINS` includes `http://localhost:3000` and `INTERNAL_API_KEY` / `API_SECRET_KEY` values match if server->server calls are used.

- `npm run dev` or `next` errors about environment:
  - Confirm `frontend/.env.local` contains `AUTH_SECRET` and other required keys. Don't commit `.env.local`.

---

## 7) Tests & linting

- Backend tests (if any): run from repo root using `pytest`:

```powershell
# from repo root
python -m pytest -q
```

- Frontend typecheck & lint:

```powershell
# from frontend/
npm run typecheck
npm run lint
```

---

## 8) Production / build

To build the frontend for production:

```powershell
cd frontend
npm run build
npm run start   # or serve with any Node host
```

For the backend, configure a production-grade Postgres DB and run with Uvicorn + a process manager (systemd, supervisord) or containerize.

---

## 9) Optional: Docker Compose (example)

If you'd like, I can add a `docker-compose.yml` that starts Postgres, backend, and frontend for development. Tell me and I will prepare it.

---

## 10) Security notes

- Do NOT check `.env` or `.env.local` into Git.
- Use strong `AUTH_SECRET` and `API_SECRET_KEY` in production.
- `USE_MOCK_STATS` must be `false` in production.

---

## 11) Helpful commands summary

```powershell
# repo root
git clone <repo>
cd injection-alert-system

# backend
python -m venv .venv
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
pip install -r requirements.txt
uvicorn web_app.presentation.app:app --reload --port 8000

# frontend (new terminal)
cd frontend
Copy-Item .env.example .env.local
# edit .env.local
nvm use 18
npm install
npm run dev
```

---

If you want, I can create a `docker-compose.yml` for local development, or commit a `docs/SETUP.md` to the repository (I created this file). Would you like a `docker-compose` example next?