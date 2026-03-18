# CyberTrace — Quick Start Guide

Follow these steps in order on a fresh clone. Total setup time: ~10 minutes.

---

## Prerequisites

| Requirement | Minimum version |
|-------------|----------------|
| Python | 3.12 or higher |
| Node.js | 18 or higher |
| Git | Any recent version |

---

## Step 1 — Clone the repository

```bash
git clone <your-repo-url>
cd injection-alert-system
```

---

## Step 2 — Set up the backend

### 2a — Create a virtual environment

```bash
# Windows
python -m venv .venv
.\.venv\Scripts\activate

# macOS / Linux
python -m venv .venv
source .venv/bin/activate
```

### 2b — Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2c — Configure the environment file

```bash
cp .env.example .env
```

The default values in `.env` work for local development.
No manual edits required unless you have a custom database or port.

### 2d — Run database migrations

> Run this **before** starting the server. It creates the database tables.

```bash
# Windows
.\.venv\Scripts\python.exe -m alembic upgrade head

# macOS / Linux
alembic upgrade head
```

Expected output: `INFO` lines only, no errors or tracebacks.
If you see `No new upgrade operations to perform` — that is also fine.

### 2e — Download the ML model (optional)

1. Download `distilbert_v3_model.zip` from the team shared drive:
   **[PASTE SHARED DRIVE LINK HERE]**
2. Extract it into `ml_model/model_registry/staging/`
3. Confirm this folder exists after extraction:
   `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755/`

> **Skipping this step is fine.** The backend starts in mock mode automatically
> if the model folder is missing. You will see a warning in the terminal —
> that is expected, not an error.

### 2f — Start the backend server

```bash
# Windows
.\.venv\Scripts\python.exe -m uvicorn web_app.presentation.app:create_app \
  --reload --host 127.0.0.1 --port 8000

# macOS / Linux
uvicorn web_app.presentation.app:create_app \
  --reload --host 127.0.0.1 --port 8000
```

The backend is ready when you see:
`INFO:     Application startup complete.`

Backend URL: **http://127.0.0.1:8000**

---

## Step 3 — Set up the frontend

Open a **new terminal**. Keep the backend terminal running.

### 3a — Navigate to the frontend folder

```bash
cd frontend
```

### 3b — Install Node.js dependencies

```bash
npm install
```

### 3c — Configure the environment file

```bash
cp .env.example .env.local
```

The default values work for local development. No manual edits required.

### 3d — Start the frontend server

```bash
npm run dev
```

The frontend is ready when you see: `✓ Ready in Xs`

Frontend URL: **http://localhost:3000**

---

## Step 4 — Seed demo data

Open a **third terminal**. Keep both the backend and frontend running.

```bash
# Windows
.\.venv\Scripts\activate
.\.venv\Scripts\python.exe seed_demo.py

# macOS / Linux
source .venv/bin/activate
python seed_demo.py
```

This inserts 18 demo records into the database:
SQL Injection attacks, Code Injection attacks, and Normal traffic
across HIGH, MEDIUM, and LOW confidence bands.

To wipe and re-seed: `python seed_demo.py --reset`

---

## Step 5 — Log in

1. Open **http://localhost:3000**
2. Log in with the demo credentials:
   - **Email:** `soc@cybertrace.local`
   - **Password:** `demopass123`

---

## Common commands

### Backend

| Command | What it does |
|---------|-------------|
| `uvicorn web_app.presentation.app:create_app --reload` | Start backend |
| `alembic upgrade head` | Apply database migrations |
| `pytest` | Run backend tests |
| `python seed_demo.py` | Insert demo data |
| `python seed_demo.py --reset` | Wipe and re-seed demo data |

### Frontend

| Command | What it does |
|---------|-------------|
| `npm run dev` | Start development server |
| `npm run typecheck` | TypeScript type check |
| `npm test` | Run unit tests |
| `npm run build` | Production build |

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Module not found` errors | Activate venv: `\.venv\Scripts\activate` then `pip install -r requirements.txt` again |
| `Application startup failed. Exiting.` | Priority 1 fix not applied yet — wrap model loading in try/except |
| Backend starts with `WARNING: Starting in mock mode` | Expected if model not downloaded. Download from shared drive to use real predictions |
| `alembic upgrade head` traceback | Check `DATABASE_URL` in `.env` starts with `sqlite+aiosqlite:///` — Priority 3 fix must be applied |
| `Cannot connect to backend` (frontend) | Confirm backend is on port 8000. Check `FASTAPI_BASE_URL` in `frontend/.env.local` |
| All API calls return 500 | Check backend terminal. If `Application startup failed` — see row 2 above |
| `401 Unauthorized` | Set `API_SECRET_KEY=` (empty) in `.env` and `INTERNAL_API_KEY=` (empty) in `frontend/.env.local` |
| Frontend `npm install` errors | `rm -rf node_modules package-lock.json` then `npm install` |
| Seed script fails | Confirm venv is active. Confirm `DATABASE_URL` in `.env` is correct and migrations have run |
