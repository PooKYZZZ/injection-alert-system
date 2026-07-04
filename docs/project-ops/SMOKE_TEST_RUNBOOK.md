# Smoke Test Runbook

**Last updated:** 2026-07-03
**Audience:** Any teammate with zero prior context.

This runbook walks through starting the current repo Docker stack, verifying the WAF proof path, verifying the current browser-facing dashboard flow, and confirming that a triage update persists through the real `triage_status` contract.

> **Scope note:** This runbook documents the current branch state only. In this repo variant, the frontend is published on `localhost:3000`, the technical CyberTrace WAF proof path is published on `localhost:8088`, the realistic protected demo website WAF path is published on `localhost:8089` when the `demo-target` profile is enabled, and the backend stays internal to the compose network as `8000/tcp`.

---

## Automated Final Demo Smoke

The maintained smoke entrypoint is `scripts/run_final_demo_smoke.py`. Every run
requires an explicit mode, prints one result per check, and exits nonzero when a
required check fails.

Backend-only smoke against a directly reachable FastAPI process:

```powershell
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode backend
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode backend --json
```

The backend default is `http://127.0.0.1:8000`. Override it only for an
intentionally reachable backend:

```powershell
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode backend --base-url http://127.0.0.1:8000 --timeout 5
```

Technical WAF proof through `localhost:8088`:

```powershell
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode waf-8088
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode waf-8088 --json
```

Realistic demo-target proof through `localhost:8089`:

```powershell
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode demo-target-8089
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode demo-target-8089 --json
```

The `waf-8088` mode checks `/healthz`, `/api/health`, an expected SQLi `403`,
and the latest transaction ID when
`logs/modsecurity/modsec_audit.jsonl` exists. The `demo-target-8089` mode checks
the portal home page, an expected `/records/search` SQLi `403`, and the latest
transaction ID when
`logs/modsecurity/demo-target/modsec_audit.jsonl` exists. Use `--audit-log` to
point either WAF mode at a different local JSONL path.

Interpretation:

- `PASS` means the check observed its expected status or transaction field.
- `FAIL` means a required check failed; the process exits `1`.
- `SKIP` means an optional local artifact or Docker-internal lookup was not
  exercised; skipped checks do not hide required HTTP failures.
- `--json` emits one parseable object and does not print request headers,
  credentials, database URLs, or request payloads.

CI-safe proof is the mocked script suite and TestClient abuse suite:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/scripts/test_run_final_demo_smoke.py
.venv\Scripts\python.exe -m pytest -q tests/integration/test_api_abuse_smoke.py
```

Those tests require neither Docker nor the sibling portal checkout. The three
CLI modes require a running target; `waf-8088` and `demo-target-8089` are
explicit local Docker checks, not always-on CI jobs. The `demo-target-8089`
stack additionally requires the sibling `land-records-portal` checkout or an
explicit `DEMO_PORTAL_CONTEXT`.

Docker-internal backend transaction lookup remains an optional manual proof
step because the backend is not host-published and the lookup requires the
container's secret environment. The automated script reports that step as
`SKIP`; use the commands in Step 5 or Step 5A when end-to-end lookup evidence
is required. The manual sections below remain the fallback for startup,
container inspection, bridge logs, transaction lookup, dashboard checks, and
triage persistence.

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

## Step 5 — Verify WAF Proof Path

Use the WAF-facing path, not `localhost:8000`:

```powershell
Invoke-WebRequest -UseBasicParsing "http://localhost:8088/healthz"
Invoke-WebRequest -UseBasicParsing "http://localhost:8088/api/health"
Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck "http://localhost:8088/api/health?id=17%27%20OR%2017%3D17--"
```

Expected:

- `/healthz` returns HTTP 200.
- `/api/health` returns HTTP 200.
- SQLi probe returns HTTP 403.

Check the latest ModSecurity transaction and bridge post:

```powershell
$latestRaw = Get-Content .\logs\modsecurity\modsec_audit.jsonl -Tail 1
$latest = $latestRaw | ConvertFrom-Json
$txid = $latest.transaction.unique_id
if ([string]::IsNullOrWhiteSpace($txid)) { throw "txid missing" }
docker compose logs --tail=100 bridge
```

Use Docker-internal backend lookup. Do not use `localhost:8000` unless backend port 8000 is explicitly published:

```powershell
docker compose exec -e TXID=$txid backend python -c "import os, urllib.request; txid=os.environ['TXID']; secret=os.environ['API_SECRET_KEY']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', headers={'Authorization': 'Bearer ' + secret}); print(urllib.request.urlopen(req).read().decode())"
```

Expected lookup fields:

- `found=true`
- `prediction=SQL Injection`
- `confidence_level=HIGH`
- `action_taken=BLOCKED`
- `source_ip` present
- `request_path=/api/health`
- `query_string` present and URL-encoded
- `crs_score=5`
- `crs_rule_ids` includes `942100` and `949110`

## Step 5A — Final Realistic Demo-Target Smoke

Use this section for the final realistic WAF demonstration. The land-records-portal source stays separate from this repo. The demo-target profile builds and starts it as `demo-portal` from the sibling repo path `../../land-records-portal`, which resolves to `G:\AI\land-records-portal` from this checkout layout; set `DEMO_PORTAL_CONTEXT` if your portal checkout lives elsewhere. The portal runs as a production Next.js standalone container on internal Compose port `3010`; no manual `npm run dev` is required.

Start the compose stack with the demo-target profile:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml --profile demo-target up -d --build
```

Confirm expected containers:

```powershell
docker ps --format "table {{.Names}}\t{{.Ports}}\t{{.Status}}"
```

Expected services include:

- `frontend`
- `backend`
- `modsecurity`
- `bridge`
- `demo-target-modsecurity`
- `demo-target-bridge`
- `demo-portal`

Confirm the protected demo website is reachable through the WAF:

```powershell
curl.exe -s -o NUL -w "8089 home status: %{http_code}`n" http://localhost:8089/
```

Expected: `8089 home status: 200`.

Generate a fresh identifiable SQLi request:

```powershell
$marker = "SMOKE$(Get-Date -Format HHmmss)"
$url = "http://localhost:8089/records/search?query=%27%20UNION%20SELECT%20null,null,null--%20$marker"
Write-Host "Marker: $marker"
curl.exe -s -o NUL -w "demo SQLi status: %{http_code}`n" $url
```

Expected: `demo SQLi status: 403`.

Inspect the demo-target audit JSONL safely:

```powershell
$raw = Get-Content .\logs\modsecurity\demo-target\modsec_audit.jsonl -Tail 1
$evt = $raw | ConvertFrom-Json
$txid = $evt.transaction.unique_id
$evt.transaction.unique_id
$evt.transaction.request.uri
$evt.transaction.request.headers.Host
```

Expected:

- transaction ID is present
- URI contains `/records/search`
- host is `localhost:8089`

Inspect the demo-target bridge logs:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml --profile demo-target logs --tail=200 demo-target-bridge | Select-String -Pattern "posted|status=200|transaction_id|rule_ids|records/search|SMOKE|949110"
```

Expected: `demo-target-bridge` posted the fresh transaction with `status=200`.

Run the Docker-internal backend lookup:

```powershell
docker compose exec -e TXID=$txid backend python -c "import os, urllib.request; txid=os.environ['TXID']; secret=os.environ['API_SECRET_KEY']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', headers={'Authorization': 'Bearer ' + secret}); print(urllib.request.urlopen(req).read().decode())"
```

Expected lookup fields:

- `found=true`
- `request_path=/records/search`
- query string includes the safe `SMOKE` marker
- `prediction=SQL Injection`
- `action_taken=BLOCKED`
- `crs_score` present
- `crs_rule_ids` present

Confirm the original `8088` proof path still blocks SQLi:

```powershell
curl.exe -s -o NUL -w "8088 SQLi status: %{http_code}`n" "http://localhost:8088/?id=1%27%20OR%20%271%27%3D%271"
```

Expected: `8088 SQLi status: 403`.

Latest verified demo-target evidence: marker `SMOKE002945`, transaction `178249138618.813428`, host `localhost:8089`, request path `/records/search`, bridge post `status=200`, backend lookup `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `crs_score=15`.

---

## Step 6 — Log In to the Dashboard

Open a browser and navigate to:

```
http://localhost:3000/login
```

Enter the id or email and password for a named account configured in
`AUTH_USERS_JSON`. Passwords must be stored as Argon2id PHC hashes; generate a
hash with `node scripts/generate_auth_password_hash.mjs "<password>"`. Old
scrypt hashes are rejected. There is no demo-password fallback. Supabase
account login is still planned for PR 3.

You should be redirected to the dashboard.

If the login button appears unresponsive or the dashboard remains on skeletons, rebuild and restart the frontend container. The production CSP must allow inline scripts for Next.js hydration.

---

## Step 7 — Verify Dashboard Page Loads

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

## Step 8 — Verify Alerts Page Loads

**URL:** `http://localhost:3000/alerts`

**What to check:**

- [ ] Page loads without errors.
- [ ] Filter bar is visible at the top.
- [ ] Alert rows are listed (should show seeded demo data).
- [ ] Each row shows prediction label, confidence, action taken, and timestamp.

---

## Step 9 — Verify ML Health Page Loads

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

## Step 10 — Verify Triage Update Persists to Supabase

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

## Step 11 — Stop the Stack

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

# 4. WAF proof path
Invoke-WebRequest -UseBasicParsing "http://localhost:8088/healthz"
Invoke-WebRequest -UseBasicParsing "http://localhost:8088/api/health"
Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck "http://localhost:8088/api/health?id=17%27%20OR%2017%3D17--"
$latestRaw = Get-Content .\logs\modsecurity\modsec_audit.jsonl -Tail 1
$latest = $latestRaw | ConvertFrom-Json
$txid = $latest.transaction.unique_id
if ([string]::IsNullOrWhiteSpace($txid)) { throw "txid missing" }
docker compose exec -e TXID=$txid backend python -c "import os, urllib.request; txid=os.environ['TXID']; secret=os.environ['API_SECRET_KEY']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', headers={'Authorization': 'Bearer ' + secret}); print(urllib.request.urlopen(req).read().decode())"

# 5. Final realistic demo-target smoke; Compose starts demo-portal from the separate portal repo
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml --profile demo-target up -d --build
curl.exe -s -o NUL -w "8089 home status: %{http_code}`n" http://localhost:8089/
$marker = "SMOKE$(Get-Date -Format HHmmss)"
$url = "http://localhost:8089/records/search?query=%27%20UNION%20SELECT%20null,null,null--%20$marker"
curl.exe -s -o NUL -w "demo SQLi status: %{http_code}`n" $url
$raw = Get-Content .\logs\modsecurity\demo-target\modsec_audit.jsonl -Tail 1
$evt = $raw | ConvertFrom-Json
$txid = $evt.transaction.unique_id
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml --profile demo-target logs --tail=200 demo-target-bridge
docker compose exec -e TXID=$txid backend python -c "import os, urllib.request; txid=os.environ['TXID']; secret=os.environ['API_SECRET_KEY']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', headers={'Authorization': 'Bearer ' + secret}); print(urllib.request.urlopen(req).read().decode())"
curl.exe -s -o NUL -w "8088 SQLi status: %{http_code}`n" "http://localhost:8088/?id=1%27%20OR%20%271%27%3D%271"

# 6. Optional demo data seeding (inside container)
docker compose exec backend python seed_demo.py

# 7. Open browser to http://localhost:3000/login and log in

# 8. Verify pages
#    - http://localhost:3000/dashboard
#    - http://localhost:3000/alerts
#    - http://localhost:3000/ml-health

# 9. Triage update (replace <ALERT_ID>)
docker compose exec backend curl -s -X PATCH http://localhost:8000/api/alerts/<ALERT_ID>/triage -H "Content-Type: application/json" -H "Authorization: Bearer local-dev-secret" -d '{\"triage_status\":\"in_review\"}'

# 10. Verify persistence
docker compose exec backend curl -s http://localhost:8000/api/alerts/<ALERT_ID> -H "Authorization: Bearer local-dev-secret"

# 11. Stop stack
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
