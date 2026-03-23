# Smoke Test Runbook

**Last updated:** 2026-03-23
**Audience:** Any teammate with zero prior context.

This runbook walks through starting the full Docker stack, seeding demo data, verifying every dashboard page loads, and confirming that a triage update persists to Supabase.

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

```powershell
curl http://localhost:8000/health
```

**Expected response (HTTP 200):**

```json
{"status": "ok"}
```

Also verify the API health endpoint:

```powershell
curl http://localhost:8000/api/health
```

**Expected response (HTTP 200):**

```json
{"status": "ok"}
```

> **Note:** The ModSecurity container exposes port 8080 internally but is mapped to host port 80. The backend is only reachable through ModSecurity at `http://localhost:80` in the Docker stack. If you need direct backend access for seeding, use `docker compose exec backend` (see Step 4).

---

## Step 4 — Seed Demo Data

Run the seed script inside the backend container:

```powershell
docker compose exec backend python seed_demo.py
```

**Expected output:** The script sends ~35 demo payloads (SQL injection, command injection, path traversal, normal traffic, etc.) through the prediction API. Each payload prints a prediction, confidence, and action. The final summary should show `Successful` equal to the total processed, with `Failed` at 0.

If `seed_demo.py` cannot reach the backend from outside Docker, run it locally instead:

```powershell
# In a separate terminal, from the repo root
.venv\Scripts\Activate.ps1
$env:API_SECRET_KEY = "local-dev-secret"
python seed_demo.py http://localhost:8000
```

> **Note:** `seed_demo.py` reads `API_SECRET_KEY` from the environment. It defaults to `http://127.0.0.1:8000`. If running locally against the Docker stack, pass the correct URL or set `API_BASE_URL`.

---

## Step 5 — Log In to the Dashboard

Open a browser and navigate to:

```
http://localhost:3000/login
```

Enter the demo password (the value of `SOC_DEMO_PASSWORD` from your `frontend/.env.local`; the default is `demo1234`).

You should be redirected to the dashboard.

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

Use PowerShell to send a triage update. Replace `<ALERT_ID>` with the actual alert ID:

```powershell
$headers = @{
    "Content-Type" = "application/json"
    "Authorization" = "Bearer local-dev-secret"
}

$body = @{
    status = "CONFIRMED"
    analyst_notes = "smoke test triage update"
} | ConvertTo-Json

Invoke-RestMethod -Uri "http://localhost:8000/api/alerts/<ALERT_ID>/triage" -Method Patch -Headers $headers -Body $body
```

> **Note:** If running through ModSecurity (port 80), use `http://localhost:80/api/alerts/<ALERT_ID>/triage` instead. If ModSecurity blocks the PATCH request, use the backend directly via `docker compose exec backend` or port-forward:

```powershell
# Alternative: exec into backend container and curl from inside
docker compose exec backend curl -s -X PATCH http://localhost:8000/api/alerts/<ALERT_ID>/triage -H "Content-Type: application/json" -H "Authorization: Bearer local-dev-secret" -d '{"status":"CONFIRMED","analyst_notes":"smoke test"}'
```

### 9c. Verify the update persisted

Query the same alert to confirm the triage status changed:

```powershell
Invoke-RestMethod -Uri "http://localhost:8000/api/alerts/<ALERT_ID>" -Headers @{"Authorization" = "Bearer local-dev-secret"}
```

**What to check:**

- [ ] The response includes `"status": "CONFIRMED"` (or the status you set).
- [ ] `analyst_notes` contains `"smoke test triage update"`.
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
curl http://localhost:8000/health
curl http://localhost:8000/api/health

# 4. Seed demo data (inside container)
docker compose exec backend python seed_demo.py

# 5. Open browser to http://localhost:3000/login and log in

# 6. Verify pages
#    - http://localhost:3000/dashboard
#    - http://localhost:3000/alerts
#    - http://localhost:3000/ml-health

# 7. Triage update (replace <ALERT_ID>)
$headers = @{ "Content-Type" = "application/json"; "Authorization" = "Bearer local-dev-secret" }
$body = @{ status = "CONFIRMED"; analyst_notes = "smoke test triage update" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8000/api/alerts/<ALERT_ID>/triage" -Method Patch -Headers $headers -Body $body

# 8. Verify persistence
Invoke-RestMethod -Uri "http://localhost:8000/api/alerts/<ALERT_ID>" -Headers @{"Authorization" = "Bearer local-dev-secret"}

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

### seed_demo.py fails with connection error

- Ensure the backend container is running: `docker compose ps`.
- If running locally (outside Docker), use the correct URL: `http://localhost:8000` (through ModSecurity) or check port mapping.

### Triage PATCH is blocked by ModSecurity

- ModSecurity may reject PATCH requests depending on CRS rules. Use the backend container directly:

```powershell
docker compose exec backend curl -s -X PATCH http://localhost:8000/api/alerts/<ALERT_ID>/triage -H "Content-Type: application/json" -H "Authorization: Bearer local-dev-secret" -d '{"status":"CONFIRMED","analyst_notes":"smoke test"}'
```
