# Injection Alert System — Local Setup Guide (updated)

This document shows the commands I ran on Windows/PowerShell to get the app running locally. It focuses on a practical, working dev setup (backend on port 8000, frontend on port 3000). Where useful I note alternatives (nvm, Docker) and common Windows issues I encountered.

Quick summary: backend runs on port `8000`, frontend runs on `3000`. For UI-only work set `USE_MOCK_STATS=true` in `frontend/.env.local`.

---

**Prerequisites**

- Git (https://git-scm.com/)
- Python 3.11+ (https://www.python.org/)
- Node.js (LTS) — on Windows you can use `nvm-windows` or `winget` (I installed via `winget` in these steps)
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

## 2) Backend (FastAPI) setup — practical steps

The backend lives in `web_app/` and uses FastAPI. On Windows I performed these steps.

1) Create a Python virtual environment

```powershell
python -m venv .venv
# Activate in PowerShell
.venv\Scripts\Activate.ps1
# If activation is blocked by execution policy, run once as admin (or use the CurrentUser scope):
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Note: if you prefer not to change execution policy, you can run the venv Python directly via `.venv\Scripts\python.exe -m pip ...` for installs and checks.

2) Create `.env` from the example and apply quick dev settings

```powershell
Copy-Item .env.example .env
notepad .env   # or open in your editor
```

Recommended local `.env` values for quick dev work:

```
DATABASE_URL=sqlite+aiosqlite:///./dev.db
APP_ENV=development
LOG_LEVEL=DEBUG
MODEL_PATH=ml_model/models/mock_model.py
API_SECRET_KEY=local_insecure_key
GROQ_API_KEY=
ALLOWED_ORIGINS=["http://localhost:3000"]
```

3) Install Python dependencies

The repository `requirements.txt` includes large ML packages (torch, transformers, onnx, onnxruntime) which can take time to download and install on Windows. If you only need the frontend/UI, you can skip this step and keep `USE_MOCK_STATS=true` in `frontend/.env.local`.

To install into the venv (recommended):

```powershell
.venv\Scripts\pip.exe install -r requirements.txt
```

If you run into permission/execution-policy issues when activating the venv, use the fully-qualified `python`/`pip` under `.venv\Scripts` as shown above.

4) Initialize DB & run the app

The application creates DB tables on first startup when `init_db()` runs. Start the backend with:

```powershell
cd .
.venv\Scripts\uvicorn.exe web_app.presentation.app:app --reload --port 8000
```

Verify the health endpoint:

```powershell
curl http://localhost:8000/health
```

---

## 3) Frontend (Next.js) setup — practical steps I used

The frontend is in `frontend/` and uses Next.js (App Router) + TypeScript.

1) Install Node.js

On Windows I used `winget` to install the Node LTS distribution:

```powershell
winget install OpenJS.NodeJS.LTS --accept-package-agreements --accept-source-agreements
```

If you use `nvm-windows` instead, the older instructions remain valid. After installing Node, ensure `npm` is callable. On PowerShell you may need to relax the execution policy for the current user to allow `npm` scripts to run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force
```

2) Create or edit the frontend env file

```powershell
cd frontend
Copy-Item .env.example .env.local  # if not already present
notepad .env.local
```

Important `frontend/.env.local` values (examples):

- `AUTH_SECRET`: generate a secret (`npx auth secret` or `openssl rand -hex 32`).
- `DEMO_USERNAME` / `DEMO_PASSWORD` (I used `demo` / `demo1234` in testing).
- `FASTAPI_BASE_URL`: set to `http://localhost:8000` for local full-stack.
- `INTERNAL_API_KEY`: set to match backend `API_SECRET_KEY` if server->server calls are used.
- `USE_MOCK_STATS=true` to use local mock data and avoid calling the backend for stats.

Note: in my run the repo's `frontend/.env.local` default pointed to `http://fastapi:8000` — I updated it to `http://localhost:8000`.

3) Install frontend dependencies

```powershell
cd frontend
npm install
```

4) If Next reports a missing package at runtime (for example `tw-animate-css` in my run), install it:

```powershell
cd frontend
npm install tw-animate-css
```

5) Start the dev server

```powershell
cd frontend
npm run dev
```

Notes about ports: Next.js prefers `3000`. If `3000` is in use, Next will pick another port (e.g., `3001`). If you need a stable port, stop whatever is using `3000` or set `PORT=3000` before running.

Open the UI at: http://localhost:3000 (or the port printed by Next if `3000` was unavailable).

To sign in to the demo app (demo provider) use the `DEMO_PASSWORD` you set (no username required if the app expects only password-based demo auth).

---

## 4) Frontend <-> Backend modes

- Mock-only UI: set `USE_MOCK_STATS=true` in `frontend/.env.local` — very fast for UI work and avoids installing or running the backend.
- Full-stack local: set `USE_MOCK_STATS=false` and ensure:
  - `FASTAPI_BASE_URL=http://localhost:8000`
  - `INTERNAL_API_KEY` (frontend) matches `API_SECRET_KEY` (backend `.env`).

When using full-stack, Next.js server-side routes will proxy to the backend.

---

## 5) Run the full stack (recommended sequence)

Terminal 1 (backend):

```powershell
cd injection-alert-system
.venv\Scripts\Activate.ps1
cd injection-alert-system
.venv\Scripts\uvicorn.exe web_app.presentation.app:app --reload --port 8000
```

Terminal 2 (frontend):

```powershell
cd injection-alert-system\frontend
npm install   # only once
npm run dev
```

Visit: http://localhost:3000

---

## 6) Common troubleshooting (Windows-specific)

- Activation / script errors: PowerShell's execution policy can block `.ps1` scripts (including `npm` helpers). The fix I used was: `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`.
- Long installs / heavy ML deps: `requirements.txt` contains large packages (torch, transformers, onnx, onnxruntime). Expect long downloads and possible native wheel issues on Windows; for UI work you can skip backend install and use `USE_MOCK_STATS=true`.
- Frontend port conflict: if `3000` is occupied Next will switch ports; stop the other process or explicitly provide `PORT=3000`.
- CORS / 401 between front/back: ensure `ALLOWED_ORIGINS` includes `http://localhost:3000` and that `INTERNAL_API_KEY` / `API_SECRET_KEY` match when using server->server calls.
- Missing runtime packages: if `npm run dev` logs a missing package, install it with `npm install <pkg>` (I installed `tw-animate-css`).

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

If you want, I can add a `docker-compose.yml` that starts Postgres, backend, and frontend for development — say if you want to avoid installing large ML deps locally.

---

## 10) Security notes

- Do NOT check `.env` or `.env.local` into Git.
- Use strong `AUTH_SECRET` and `API_SECRET_KEY` in production.
- `USE_MOCK_STATS` must be `false` in production.

---

## 11) Quick commands summary

```powershell
# repo root
git clone <repo>
cd injection-alert-system

# backend (create venv and install deps)
python -m venv .venv
.venv\Scripts\Activate.ps1
Copy-Item .env.example .env
.venv\Scripts\pip.exe install -r requirements.txt
.venv\Scripts\uvicorn.exe web_app.presentation.app:app --reload --port 8000

# frontend (new terminal)
cd frontend
Copy-Item .env.example .env.local
# edit .env.local (set FASTAPI_BASE_URL, DEMO_PASSWORD, AUTH_SECRET, etc.)
npm install
npm install tw-animate-css  # optional: install if Next warns about it
npm run dev
```

---

If you'd like, I can commit this updated `docs/SETUP.md` and/or create a `docker-compose.yml` example next. Which would you prefer?