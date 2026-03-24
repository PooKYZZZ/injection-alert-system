# Smoke Test Runbook

**Last updated:** 2026-03-24
**Audience:** Any teammate with zero prior context.

This runbook walks through starting the current repo Docker stack, verifying the current browser-facing dashboard flow, and confirming that a triage update persists through the real `triage_status` contract.

> **Scope note:** This runbook documents the current branch state only. In this repo variant, the frontend is published on `localhost:3000`, while backend and ModSecurity stay internal to the compose network.

---

## Prerequisites

- Docker Desktop is installed and running.
- You have cloned the repo and are at the repo root (`injection-alert-system/`).
- `.env` exists at the repo root with a valid `DATABASE_URL` pointing to your Supabase PostgreSQL instance.
- `frontend/.env.local` exists with valid values (see `docs/SETUP.md` for the template).

---

## Step 1 — Start the Docker Stack

From the repo root:

```powershell
docker compose up --build -d
```

**What this does:** Builds the backend (Python/FastAPI), frontend (Next.js), and ModSecurity (OWASP CRS + Nginx) images, then starts all three containers in detached mode.

Wait approximately 30–60 seconds for all containers to initialize.

---

## Step 2 — Confirm All Containers Are Running

```powershell
docker compose ps
```

**Expected output:** Three services listed, all with status `Up` (or `running`):

| Service      | Expected Status |
|--------------|-----------------|
| `modsecurity` | Up             |
| `backend`     | Up             |
| `frontend`    | Up             |

If any container shows `Exit` or is missing, inspect its logs:

```powershell
docker compose logs <service-name>
```

For example: `docker compose logs backend`

---

## Step 3 — Verify Backend Health

The backend image does not include `curl`, so use Python inside the container:

```powershell
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)"
```

**Expected response (HTTP 200):**

```json
{"status": "ok"}
```

Also verify the API health endpoint:

```powershell
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').status)"
```

**Expected response (HTTP 200):**

```json
{"status": "ok"}
```

> **Note:** The backend is not published to the host in the current compose file. Use `docker compose exec backend ...` for direct backend checks from the host machine.

---

## Step 4 — Optional Demo Data Seeding

This repository does track `seed_demo.py`, but it targets `127.0.0.1:8000`.

That means:

- running it on the host will fail in Docker mode because backend is not host-published
- running it inside the backend container will hit FastAPI directly
- it will not exercise the ModSecurity path

If you want to seed directly into the backend container:

```powershell
docker compose exec backend python seed_demo.py
```

Treat this step as optional. The rest of the runbook still works if the database already contains alert rows.

---

## Step 5 — Log In to the Dashboard

Open a browser and navigate to:

```
http://localhost:3000/login
```

Enter the demo password (the value of `SOC_DEMO_PASSWORD` from your `frontend/.env.local`; the default is `demo1234`).

You should be redirected to the dashboard.

If the login button appears unresponsive or the dashboard remains on skeletons, rebuild and restart the frontend container. The production CSP must allow inline scripts for Next.js hydration.

---

## Step 6 — Verify Dashboard Page Loads

**URL:** `http://localhost:3000/dashboard`

**What to check:**

- [ ] Page loads without a blank screen or error overlay.
- [ ] Six stat cards are visible at the top (High alerts, Blocked, Throttled, Allowed, Avg ML confidence, False Positive Rate).
- [ ] The timeline chart panel renders (may show "No events" if no data yet, but the panel itself should be visible).
- [ ] Attack type distribution panel renders.
- [ ] ML confidence bands panel renders.
- [ ] Top source IPs panel renders.
- [ ] Top targeted paths panel renders.
- [ ] Recent alerts table renders at the bottom.

If stat cards show `—`, the backend may not be responding. Check `docker compose logs backend`.

---

## Step 7 — Verify Alerts Page Loads

**URL:** `http://localhost:3000/alerts`

**What to check:**

- [ ] Page loads without errors.
- [ ] Filter bar is visible at the top.
- [ ] Alert rows are listed (should show seeded demo data).
- [ ] Each row shows prediction label, confidence, action taken, and timestamp.

---

## Step 8 — Verify ML Health Page Loads

**URL:** `http://localhost:3000/ml-health`

**What to check:**

- [ ] Page loads without errors.
- [ ] Model header section renders (model name, version, status).
- [ ] Confidence thresholds section renders.
- [ ] Per-class F1 chart renders.
- [ ] Reliability diagram renders.
- [ ] Confidence drift chart renders.
- [ ] Prediction distribution renders.

---

## Step 9 — Verify Triage Update Persists to Supabase

### 9a. Find an alert to triage

Go to `http://localhost:3000/alerts` and note the ID of any alert row (e.g., click on it to open the detail view, or copy the ID from the row).

### 9b. PATCH the triage status

Use PowerShell to send a triage update directly inside the backend container. Replace `<ALERT_ID>` with the actual alert ID:

```powershell
docker compose exec backend curl -s -X PATCH http://localhost:8000/api/alerts/<ALERT_ID>/triage -H "Content-Type: application/json" -H "Authorization: Bearer local-dev-secret" -d '{"triage_status":"in_review"}'
```

> **Note:** The browser path still goes through the Next.js BFF. This direct backend call is only for smoke verification because the backend is internal to the compose network.

### 9c. Verify the update persisted

Query the same alert to confirm the triage status changed:

```powershell
docker compose exec backend curl -s http://localhost:8000/api/alerts/<ALERT_ID> -H "Authorization: Bearer local-dev-secret"
```

**What to check:**

- [ ] The response includes `"triage_status": "in_review"` (or the status you set).
- [ ] The `labeled_at` field is populated with a recent timestamp.

### 9d. Verify in the dashboard UI

Refresh `http://localhost:3000/alerts` and confirm the updated alert reflects the new triage status in the table.

---

## Step 10 — Stop the Stack

When finished:

```powershell
docker compose down
```

To also remove volumes (clears local data):

```powershell
docker compose down -v
```

---

## Quick Reference — All Commands in Order

```powershell
# 1. Start stack
docker compose up --build -d

# 2. Confirm containers
docker compose ps

# 3. Backend health
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)"
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').status)"

# 4. Optional demo data seeding (inside container)
docker compose exec backend python seed_demo.py

# 5. Open browser to http://localhost:3000/login and log in

# 6. Verify pages
#    - http://localhost:3000/dashboard
#    - http://localhost:3000/alerts
#    - http://localhost:3000/ml-health

# 7. Triage update (replace <ALERT_ID>)
docker compose exec backend curl -s -X PATCH http://localhost:8000/api/alerts/<ALERT_ID>/triage -H "Content-Type: application/json" -H "Authorization: Bearer local-dev-secret" -d '{\"triage_status\":\"in_review\"}'

# 8. Verify persistence
docker compose exec backend curl -s http://localhost:8000/api/alerts/<ALERT_ID> -H "Authorization: Bearer local-dev-secret"

# 9. Stop stack
docker compose down
```

---

## Troubleshooting

### Container exits immediately

```powershell
docker compose logs <service-name>
```

Common causes:
- Missing `.env` or `frontend/.env.local` — check that both files exist with correct values.
- `DATABASE_URL` is invalid or Supabase is unreachable — verify connectivity.
- Port conflict (80, 3000, or 8000 already in use) — stop conflicting services.

### Dashboard shows blank or 401

- Ensure you logged in at `http://localhost:3000/login` first.
- Check `AUTH_TRUST_HOST=true` in `frontend/.env.local`.
- Check `INTERNAL_API_KEY` matches `API_SECRET_KEY` in `.env`.

### Seeding utility fails with connection error

- Ensure the backend container is running: `docker compose ps`.
- `seed_demo.py` targets `127.0.0.1:8000`, so it must be run inside the backend container in Docker mode.
- If you want to test the ModSecurity path, do not use `seed_demo.py` unchanged.

### ModSecurity routing expectation

- In the current compose file, ModSecurity is internal-only.
- Browser traffic on `localhost:3000` does not pass through ModSecurity.
- ModSecurity does proxy to `backend` inside the Compose network.
- Direct backend container calls are valid for smoke verification, but they bypass ModSecurity.
