# ModSecurity Audit Log Policy

**Project:** CyberTrace / Injection Alert System
**File:** `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`
**Last updated:** 2026-06-25
**Scope:** Local PD2 WAF proof, audit evidence handling, and operator documentation

---

## 1. Purpose

This policy defines how CyberTrace handles ModSecurity audit logs during the local PD2 WAF proof.

The goal is to keep WAF evidence:

* useful for defense
* safe from accidental secret leakage
* easy to trace from WAF event to backend alert
* small enough for local development
* honest about what is implemented and what is only planned

This is a local PD2 policy. It is not a claim that production-grade centralized logging, SIEM ingestion, or automatic retention enforcement is already implemented.

---

## 2. Current Verified WAF Paths

The verified technical CyberTrace backend WAF proof path is:

```text id="tqz77q"
Client/test request
-> http://localhost:8088
-> ModSecurity / OWASP CRS
-> logs/modsecurity/modsec_audit.jsonl
-> WAF audit bridge
-> FastAPI internal WAF ingest
-> ML triage
-> persisted alert
-> dashboard / backend transaction lookup
```

Use this path for technical CyberTrace backend WAF proof requests:

```text id="x6g7rz"
http://localhost:8088
```

The verified realistic protected demo website WAF path is:

```text id="demo-target-path"
Client/test request
-> http://localhost:8089
-> demo-target-modsecurity / OWASP CRS
-> demo-target-app built from the separate land-records-portal repo
-> logs/modsecurity/demo-target/modsec_audit.jsonl
-> demo-target-bridge
-> FastAPI internal WAF ingest
-> ML triage
-> persisted alert
-> dashboard / backend transaction lookup
```

Use this path for the final realistic WAF demonstration:

```text id="demo-target-url"
http://localhost:8089
```

Backend proof lookup must use Docker-internal access:

```text id="ip8gcg"
docker compose exec backend
```

Do not document `http://localhost:8000` as the normal Docker proof path unless the backend port is explicitly published.

---

## 3. Audit Log Source of Truth

Main ModSecurity audit log path for `8088`:

```text id="qvp1p3"
logs/modsecurity/modsec_audit.jsonl
```

Demo-target ModSecurity audit log path for `8089`:

```text id="demo-target-audit-path"
logs/modsecurity/demo-target/modsec_audit.jsonl
```

Current audit log format:

```text id="jmqy6q"
JSONL
```

Meaning:

```text id="dkfo7e"
one ModSecurity audit event per line
```

The raw ModSecurity audit log is the main evidence source for WAF-layer events. Keep the `8088` and `8089` audit files separate to avoid confusing proof evidence or bridge reads.

Database alert records and dashboard cards are derived application records. They are useful, but they do not replace the raw WAF audit log when proving where an alert came from.

---

## 4. What Must Be Preserved for Evidence

For each important WAF event, preserve these fields when available:

```text id="dsl04w"
transaction_id
timestamp
source_ip
request_method
request_path
query_string
full request URI
HTTP status
CRS anomaly score
CRS rule IDs
matched rule messages
matched rule tags
backend alert ID if available
ML prediction if available
ML confidence if available
ML confidence tier if available
action_taken if available
ingest_source
```

Minimum proof-quality event evidence:

```text id="dfkgph"
transaction_id present
source_ip present
request path present
query string present when applicable
CRS score present when blocked/logged
CRS rule IDs present when blocked/logged
bridge post result visible
backend lookup found=true when testing full WAF -> backend flow
prediction/action visible when testing full ML triage flow
```

The transaction ID is the main correlation key.

It should connect:

```text id="g944qk"
ModSecurity audit log
-> bridge or demo-target-bridge log
-> backend WAF ingest record
-> persisted alert
-> dashboard evidence
```

---

## 5. What Must Not Be Logged in Normal Proof Docs

Do not expose secrets or sensitive raw data in normal logs, screenshots, proof reports, or Markdown docs.

Do not log or paste:

```text id="i58g02"
API_SECRET_KEY
INTERNAL_API_KEY
Authorization headers
Bearer tokens
cookies
session tokens
database URLs
Supabase credentials
private keys
passwords
raw request bodies by default
full raw audit events by default
```

Allowed in normal proof summaries:

```text id="ns5fvw"
transaction_id
timestamp
source_ip
request method
request path
query string if needed for attack proof
HTTP status
CRS score
CRS rule IDs
matched rule messages
matched rule tags
ML prediction
confidence tier
action_taken
```

Raw request bodies should only be captured when they are necessary for a specific test, and only if the payload is safe test data.

If a raw body is included in a local artifact, the artifact must be treated as local evidence and not pasted into public docs or screenshots without review.

---

## 6. Log Redaction and Sanitization Rules

Any documentation or generated report must follow these rules:

```text id="kjw2b7"
replace secrets with [REDACTED]
do not print Authorization values
do not print cookies
do not print API keys
do not print database URLs
do not dump raw request bodies into Markdown
do not dump full raw audit events into Markdown
prefer short safe excerpts
```

Safe excerpt example:

```text id="uvs332"
transaction_id: 17821639659.909603
request_path: /api/health
query_string: id=17%27%20OR%2017%3D17--
crs_score: 5
crs_rule_ids: 942100, 949110
action_taken: BLOCKED
prediction: SQL Injection
```

Unsafe excerpt example:

```text id="g3vexz"
Authorization: Bearer <real secret>
Cookie: <real session>
DATABASE_URL=<real db url>
raw full request body with sensitive data
```

---

## 7. Log Storage Boundary

There are three different log/evidence types. Do not mix them up.

### 7.1 ModSecurity audit log

```text id="ifhz6w"
logs/modsecurity/modsec_audit.jsonl
logs/modsecurity/demo-target/modsec_audit.jsonl
```

Purpose:

```text id="gyndd7"
raw WAF transaction evidence for the `8088` technical proof path and the `8089` realistic demo-target path
```

The main `bridge` reads `logs/modsecurity/modsec_audit.jsonl`. The `demo-target-bridge` reads `logs/modsecurity/demo-target/modsec_audit.jsonl`.

### 7.2 Docker container logs

Examples:

```text id="bubij5"
docker compose logs modsecurity
docker compose logs bridge
docker compose logs backend
```

Purpose:

```text id="iw14ql"
container troubleshooting and runtime behavior
```

Docker logs are not the same as the ModSecurity audit log file.

### 7.3 Backend/database alert records

Purpose:

```text id="qibgpd"
application alert state, ML triage result, dashboard display
```

Database records are useful for dashboard proof, but they are not the raw WAF audit evidence.

---

## 8. Local Retention Policy

There are two categories of audit evidence.

### 8.1 Checked-in proof evidence

Checked-in proof evidence belongs under:

```text id="gotah5"
reports/modsecurity-live-proof/
```

This evidence should not be physically deleted during PD2.

Examples:

```text id="gxr3bt"
reports/modsecurity-live-proof/e2e-proof.md
reports/modsecurity-live-proof/crs-baseline.md
reports/modsecurity-live-proof/safe screenshots
reports/modsecurity-live-proof/safe audit excerpts
```

Checked-in proof evidence must be reviewed for secrets before commit.

### 8.2 Routine local audit logs

Routine local logs belong under:

```text id="r2r4z2"
logs/modsecurity/
logs/modsecurity/demo-target/
```

Routine local logs may be rotated, archived, or cleared after proof evidence has been captured.

Before clearing routine logs, capture any needed proof evidence under:

```text id="w4ticq"
reports/modsecurity-live-proof/
```

Routine cleanup must not remove checked-in proof evidence.

---

## 9. Local Rotation Recommendation

Recommended local PD2 rotation target:

```text id="e0dgvr"
max active audit log size: 10 MB
rotated files to keep: 5
compression: optional
automatic enforcement: not implemented yet
```

Suggested rotated naming style:

```text id="r3kxqr"
logs/modsecurity/modsec_audit.jsonl
logs/modsecurity/modsec_audit.jsonl.1
logs/modsecurity/modsec_audit.jsonl.2
logs/modsecurity/modsec_audit.jsonl.3
logs/modsecurity/modsec_audit.jsonl.4
logs/modsecurity/modsec_audit.jsonl.5
```

Use the same naming style under `logs/modsecurity/demo-target/` for the demo-target audit file if local rotation is added later.

This document defines the policy target only.

It does not implement automatic rotation.

Do not mark automatic rotation as done unless a tested rotation mechanism is added and verified.

---

## 10. Why Automatic Rotation Is Not Implemented Yet

Automatic rotation is intentionally not implemented in this policy because the current priority is to avoid breaking the proven WAF evidence path.

The current working path depends on:

```text id="a702bg"
ModSecurity writing logs
bridge reading logs
backend ingesting events
transaction lookup proving storage
```

Poorly implemented rotation can cause missed lines, stale file handles, or confusing evidence.

If automatic rotation is added later, it must be tested with:

```text id="s4vmuc"
normal WAF request still passes
blocked SQLi request still writes audit event
bridge still reads new event after rotation
backend lookup still finds transaction
no secrets appear in rotation logs
reports/modsecurity-live-proof/ is never touched
```

---

## 11. Manual Operator Commands

Check whether the policy file exists:

```powershell id="gsrmch"
Test-Path .\docs\project-ops\MODSECURITY_AUDIT_LOG_POLICY.md
```

Check audit log size:

```powershell id="a4lnda"
Get-Item .\logs\modsecurity\modsec_audit.jsonl | Select-Object FullName, Length, LastWriteTime
```

Check demo-target audit log size:

```powershell id="demo-target-size"
Get-Item .\logs\modsecurity\demo-target\modsec_audit.jsonl | Select-Object FullName, Length, LastWriteTime
```

View latest audit event:

```powershell id="c11j3e"
Get-Content .\logs\modsecurity\modsec_audit.jsonl -Tail 1
```

View latest demo-target audit event:

```powershell id="demo-target-tail"
Get-Content .\logs\modsecurity\demo-target\modsec_audit.jsonl -Tail 1
```

Capture a local proof snapshot before clearing routine logs:

```powershell id="ivc4ga"
New-Item -ItemType Directory -Force .\reports\modsecurity-live-proof | Out-Null
Copy-Item .\logs\modsecurity\modsec_audit.jsonl .\reports\modsecurity-live-proof\modsec_audit_snapshot.jsonl
```

Extract the latest transaction ID:

```powershell id="t3ylt9"
$latestRaw = Get-Content .\logs\modsecurity\modsec_audit.jsonl -Tail 1
$latest = $latestRaw | ConvertFrom-Json
$txid = $latest.transaction.unique_id
if ([string]::IsNullOrWhiteSpace($txid)) { throw "txid missing" }
$txid
```

Run Docker-internal backend lookup:

```powershell id="bzzflm"
docker compose exec -e TXID=$txid backend python -c "import os, urllib.request; txid=os.environ['TXID']; secret=os.environ['API_SECRET_KEY']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', headers={'Authorization': 'Bearer ' + secret}); print(urllib.request.urlopen(req).read().decode())"
```

---

## 12. CRS Baseline Evidence Rule

CRS baseline evidence must be created from actual observed results.

Do not invent:

```text id="havsnf"
HTTP status
transaction IDs
CRS scores
rule IDs
matched messages
backend lookup results
```

The CRS baseline report should be written after running the requests.

Recommended CRS baseline report path:

```text id="sp6snh"
reports/modsecurity-live-proof/crs-baseline.md
```

Minimum baseline request set:

```text id="cxtxr2"
normal health request
normal API health request
SQLi request
XSS-like request
command/code-injection-like request
weird-but-legit request
```

Purpose:

```text id="j20h9s"
prove normal traffic still passes
prove attack-looking traffic is handled by CRS
record false-positive behavior honestly
separate CRS behavior from ML triage behavior
```

---

## 13. Dataset Replay Evidence Rule

Dataset replay evidence may be used as broader CRS evidence, but it must not replace the small fixed CRS baseline.

Dataset replay should be treated as a secondary evidence layer.

Recommended output path:

```text id="x0jxzn"
reports/modsecurity-replay/<timestamp>/
```

Dataset replay must be:

```text id="l2a700"
local only
deterministic or clearly bounded
limited in sample size
based on existing sample_exports
not run against external targets
not AI-generated
not fuzzing
not full 907k replay
```

Safe replay limits for PD2:

```text id="p5c6tm"
start with 5 samples
then 30 samples if clean
do not replay the full dataset unless explicitly approved
```

Reports should include:

```text id="ntj6bq"
sample count
dataset source path
timestamp
git commit if available
HTTP status
ModSecurity detected true/false
transaction_id
CRS rule IDs
matched message summary
skip/failure reason
```

Reports should not include:

```text id="cztr29"
API keys
Authorization headers
cookies
database URLs
raw request bodies in Markdown
external target URLs
```

---

## 14. SIEM Position

CyberTrace does not deploy a full SIEM for PD2.

Not implemented:

```text id="wu5oi9"
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
centralized production log retention
```

The current policy keeps logs structured and evidence-friendly so future SIEM-compatible export remains possible.

If future SIEM-compatible export is implemented, it should export normalized alert summaries separately from raw ModSecurity audit logs.

Example future export path:

```text id="ee9vua"
logs/exports/security_alerts.jsonl
```

This future export is optional and not part of the current PD2 WAF proof.

---

## 15. Production Position

This policy is for local PD2 development and defense evidence.

It does not claim production-grade retention.

A real production deployment would still need decisions for:

```text id="wz6trr"
centralized collection
access control
tamper resistance
encryption at rest
backup/archive location
retention duration
legal/compliance requirements
automated rotation
monitoring when logging stops
alert review process
disposal process
```

Do not claim these are implemented until they are actually built and verified.

---

## 16. Panel-Ready Explanation

Use this explanation during defense:

```text id="vr2q4d"
We keep ModSecurity audit logs in JSONL format at logs/modsecurity/modsec_audit.jsonl. The important evidence is the transaction ID, timestamp, source IP, request path, query string, CRS score, CRS rule IDs, matched rule messages, and backend lookup result when available. Routine local logs can be rotated or cleared after proof evidence is captured, but checked-in proof evidence under reports/modsecurity-live-proof/ is preserved. We intentionally do not deploy a full SIEM for PD2 because that would expand the scope. The logs are structured so future SIEM-compatible export remains possible.
```

Shorter version:

```text id="bcqcdr"
Raw WAF logs prove what ModSecurity/CRS saw. Backend records prove what CyberTrace stored. Dashboard proof shows what the analyst sees. We keep those layers separate so the evidence is traceable and not overclaimed.
```

---

## 17. Done Criteria

This policy is considered documented when:

```text id="lh2k4f"
PASS: file exists at docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md
PASS: audit format is documented as JSONL
PASS: audit path is documented as logs/modsecurity/modsec_audit.jsonl
PASS: demo-target audit path is documented as logs/modsecurity/demo-target/modsec_audit.jsonl
PASS: preserved evidence fields are listed
PASS: sensitive-data exclusions are listed
PASS: local retention behavior is documented
PASS: local rotation target is documented
PASS: reports/modsecurity-live-proof/ is identified as proof evidence location
PASS: localhost:8088 remains the WAF proof path
PASS: localhost:8089 remains the realistic protected demo website proof path
PASS: backend lookup remains Docker-internal
PASS: docs do not claim full SIEM deployment
PASS: docs do not claim production retention is implemented
WARN: automatic rotation is not implemented
WARN: production retention is planned, not implemented
FAIL: docs say localhost:8000 is the normal Docker proof path
FAIL: docs say Wazuh/SIEM is currently deployed
FAIL: docs say automatic rotation is implemented
FAIL: docs expose API keys, Authorization headers, cookies, or DB URLs
```

---

## 18. Next Task After This Policy

After this policy is created and referenced by the docs, the next task is:

```text id="whjpjh"
Create CRS-only baseline evidence report.
```

Target report:

```text id="xuelmj"
reports/modsecurity-live-proof/crs-baseline.md
```

That report must be based on actual observed request results, not invented expected results.
