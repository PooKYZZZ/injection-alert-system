# ModSecurity Live Proof

## Purpose

Capture real evidence for the live ModSecurity -> bridge -> FastAPI WAF ingest proof path.

This proof verifies that a real SQL injection probe is blocked by ModSecurity/OWASP CRS, written to the ModSecurity audit log, forwarded by the audit bridge, ingested by the FastAPI backend, classified by the ML triage path, and retrievable by transaction ID.

## Environment

* Project: CyberTrace / injection-alert-system
* Proof date/time: Mon, 22 Jun 2026, around 21:32 UTC based on observed HTTP `Date` headers
* Host shell: PowerShell 7.6.1
* Host path: `G:\AI\PDDDD\injection-alert-system`
* Backend exposure model: internal-only Docker service, shown as `8000/tcp`
* WAF public proof path: `localhost:8088`
* Backend proof lookup path: Docker-internal `docker compose exec backend ...`
* Git branch/commit: Not captured in command output
* Docker version: Not captured in command output

## Important Proof Path Note

The backend service is intentionally internal-only in Docker Compose.

Use:

```powershell
http://localhost:8088
```

for WAF-facing proof requests.

Use:

```powershell
docker compose exec backend ...
```

for backend-internal transaction lookup.

Do not use:

```powershell
http://localhost:8000
```

unless the backend port is explicitly published in Compose, for example `0.0.0.0:8000->8000/tcp`.

During this proof, `localhost:8000` was not the valid proof path.

## Commands Run

### 1. Check Compose backend status

```powershell
docker compose ps
```

Observed backend status excerpt:

```text
NAME                               IMAGE                            COMMAND                  SERVICE   CREATED          STATUS                   PORTS
injection-alert-system-backend-1   injection-alert-system-backend   "sh -c 'alembic upgr…"   backend   30 minutes ago   Up 5 minutes (healthy)   8000/tcp
```

### 2. Start required services

```powershell
docker compose up -d backend modsecurity bridge frontend
```

Observed result:

```text
[+] up 4/4
 ✔ Container injection-alert-system-backend-1     Healthy
 ✔ Container injection-alert-system-frontend-1    Started
 ✔ Container injection-alert-system-bridge-1      Started
 ✔ Container injection-alert-system-modsecurity-1 Started
```

### 3. Apply database migrations

```powershell
docker compose exec backend alembic upgrade head
docker compose restart backend
```

Observed result:

```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```

Backend became healthy after restart:

```text
NAME                               IMAGE                            COMMAND                  SERVICE   CREATED          STATUS                    PORTS
injection-alert-system-backend-1   injection-alert-system-backend   "sh -c 'alembic upgr…"   backend   32 minutes ago   Up 48 seconds (healthy)   8000/tcp
```

### 4. Verify backend lookup response schema inside container

```powershell
docker compose exec backend python -c "from web_app.presentation.schemas import WafIngestLookupResponse; print(WafIngestLookupResponse.model_fields.keys())"
```

Observed result:

```text
dict_keys(['found', 'transaction_id', 'alert_id', 'status', 'prediction', 'confidence', 'confidence_level', 'action_taken', 'ingest_source', 'source_ip', 'request_path', 'query_string', 'crs_score', 'crs_rule_ids', 'matched_rule_messages', 'matched_rule_tags', 'timestamp'])
```

### 5. Check backend port publishing

```powershell
docker compose port backend 8000
```

Observed result:

```text
invalid IP:0
```

Interpretation:

The backend should not be proven through `localhost:8000`. The valid backend lookup proof path is Docker-internal through `docker compose exec backend`.

### 6. Check WAF health endpoint

```powershell
Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8088/healthz'
```

Observed result:

```text
StatusCode        : 200
StatusDescription : OK
Content           : OK
```

### 7. Check backend API health through WAF

```powershell
Invoke-WebRequest -UseBasicParsing -Uri 'http://localhost:8088/api/health'
```

Observed result:

```text
StatusCode        : 200
StatusDescription : OK
Content           : {"status":"healthy","database":"connected"}
```

### 8. Send SQL injection probe through WAF

```powershell
$r = Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck -Uri 'http://localhost:8088/api/health?id=17%27%20OR%2017%3D17--'
$r.StatusCode
```

Observed result:

```text
403
```

### 9. Extract latest ModSecurity transaction ID

```powershell
$latestRaw = Get-Content .\logs\modsecurity\modsec_audit.jsonl -Tail 1
$latest = $latestRaw | ConvertFrom-Json
$txid = $latest.transaction.unique_id
$txid
```

Observed transaction ID:

```text
17821639659.909603
```

### 10. Verify raw ModSecurity audit fields

```powershell
$latest.transaction.client_ip
$latest.transaction.request.uri
```

Observed result:

```text
172.21.0.1
/api/health?id=17%27%20OR%2017%3D17--
```

### 11. Check bridge forwarding log

```powershell
Start-Sleep -Seconds 3
docker compose logs --tail=100 bridge
```

Observed relevant bridge log:

```text
bridge posted: status=200 transaction_id=17821639659.909603 rule_ids=['942100', '949110']
```

A previous transient bridge read error was also observed:

```text
OSError: [Errno 5] Input/output error
```

The bridge restarted and continued processing successfully. This is recorded as a resilience TODO, not a failure of this proof.

### 12. Run backend Docker-internal lookup

```powershell
docker compose exec -e TXID=$txid backend python -c "import os, urllib.request; txid=os.environ['TXID']; secret=os.environ['API_SECRET_KEY']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', headers={'Authorization': 'Bearer ' + secret}); print(urllib.request.urlopen(req).read().decode())"
```

Observed result:

```json
{
  "found": true,
  "transaction_id": "17821639659.909603",
  "alert_id": 2852,
  "status": "COMPLETED",
  "prediction": "SQL Injection",
  "confidence": 0.998819,
  "confidence_level": "HIGH",
  "action_taken": "BLOCKED",
  "ingest_source": "modsec_audit_bridge",
  "source_ip": "172.21.0.1",
  "request_path": "/api/health",
  "query_string": "id=17%27%20OR%2017%3D17--",
  "crs_score": 5,
  "crs_rule_ids": [
    "942100",
    "949110"
  ],
  "matched_rule_messages": [
    "SQL Injection Attack Detected via libinjection",
    "Inbound Anomaly Score Exceeded (Total Score: 5)"
  ],
  "matched_rule_tags": [
    "application-multi",
    "language-multi",
    "platform-multi",
    "attack-sqli",
    "paranoia-level/1",
    "OWASP_CRS",
    "capec/1000/152/248/66",
    "PCI/6.5.2",
    "modsecurity",
    "attack-generic"
  ],
  "timestamp": "2026-06-22T21:32:45Z"
}
```

### 13. Run targeted tests

```powershell
.venv\Scripts\python.exe -m pytest tests\scripts\test_waf_audit_bridge.py -q
```

Observed result:

```text
34 passed in 0.46s
```

```powershell
.venv\Scripts\python.exe -m pytest tests\integration\test_waf_ingest_route.py -q
```

Observed result:

```text
8 passed in 8.89s
```

```powershell
.venv\Scripts\python.exe -m pytest tests\unit\test_waf_ingest_use_case.py -q
```

Observed result:

```text
4 passed in 0.12s
```

```powershell
docker compose config --quiet
```

Observed result:

```text
passed with no output
```

## Expected Results

| Check                  | Expected                                                      |
| ---------------------- | ------------------------------------------------------------- |
| Compose services       | backend, modsecurity, bridge running/healthy enough for proof |
| WAF healthz            | HTTP 200                                                      |
| API health through WAF | HTTP 200                                                      |
| SQLi probe through WAF | HTTP 403                                                      |
| Audit log              | JSON event with `transaction.unique_id`                       |
| Bridge log             | `bridge posted: status=200 transaction_id=<same id>`          |
| Backend lookup         | `found: true` for same transaction ID                         |
| Prediction             | `SQL Injection`                                               |
| Confidence level       | `HIGH`                                                        |
| Action                 | `BLOCKED`                                                     |
| CRS score              | `5`                                                           |
| Source IP              | present                                                       |
| Request path           | `/api/health`                                                 |
| Query string           | present and URL-encoded                                       |
| CRS rules              | includes `942100` and `949110`                                |

## Actual Results

| Evidence                                   | Actual                                                                                              |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| Compose backend status                     | `injection-alert-system-backend-1` healthy; backend shown as `8000/tcp`                             |
| `GET /healthz` through `localhost:8088`    | HTTP 200                                                                                            |
| `GET /api/health` through `localhost:8088` | HTTP 200; `{"status":"healthy","database":"connected"}`                                             |
| SQLi request through `localhost:8088`      | HTTP 403                                                                                            |
| Latest `transaction.unique_id`             | `17821639659.909603`                                                                                |
| Raw source IP from ModSecurity audit log   | `172.21.0.1`                                                                                        |
| Raw request URI from ModSecurity audit log | `/api/health?id=17%27%20OR%2017%3D17--`                                                             |
| Bridge post result                         | `bridge posted: status=200 transaction_id=17821639659.909603 rule_ids=['942100', '949110']`         |
| Backend lookup                             | `found: true`                                                                                       |
| `prediction`                               | `SQL Injection`                                                                                     |
| `confidence`                               | `0.998819`                                                                                          |
| `confidence_level`                         | `HIGH`                                                                                              |
| `action_taken`                             | `BLOCKED`                                                                                           |
| `ingest_source`                            | `modsec_audit_bridge`                                                                               |
| `source_ip`                                | `172.21.0.1`                                                                                        |
| `request_path`                             | `/api/health`                                                                                       |
| `query_string`                             | `id=17%27%20OR%2017%3D17--`                                                                         |
| `crs_score`                                | `5`                                                                                                 |
| `crs_rule_ids`                             | `942100`, `949110`                                                                                  |
| Matched CRS messages                       | `SQL Injection Attack Detected via libinjection`; `Inbound Anomaly Score Exceeded (Total Score: 5)` |
| Targeted bridge tests                      | `34 passed`                                                                                         |
| Targeted WAF ingest route tests            | `8 passed`                                                                                          |
| Targeted WAF ingest use-case tests         | `4 passed`                                                                                          |
| Docker Compose config validation           | passed with no output                                                                               |
| Dashboard screenshot                       | Observed manually; repository file path not captured                                                |

## Acceptance Criteria

* [x] `healthz` returns 200 through `localhost:8088`
* [x] `/api/health` returns 200 through `localhost:8088`
* [x] SQLi probe returns 403 through `localhost:8088`
* [x] ModSecurity audit JSON contains `transaction.unique_id`
* [x] ModSecurity audit JSON contains source IP
* [x] ModSecurity audit JSON contains request URI
* [x] Bridge posts with `status=200`
* [x] Backend lookup returns `found: true`
* [x] Lookup `prediction` is `SQL Injection`
* [x] Lookup `confidence_level` is `HIGH`
* [x] Lookup `action_taken` is `BLOCKED`
* [x] Lookup `crs_score` is `5`
* [x] Lookup `source_ip` is present
* [x] Lookup `request_path` is `/api/health`
* [x] Lookup `query_string` is present and URL-encoded
* [x] Lookup `crs_rule_ids` includes `942100` and `949110`
* [x] Logs used in this proof do not expose API keys, authorization values, cookies, request body, or database URLs
* [x] Targeted bridge tests pass
* [x] Targeted WAF ingest route tests pass
* [x] Targeted WAF ingest use-case tests pass
* [x] Docker Compose config validates

## Final Verdict

PASS.

The live WAF ingest path is proven:

```text
SQLi request
-> ModSecurity / OWASP CRS block
-> JSON audit log
-> WAF audit bridge
-> FastAPI internal WAF ingest
-> ML triage result
-> persisted alert
-> transaction lookup proof
```

The proof confirms:

```text
transaction_id = 17821639659.909603
source_ip      = 172.21.0.1
request_path   = /api/health
query_string   = id=17%27%20OR%2017%3D17--
prediction     = SQL Injection
confidence     = 0.998819
action_taken   = BLOCKED
crs_score      = 5
crs_rule_ids   = 942100, 949110
```

## Known Follow-Up

The bridge once logged a transient file read error:

```text
OSError: [Errno 5] Input/output error
```

The bridge restarted and successfully posted the latest event afterward, so this did not invalidate the proof.

Recommended follow-up:

```text
Add a regression test and small retry/reopen handling for transient OSError from follow-mode readline().
```

This should be treated as resilience hardening, not as a blocker for the current live proof.
