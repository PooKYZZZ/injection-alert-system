# ModSecurity Audit Log Policy

**Location:** `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`
**Project:** CyberTrace / Injection Alert System
**Last updated:** 2026-06-23
**Scope:** Local PD2 WAF proof and operator evidence handling

---

## 1. Purpose

This policy defines how the project handles ModSecurity audit logs for the local PD2 proof path.

The goal is to keep WAF evidence useful, safe, and defensible without pretending that the project already has a full production SIEM/log-management deployment.

This policy covers:

* current audit log format
* current audit log path
* fields that must be preserved for evidence
* sensitive data handling
* local rotation recommendation
* local retention rules
* distinction between raw WAF logs, Docker logs, and database alert records
* what is not implemented yet

---

## 2. Current WAF Proof Truth

The verified local WAF proof path is:

```text
Client/test request
-> localhost:8088
-> ModSecurity / OWASP CRS
-> logs/modsecurity/modsec_audit.jsonl
-> WAF audit bridge
-> FastAPI internal WAF ingest
-> ML triage
-> persisted alert
-> Docker-internal transaction lookup
```

Use this path for WAF-facing proof requests:

```text
http://localhost:8088
```

Do not use this as the Docker proof path unless backend port `8000` is explicitly published:

```text
http://localhost:8000
```

Backend lookup proof must use Docker-internal access through `docker compose exec backend`.

---

## 3. Audit Log Format

Current ModSecurity audit log format:

```text
JSONL
```

Current local audit log path:

```text
logs/modsecurity/modsec_audit.jsonl
```

Each line should be treated as one ModSecurity audit event.

Reason:

* JSONL is easy for the bridge to consume line by line.
* JSONL is easy to inspect during defense.
* JSONL is compatible with common security-log/SIEM-style processing later.
* JSONL avoids custom parsing when structured fields already exist.

---

## 4. Evidence Fields To Preserve

For each important WAF event, the evidence path should preserve these fields when available:

```text
transaction_id
timestamp
source_ip
request_method
request_path
query_string
full request URI
CRS score
CRS rule IDs
matched rule messages
matched rule tags
backend alert ID
ML prediction
ML confidence
ML confidence tier
action_taken
ingest_source
```

Minimum proof-quality evidence for a blocked injection request:

```text
transaction_id present
source_ip present
request_path present
query_string present
crs_score present
crs_rule_ids present
bridge post shown
backend lookup found=true
prediction shown
action_taken shown
```

The raw ModSecurity transaction ID is the main correlation key between:

```text
raw WAF audit log
-> bridge log
-> backend WAF ingest lookup
-> persisted alert
-> dashboard evidence
```

---

## 5. Sensitive Data Handling

Bridge logs and operator docs must not expose secrets.

Do not log or paste these into normal bridge logs, tracker docs, screenshots, or proof notes:

```text
API_SECRET_KEY
INTERNAL_API_KEY
Authorization headers
Bearer tokens
cookies
session tokens
database URLs
Supabase credentials
raw request bodies
full raw audit events unless intentionally captured as local proof evidence
```

Allowed in normal proof summaries:

```text
transaction_id
source_ip
request_path
query_string
CRS rule IDs
CRS score
matched rule names/messages
prediction
confidence tier
action_taken
HTTP status code
```

Request bodies should not be used as default proof evidence. If a request body is needed for a targeted test, capture only the smallest safe sample and clearly mark it as test data.

---

## 6. Local Rotation Recommendation

For local PD2 development and demo work, use this recommended routine rotation target:

```text
max size per routine local audit log: 10 MB
rotated files to keep locally: 5
compression: optional
```

Example naming style:

```text
logs/modsecurity/modsec_audit.jsonl
logs/modsecurity/modsec_audit.jsonl.1
logs/modsecurity/modsec_audit.jsonl.2
logs/modsecurity/modsec_audit.jsonl.3
logs/modsecurity/modsec_audit.jsonl.4
logs/modsecurity/modsec_audit.jsonl.5
```

This policy documents the target behavior. Automatic rotation is not yet implemented by this document.

Do not build a custom Python rotation system inside the bridge unless later evidence shows it is necessary.

---

## 7. Local Retention Policy

There are two types of audit log data:

### 7.1 Checked-in proof evidence

Checked-in proof evidence belongs under:

```text
reports/modsecurity-live-proof/
```

Do not physically delete checked-in proof evidence during PD2.

Proof evidence should include enough data to defend the WAF path without exposing secrets.

Examples:

```text
reports/modsecurity-live-proof/e2e-proof.md
reports/modsecurity-live-proof/dashboard screenshots
reports/modsecurity-live-proof/safe audit log excerpts
```

### 7.2 Routine local audit logs

Routine local logs live under:

```text
logs/modsecurity/
```

Routine local logs may be rotated, archived, or cleared after proof evidence has been captured.

Before clearing routine local logs, capture any needed proof evidence under:

```text
reports/modsecurity-live-proof/
```

Routine local log cleanup must not remove checked-in proof evidence.

---

## 8. Manual Operator Commands

Inspect audit log size:

```powershell
Get-Item .\logs\modsecurity\modsec_audit.jsonl | Select-Object FullName, Length, LastWriteTime
```

View latest audit events:

```powershell
Get-Content .\logs\modsecurity\modsec_audit.jsonl -Tail 3
```

Capture a local proof snapshot before cleanup:

```powershell
New-Item -ItemType Directory -Force .\reports\modsecurity-live-proof | Out-Null
Copy-Item .\logs\modsecurity\modsec_audit.jsonl .\reports\modsecurity-live-proof\modsec_audit_snapshot.jsonl
```

Check latest transaction ID:

```powershell
$latestRaw = Get-Content .\logs\modsecurity\modsec_audit.jsonl -Tail 1
$latest = $latestRaw | ConvertFrom-Json
$txid = $latest.transaction.unique_id
if ([string]::IsNullOrWhiteSpace($txid)) { throw "txid missing" }
$txid
```

Run Docker-internal backend lookup:

```powershell
docker compose exec -e TXID=$txid backend python -c "import os, urllib.request; txid=os.environ['TXID']; secret=os.environ['API_SECRET_KEY']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', headers={'Authorization': 'Bearer ' + secret}); print(urllib.request.urlopen(req).read().decode())"
```

---

## 9. Important Distinctions

ModSecurity audit logs are not the same as Docker container logs.

```text
ModSecurity audit log:
logs/modsecurity/modsec_audit.jsonl
Purpose: raw WAF transaction evidence
```

```text
Docker logs:
docker compose logs bridge
docker compose logs modsecurity
Purpose: container stdout/stderr troubleshooting
```

```text
Database alert records:
traffic_logs / alert records in the backend database
Purpose: persisted application alert state and dashboard data
```

Do not treat one as a full replacement for the others.

A dashboard alert should be traceable back to the ModSecurity transaction ID when it came from the WAF path.

---

## 10. SIEM Compatibility Position

This project does not deploy a full SIEM for PD2.

No current implementation claim is made for:

```text
Wazuh manager
Wazuh agent
Wazuh indexer
Wazuh dashboard
Elasticsearch
Loki
Kafka
Celery
Kubernetes
Helm
Terraform
```

The current policy only keeps logs structured and evidence-friendly so future SIEM-compatible export remains possible.

Future SIEM-compatible export, if implemented, should export normalized alert summaries separately from the raw ModSecurity audit log.

Raw WAF evidence should remain the source for transaction-level proof.

---

## 11. Production Position

This policy is for local PD2 proof and operator discipline.

This is not a production retention implementation.

Production deployment would still need separate decisions for:

```text
centralized log collection
access control for logs
tamper resistance
backup/archive location
retention duration
legal/compliance requirements
encryption at rest
automatic rotation
incident-response review process
disposal process
```

Do not document production-grade retention as implemented until it is actually implemented and verified.

---

## 12. Panel-Ready Explanation

Short answer:

```text
We keep ModSecurity audit logs in JSONL format at logs/modsecurity/modsec_audit.jsonl for local WAF proof. The important evidence is the transaction ID, source IP, request path, query string, CRS score, CRS rules, bridge post, and backend lookup result. Routine local logs can be rotated after evidence is captured, but checked-in proof evidence under reports/modsecurity-live-proof/ is preserved. We intentionally do not deploy a full SIEM for PD2; the logs are structured so future SIEM-compatible export is possible without bloating the current project.
```

---

## 13. Done Criteria

This policy is satisfied when:

```text
PASS: audit format is documented as JSONL
PASS: audit path is documented as logs/modsecurity/modsec_audit.jsonl
PASS: evidence fields are listed
PASS: sensitive-data handling is documented
PASS: local rotation recommendation is documented
PASS: local retention behavior is documented
PASS: proof evidence location is documented
PASS: localhost:8088 remains the WAF proof path
PASS: Docker-internal backend lookup remains the backend proof path
PASS: docs do not claim full SIEM deployment
PASS: docs do not claim production retention is implemented
WARN: automatic rotation is still not implemented
WARN: production retention is still planned
FAIL: docs say localhost:8000 is the Docker proof path
FAIL: docs say Wazuh/SIEM is currently deployed
FAIL: docs suggest raw request bodies/secrets are safe to log
```
