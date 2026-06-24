# Demo Target WAF Proof

## Purpose

This document defines the optional local WAF proof path for the portal demo target from `stable/portal-pre-waf`.

This is separate from the default CyberTrace WAF proof path.

- Default CyberTrace WAF proof: `localhost:8088 -> ModSecurity/CRS -> CyberTrace backend`
- Optional portal-target WAF proof: `localhost:8089 -> ModSecurity/CRS -> portal demo target`

No proof is claimed until observed results are captured in:

```text
reports/modsecurity-live-proof/demo-target-crs-proof.md
```

## Local Runtime Assumption

The portal target must be started separately by the user on host port `3010`.

Codex must not start the portal, install dependencies, run Docker, or execute attack requests for this proof.

The optional WAF route proxies to:

```text
host.docker.internal:3010
```

The portal source stays separate. Do not merge the portal branch into this repository.

## Optional Compose Path

Use the optional compose override only when running the demo-target proof:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml --profile demo-target up -d demo-target-modsecurity
```

The normal CyberTrace stack remains:

```powershell
docker compose up -d
```

## Planned Normal Requests

These are planned requests only. Record actual observed results later.

```powershell
Invoke-WebRequest -UseBasicParsing "http://localhost:8089/"
Invoke-WebRequest -UseBasicParsing "http://localhost:8089/records/search?query=Pasig"
Invoke-WebRequest -UseBasicParsing "http://localhost:8089/records/LND-2026-0001"
Invoke-WebRequest -UseBasicParsing "http://localhost:8089/transactions/status?ref=SUP-2026-0001"
```

## Planned Controlled CRS Checks

These are controlled local-lab checks only. Do not run them against external targets.

```powershell
Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck "http://localhost:8089/records/search?query=%27%20UNION%20SELECT%20null,null,null--%20"
Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck "http://localhost:8089/transactions/status?ref=%3Cscript%3Ealert%281%29%3C%2Fscript%3E"
Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck -Method POST "http://localhost:8089/comments/submit" -ContentType "application/x-www-form-urlencoded" -Body "displayName=%3Cimg%20src%3Dx%20onerror%3Dalert%281%29%3E&message=ComplianceTest"
Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck -Method POST "http://localhost:8089/login/submit" -ContentType "application/x-www-form-urlencoded" -Body "username=demo&password=%27%20OR%20%271%27%3D%271"
```

## Evidence To Capture Later

For each observed request, capture only safe evidence:

- actual HTTP status
- transaction ID
- source IP
- request URI
- CRS rule IDs
- matched messages
- short verdict
- safe notes only

Do not paste cookies, Authorization headers, API keys, database URLs, or unrelated raw request bodies.

## Current Status

```text
WARN: Optional configuration and docs exist.
WARN: User must run the portal target on host port 3010.
WARN: Observed demo-target proof report is still pending.
```
