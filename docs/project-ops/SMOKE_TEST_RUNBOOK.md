# Smoke Test Runbook

**Last updated:** 2026-07-20
**Audience:** Any teammate with zero prior context.

This runbook walks through starting the current repo Docker stack, verifying the WAF proof path, verifying the current browser-facing dashboard flow, and confirming that a triage update persists through the real `triage_status` contract.

> **Scope note:** This runbook documents the current branch state only. In this repo variant, the frontend is published on `localhost:3000`, the technical CyberTrace WAF proof path is published on `localhost:8088`, the realistic protected demo website WAF path is published on `localhost:8089` when the `demo-target` profile is enabled, and the backend stays internal to the compose network as `8000/tcp`.

---

## Guarded Telegram provider smoke

The provider-only Telegram smoke refuses to send unless all three server-side
values are deliberately configured:

```powershell
$env:TELEGRAM_LIVE_TEST_ENABLED = "true"
$env:TELEGRAM_BOT_TOKEN = "<bot-token>"
$env:TELEGRAM_CHAT_ID = "<analyst-chat-id>"
.venv\Scripts\python.exe scripts\run_telegram_smoke.py
```

With the live flag absent or false, the command prints a safe `SKIP` and sends
nothing. It never prints the token or chat ID and sends only a fixed harmless
connectivity message. This does not prove the real WAF-to-alert-to-outbox flow;
thesis evidence must correlate a persisted HIGH/CRITICAL alert ID with its
Telegram message and database lifecycle. Do not run live provider tests in CI.

---

## Verified hosted Admin authentication journey

The following journey was verified against the public deployment. Use a
disposable test account and synthetic data only:

1. **Admin creates an account.** Expected: the account is created with the
   intended role and MFA requirement, and a one-time setup email is queued.
2. **Setup email arrives.** Expected: the link opens the password-setup flow;
   do not copy the link into screenshots, logs, or issue reports.
3. **User sets a password.** Expected: the one-time setup token is consumed and
   the user can sign in with the new password.
4. **User enrolls TOTP.** Expected: `/mfa/enroll` renders the QR/manual setup
   interface only for an active password-level enrollment challenge.
5. **Invalid TOTP is submitted.** Expected: the code is rejected and the
   enrollment remains incomplete.
6. **Valid TOTP is submitted.** Expected: enrollment completes, the
   password-level Auth.js session transitions to MFA-authenticated state, and
   the pre-auth handle is cleared.
7. **MFA-authenticated Admin logs in.** Expected: the login completes with the
   required MFA assurance and current authorization metadata.
8. **User Management opens.** Expected: the Admin with the current
   `authz_version`, `auth_level=mfa`, `auth_method=totp`, and the required RBAC
   permission can access User Management. Password-only sessions remain denied.

For safe cleanup, disable or remove only the disposable test account through
the supported account-management flow after the journey. Do not delete shared
accounts or production data. Never capture passwords, setup links, TOTP seeds,
recovery codes, session cookies, or authorization headers in screenshots or
logs. Rotate credentials immediately after any accidental exposure.

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
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode waf-8088 --require-backend-lookup
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode waf-8088 --json
```

Realistic demo-target proof through `localhost:8089`:

```powershell
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode demo-target-8089
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode demo-target-8089 --require-backend-lookup
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode demo-target-8089 --json
```

Each WAF run generates a unique `CYBERTRACE_SMOKE_*` marker and accepts only an
audit event containing that exact marker. The correlated audit event supplies
the transaction ID. With `--require-backend-lookup`, the script runs the
Docker-internal lookup and also requires the backend row to contain the same
marker with a timestamp at or after the smoke start. Use `--audit-log` to point
either WAF mode at a different local JSONL path. Audit-log discovery and
backend persistence use bounded retries because ModSecurity flush and bridge
ingest are asynchronous; a stale or never-persisted marker still fails.

Interpretation:

- `PASS` means every requested proof boundary passed for the current marker.
- `WARN` means required checks passed but optional backend lookup was skipped;
  this is audit-only proof, not full WAF-to-backend proof.
- `FAIL` means a required check failed; the process exits `1`.
- `SKIP` is a per-check state for optional evidence that was not exercised.
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

Docker-internal backend transaction lookup is automated only when
`--require-backend-lookup` is supplied. The script passes the transaction ID,
not the secret, into `docker compose exec`; the container reads its own
`API_SECRET_KEY`. Manual sections remain useful for container inspection,
dashboard checks, and triage persistence.

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
docker compose --profile technical-waf up --build -d
```

**What this does:** Builds the backend, frontend, technical ModSecurity WAF,
and WAF bridge, then starts them in detached mode. Without
`--profile technical-waf`, normal Compose starts only backend and frontend.

Wait approximately 30–60 seconds for all containers to initialize.

---

## Step 2 — Confirm All Containers Are Running

```powershell
docker compose ps
```

**Expected output:** Four services listed, all with status `Up` (or `running`):

| Service      | Expected Status |
|--------------|-----------------|
| `modsecurity` | Up             |
| `backend`     | Up             |
| `frontend`    | Up             |
| `bridge`      | Up             |

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

## Step 4 — Demo Data

No maintained `seed_demo.py` exists. The current-run smoke request creates the
WAF evidence used by this runbook; account creation uses the provisioning
scripts in `docs/SETUP.md`.

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
- `demo-target-modsecurity`
- `demo-target-bridge`
- `demo-portal`

The technical `modsecurity`/`bridge` pair is intentionally absent unless the
separate `technical-waf` profile is also enabled.

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

## Controlled Source-Correlation Proof

This opt-in topology publishes no host ports and forces the backend to an
isolated SQLite file. Supply distinct test-only values in the current shell;
do not reuse runtime credentials:

```powershell
$env:SOURCE_TEST_API_SECRET_KEY = '<test-only-internal-key>'
$env:SOURCE_TEST_WAF_INGEST_API_KEY = '<different-test-only-waf-key>'
docker compose -f docker-compose.yml -f docker-compose.source-correlation-test.yml --profile source-correlation-test up -d --build
```

The topology contains controlled clients A and B behind one trusted proxy, a
direct untrusted client on another network, ModSecurity attached to both, and
one bridge/backend path. Only `172.30.10.2/32` is trusted for
`CF-Connecting-IP`; no ordinary host-browser path exists. The Compose file
forces `WAF_SOURCE_VERIFICATION_MODE=unverified`. The trusted-proxy requests
prove source restoration only, not authorization trust; clients A and B and
the direct untrusted client must all persist with `UNVERIFIED` status. A proof
is complete only after capturing both controlled client sources, proving the
direct client's forged header did not replace its real address, recording
transaction IDs and persisted source/provenance/status, and observing SQLi
HTTP 403.
If the build or any correlation step fails, record `Not Run` or `Partial` and
do not infer success from `docker compose config` alone.

For the controlled real-IP diagnosis, inspect the running ModSecurity service
without printing unrelated configuration or secrets:

```powershell
docker compose -p source-correlation-proof `
  -f docker-compose.yml `
  -f docker-compose.source-correlation-test.yml `
  -f docker-compose.source-correlation-test.override.yml `
  --profile source-correlation-test exec source-test-modsecurity nginx -V

docker compose -p source-correlation-proof `
  -f docker-compose.yml `
  -f docker-compose.source-correlation-test.yml `
  -f docker-compose.source-correlation-test.override.yml `
  --profile source-correlation-test exec source-test-modsecurity sh -c `
  "nginx -T 2>&1 | grep -E 'set_real_ip_from|real_ip_header|real_ip_recursive|source_correlation'"
```

The expected controlled configuration is exactly `set_real_ip_from
172.30.10.2/32`, `real_ip_header CF-Connecting-IP`, and
`real_ip_recursive off`. The diagnostic file
`logs/modsecurity/source-correlation-test/nginx_access.log` contains only the
request ID, `$remote_addr`, `$realip_remote_addr`, CF header candidate, method,
safe path, and status. A passing row has `remote_addr=172.30.10.4` or
`172.30.10.5` while `realip_remote_addr=172.30.10.2`; ModSecurity's
`transaction.client_ip` and the backend `source_ip` must match that restored
address. The direct untrusted row must retain its actual `172.30.11.4` source
even when it sends `CF-Connecting-IP: 203.0.113.123` and
`X-Forwarded-For: 203.0.113.123`.

The current WAF services use `MODSEC_AUDIT_LOG_PARTS=AIJDEFHZ`. Part `B` is
omitted so raw `Authorization`, `Cookie`, and Cloudflare Access JWT headers do
not enter new audit files. Do not re-enable `B` merely to make a screenshot or
fingerprint look richer. The live controlled proof confirmed that CRS blocking,
bridge ingestion, source provenance, and fingerprint persistence still work.

## Hosted Cloudflare Source-Correlation Proof (operator-only)

Before starting the hosted overlay, persist the observed narrow peer in the
ignored root `.env`. Do not rely on a session-only `$env:` assignment:

```dotenv
HOSTED_WAF_TRUSTED_PEER=<observed-narrow-peer-or-subnet>
WAF_SOURCE_VERIFICATION_MODE=unverified
```

Validate and start the hosted target through the checked-in launcher:

```powershell
pwsh -NoProfile -File scripts/start_hosted_target.ps1 -ValidateOnly
pwsh -NoProfile -File scripts/start_hosted_target.ps1 -Build
```

The launcher rejects missing or broad trust values and refuses any verification
mode other than `unverified`. It preserves the hosted overlay's exact
`CF-Connecting-IP` and `real_ip_recursive off` contract across fresh shells and
Compose recreates.

This is a separate manual proof. Keep `WAF_SOURCE_VERIFICATION_MODE=unverified`
until every trust-gate row below is confirmed. The final operator proof already
passed for one home-Wi-Fi request and one mobile-data request; the procedure
below remains the repeatable evidence path. Do not use the same NAT for both.
On each device record
the public egress address without sending it to the application:

```powershell
curl.exe -s https://api.ipify.org
```

Send a unique safe SQLi marker through the Access-protected target (replace the
marker for each device):

```text
https://target.cybertracesystems.com/records/search?query=%27%20UNION%20SELECT%20null,null,null--%20SOURCE_PROOF_WIFI_001
```

The expected response is CRS HTTP 403. On the host running the target, extract
only safe fields from the fresh audit event; never print the raw event,
`Authorization`, cookies, or query values outside the marker:

```powershell
$marker = 'SOURCE_PROOF_WIFI_001'
$event = Get-Content .\logs\modsecurity\demo-target\modsec_audit.jsonl -Encoding UTF8 |
  ForEach-Object { try { $_ | ConvertFrom-Json } catch {} } |
  Where-Object { $_.transaction.request.uri -like "*$marker*" } |
  Select-Object -Last 1
$txid = $event.transaction.unique_id
[pscustomobject]@{
  transaction_id = $txid
  modsecurity_client_ip = $event.transaction.client_ip
  received_cf_connecting_ip = $event.transaction.request.headers.'CF-Connecting-IP'
  request_uri = $event.transaction.request.uri
}
```

Correlate the same `$txid` in the bridge without exposing its payload:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml `
  --profile demo-target logs --no-color --tail=200 demo-target-bridge |
  Select-String -Pattern $txid
```

Use the internal lookup with `API_SECRET_KEY` kept inside the backend container:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml `
  --profile demo-target exec -e TXID=$txid backend python -c "import os,urllib.request; txid=os.environ['TXID']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}',headers={'Authorization':'Bearer '+os.environ['API_SECRET_KEY']}); print(urllib.request.urlopen(req).read().decode())"
```

The lookup must show the same canonical `source_ip`,
`source_provenance=CLOUDFLARE_CONNECTING_IP` only when that mode is explicitly
configured, and the persisted `source_verification_status`. The fingerprint is
not in the lookup contract; inspect it only through a protected database query
using the operator's normal Supabase procedure:

```sql
SELECT transaction_id, source_ip, source_provenance,
       source_verification_status, ingest_fingerprint_sha256
FROM traffic_logs
WHERE transaction_id = '<txid>';
```

Repeat with a mobile-data marker. PASS requires both known public egress IPs to
match ModSecurity, bridge-selected source, and the persisted database source;
they must not collapse to a Docker gateway. Separately send a local/direct
request with forged `CF-Connecting-IP: 203.0.113.123` and
`X-Forwarded-For: 203.0.113.123`. It must persist the actual direct source with
`DIRECT_REMOTE_ADDR` and never become `VERIFIED`.

Final evidence status: home/mobile correlation, two-network separation,
forged-header resistance, fresh-audit credential-leakage review, and hosted
restart/recreate all passed. The remaining trust gates are limited to Cloudflare
Pseudo IPv4, Worker header behavior, direct-origin isolation, and independent
confirmation of the immediate tunnel-side peer.

Before any hosted `VERIFIED` decision, prove that the origin cannot be reached
directly, identify the actual immediate tunnel peer, inspect Cloudflare
Workers and Network → Pseudo IPv4 (prefer `Off` or `Add Header`), and confirm
the fresh audit file contains no Access credentials. Unit, integration, Compose,
and local Docker evidence cannot replace this hosted packet-path proof.

---

## Step 6 — Log In to the Dashboard

Open a browser and navigate to:

```
http://localhost:3000/login
```

Before this step, a reviewed operator must apply migration `20260704_000008` to
the target Supabase environment and create at least one account with
`frontend/scripts/create_auth_account.mjs`. Do not have app startup or tests
apply the migration or mutate live Supabase.

For the temporary PR 3 pre-MFA demo path, create the account with
`--mfa-required false`. Accounts with `mfa_required=true` fail closed and do not
receive a final Auth.js session until MFA is implemented.

Enter the account id, normalized email, or normalized username and password.
Passwords are Argon2id-only; null, old scrypt, malformed, and unsupported hashes
are rejected. There is no demo-password or `AUTH_USERS_JSON` fallback. If
Supabase is unavailable, login is unavailable by design.

After the login check, verify set-password and disable behavior on a disposable
account. For rollback, revert the PR 3 cutover code before securely restoring a
pre-cutover `AUTH_USERS_JSON` value; keep the auth tables intact unless a
separate reviewed recovery requires otherwise.

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

## Step 8a — Verify Real-Time Alerts Without Refresh

Manual status as of 2026-07-19: PASS. The Alerts page received new persisted
alerts without refresh, the hosted browser connected to
`https://app.cybertracesystems.com/api/alerts/stream` with
`Accept: text/event-stream`, and the offline/online catch-up test reconnected
EventSource, refetched canonical REST state, and displayed the missed alert
without a page reload. The procedure below remains the repeatable operator
check.

Keep `http://localhost:3000/alerts` open and do not reload the page. In another
PowerShell window, create a fresh marker through the realistic WAF path:

```powershell
$marker = "SSE_$(Get-Date -Format 'yyyyMMddHHmmss')"
$url = "http://localhost:8089/records/search?query=%27%20UNION%20SELECT%20null,null,null--%20$marker"
curl.exe -s -o NUL -w "%{http_code}`n" $url
```

Confirm the bridge posts the transaction and the new alert appears in the open
dashboard without F5/manual reload. Record the persistence and visible-update
times if latency is being measured; report observed median/p95/max only from
actual controlled trials.

Then test catch-up:

1. In browser developer tools, temporarily switch the browser network offline
   or block `/api/alerts/stream`.
2. Generate another unique marker while the stream is disconnected.
3. Restore connectivity without reloading the page.
4. Confirm native EventSource reconnects, `open` causes canonical alert/stats
   refetch, and the missed alert appears automatically.

For hosted proof, the named CyberTrace deployment has now passed this check.
Do not generalize that result to every Cloudflare or proxy configuration, and do
not use a `trycloudflare.com` Quick Tunnel as authoritative SSE proof. Never
capture cookies, Authorization headers, API keys, passwords, TOTP secrets,
recovery codes, or database credentials in evidence.

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
docker compose exec -e ALERT_ID=<ALERT_ID> backend python -c "import json, os, urllib.request; alert_id=os.environ['ALERT_ID']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/alerts/{alert_id}/triage', data=json.dumps({'triage_status':'in_review'}).encode(), method='PATCH', headers={'Content-Type':'application/json','Authorization':'Bearer ' + os.environ['API_SECRET_KEY']}); print(urllib.request.urlopen(req).read().decode())"
```

> **Note:** The browser path still goes through the Next.js BFF. This direct backend call is only for smoke verification because the backend is internal to the compose network.

### 9c. Verify the update persisted

Query the same alert to confirm the triage status changed:

```powershell
docker compose exec -e ALERT_ID=<ALERT_ID> backend python -c "import os, urllib.request; alert_id=os.environ['ALERT_ID']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/alerts/{alert_id}', headers={'Authorization':'Bearer ' + os.environ['API_SECRET_KEY']}); print(urllib.request.urlopen(req).read().decode())"
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
docker compose --profile technical-waf up --build -d

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

# 6. Open browser to http://localhost:3000/login and log in

# 8. Verify pages
#    - http://localhost:3000/dashboard
#    - http://localhost:3000/alerts
#    - http://localhost:3000/ml-health

# 9. Triage update (replace <ALERT_ID>)
docker compose exec -e ALERT_ID=<ALERT_ID> backend python -c "import json, os, urllib.request; alert_id=os.environ['ALERT_ID']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/alerts/{alert_id}/triage', data=json.dumps({'triage_status':'in_review'}).encode(), method='PATCH', headers={'Content-Type':'application/json','Authorization':'Bearer ' + os.environ['API_SECRET_KEY']}); print(urllib.request.urlopen(req).read().decode())"

# 10. Verify persistence
docker compose exec -e ALERT_ID=<ALERT_ID> backend python -c "import os, urllib.request; alert_id=os.environ['ALERT_ID']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/alerts/{alert_id}', headers={'Authorization':'Bearer ' + os.environ['API_SECRET_KEY']}); print(urllib.request.urlopen(req).read().decode())"

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

### A copied seeding command fails

`seed_demo.py` is not a maintained repository script. Remove the stale command
and use the marker-correlated smoke or account provisioning workflow instead.

### ModSecurity routing expectation

- In the current compose file, ModSecurity is internal-only.
- Browser traffic on `localhost:3000` does not pass through ModSecurity.
- ModSecurity does proxy to `backend` inside the Compose network.
- Direct backend container calls are valid for smoke verification, but they bypass ModSecurity.
