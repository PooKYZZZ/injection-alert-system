# Demo Target WAF Proof

## Purpose

This document defines the local WAF proof path for the separate land-records-portal demo target from `stable/portal-pre-waf`.

This is separate from the default CyberTrace WAF proof path.

- Default CyberTrace backend WAF proof: `localhost:8088 -> ModSecurity/CRS -> bridge -> CyberTrace backend`
- Realistic final demo WAF path: `localhost:8089 -> demo-target-modsecurity -> demo-portal`
- Realistic final demo CyberTrace ingest: `localhost:8089 -> demo-target-modsecurity -> demo-target-bridge -> CyberTrace backend`

Observed results are captured in:

```text
reports/modsecurity-live-proof/demo-target-crs-proof.md
```

## Current State

The demo-target Compose profile is optional for normal developer startup. It is required for the final realistic WAF demonstration against the protected demo website.

The demo-target profile builds and starts the protected demo website as `demo-portal`.

The land-records-portal source stays separate. Do not merge the portal branch into this repository. By default, Compose uses the sibling build context `../../land-records-portal`, which resolves to `G:\AI\land-records-portal` from this checkout layout; override `DEMO_PORTAL_CONTEXT` if your portal checkout is elsewhere.

The demo-target WAF route proxies to:

```text
demo-portal:3010
```

The portal container runs the production Next.js standalone server with `HOSTNAME=0.0.0.0` and `PORT=3010`; it is exposed only to the Compose network and is not host-published by default.

The demo-target compose service uses the official `owasp/modsecurity-crs:nginx-alpine` reverse-proxy behavior through the `BACKEND` environment variable. It does not mount a custom Nginx template.

The demo-target WAF writes its own audit log:

```text
logs/modsecurity/demo-target/modsec_audit.jsonl
```

The `demo-target-bridge` service watches that separate log and posts events to the internal FastAPI WAF ingest endpoint. It is required when `8089` attacks need to appear in CyberTrace.

## How To Run

Use the demo-target compose profile from this repo:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml --profile demo-target up -d --build
```

For normal CyberTrace developer startup without the realistic demo target, the default stack remains:

```powershell
docker compose up -d
```

## Expected Services

Expected services when running the demo-target profile:

```text
frontend
backend
modsecurity
bridge
demo-target-modsecurity
demo-target-bridge
demo-portal
```

The backend remains internal-only on `8000/tcp`; do not publish or use host `localhost:8000` for this proof.

## Final Realistic Demo Smoke

Canonical command sequence lives in `docs/project-ops/SMOKE_TEST_RUNBOOK.md`.

Expected checks:

```powershell
curl.exe -s -o NUL -w "8089 home status: %{http_code}`n" http://localhost:8089/
```

Expected: `8089 home status: 200`.

```powershell
$marker = "SMOKE$(Get-Date -Format HHmmss)"
$url = "http://localhost:8089/records/search?query=%27%20UNION%20SELECT%20null,null,null--%20$marker"
curl.exe -s -o NUL -w "demo SQLi status: %{http_code}`n" $url
```

Expected: `demo SQLi status: 403`.

## Verified Evidence

| Check | Result |
|---|---|
| Compose config | PASS |
| Stack startup with demo-target profile | PASS |
| `localhost:8089` home | HTTP 200 |
| Fresh SQLi marker | `SMOKE002945`, HTTP 403 |
| Demo-target audit transaction | `178249138618.813428` |
| Demo-target audit request path | `/records/search` |
| Demo-target audit host | `localhost:8089` |
| `demo-target-bridge` post | `status=200`, transaction `178249138618.813428` |
| Backend lookup | `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `crs_score=15` |
| `localhost:8088` SQLi smoke after fix | HTTP 403 |

Dashboard check: use the dashboard alert views at `localhost:3000` to confirm the stored alert is visible to the analyst. The backend lookup above proves CyberTrace storage for the verified transaction; no fresh dashboard screenshot was captured in this docs pass.

## Evidence Handling

For each observed request, capture only safe evidence:

- actual HTTP status
- transaction ID
- source IP
- host
- request path
- safe query marker
- CRS score
- CRS rule IDs
- bridge post status
- prediction
- confidence tier
- action_taken

Do not paste cookies, Authorization headers, API keys, database URLs, or unrelated raw request bodies.

## Current Status

```text
PASS: Optional configuration and docs exist.
PASS: Observed demo-target proof report exists at `reports/modsecurity-live-proof/demo-target-crs-proof.md`.
PASS: `demo-target-bridge` forwards `8089` audit events to CyberTrace.
PASS: Verified transaction `178249138618.813428` reached backend lookup as `/records/search`, `SQL Injection`, `BLOCKED`, `crs_score=15`.
PASS: `demo-portal` is started by the demo-target Compose profile from the separate portal repo build context.
WARN: This is a verified local PD2 proof, not a production deployment.
```
