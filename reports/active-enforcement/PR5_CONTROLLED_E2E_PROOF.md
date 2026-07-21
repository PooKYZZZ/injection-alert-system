# PR5 Controlled Full-Stack E2E Proof

## Document purpose

This report records the controlled manual end-to-end validation of PR5 LOW/MEDIUM active enforcement for the CyberTrace demo portal.

It verifies the integrated path:

```text
Browser
→ ModSecurity / OWASP CRS
→ Land Records Demo Portal
→ CyberTrace enforcement API
→ PostgreSQL enforcement state
→ Cloudflare Turnstile test verification
→ portal ALLOW / CHALLENGE / THROTTLE behavior
```

This is a controlled local acceptance test. It is not a production deployment report.

---

## Tested revisions

```text
CyberTrace backend PR #90
Commit: ea3ad66

Land Records Demo Portal PR #91
Commit: 665cb83
```

---

## Scope

The protected application boundary tested was:

```text
http://localhost:8089/records/search
```

PR5 enforcement was validated only for:

```text
Scope: RECORD_SEARCH
Route: /records/search
```

The tests focused on:

- LOW recommendation behavior
- MEDIUM recommendation behavior
- successful challenge verification
- challenge-grant persistence
- fixed-window request counting
- MEDIUM throttling
- invalid Turnstile behavior
- CyberTrace backend outage fail-open behavior
- absence of fabricated grant/window state during failure paths

---

## Test environment

```text
Operating environment:
Windows PowerShell + Docker Desktop

Application stack:
Docker Compose

Database:
Disposable PostgreSQL 16 container

Database container:
cybertrace-pr5-e2e-db

Database name:
cybertrace_e2e

Portal:
http://localhost:8089

Portal APP_ENV:
development

Enforcement mode:
enforce

Source trust:
Controlled test-only unverified-source bypass

Turnstile:
Cloudflare-published test credentials

Hosted production ENFORCE:
Not enabled
```

The controlled browser/source identity used during the tests was:

```text
172.18.0.1
```

---

## Configuration summary

The local E2E configuration used the PR5 defaults and safeguards:

```text
LOW window:
60 seconds

LOW maximum unchallenged requests:
5

MEDIUM window:
60 seconds

MEDIUM maximum requests after grant:
10

Challenge grant TTL:
300 seconds

Backend Turnstile timeout:
3 seconds

Portal challenge timeout:
5000 milliseconds
```

The environment also used:

```text
APP_ENV=development
ENFORCEMENT_ALLOW_UNVERIFIED_SOURCE_FOR_TESTS=true
```

This bypass was used only for controlled local testing.

---

# Results summary

| Test | Result |
|---|---|
| Local portal through ModSecurity reachable | PASS |
| Demo portal upstream resolution | PASS |
| Demo target bridge to backend | PASS |
| Backend health | PASS |
| Disposable PostgreSQL availability | PASS |
| LOW recommendation match | PASS |
| LOW challenge displayed | PASS |
| LOW Turnstile verification | PASS |
| LOW challenge grant persisted | PASS |
| LOW requests remained allowed while grant was valid | PASS |
| LOW counter not incremented while grant was valid | PASS |
| MEDIUM first request challenged | PASS |
| MEDIUM Turnstile verification | PASS |
| MEDIUM challenge grant persisted | PASS |
| MEDIUM request-window counting | PASS |
| MEDIUM throttling | PASS |
| Positive retry countdown | PASS |
| Fixed-window rollover behavior | PASS |
| Invalid Turnstile blocked access | PASS |
| Invalid Turnstile created no grant | PASS |
| Invalid Turnstile created no request window | PASS |
| Backend outage failed open | PASS |
| Backend outage created no fake grant | PASS |
| Backend outage created no fake request window | PASS |
| Stack restored healthy after testing | PASS |

---

# Test evidence

## 1. Local stack and protected route

The local portal was reached through the realistic protected path:

```text
http://localhost:8089/records/search
```

Observed result:

```text
HTTP/1.1 200 OK
Server: nginx
X-Powered-By: Next.js
```

The ModSecurity container was also able to reach the demo portal directly:

```text
http://demo-portal:3010/records/search
```

Observed result:

```text
HTTP 200
```

An earlier `502 Bad Gateway` was traced to the long-running ModSecurity container retaining a stale internal Docker IP for the recreated portal container.

Recreating:

```text
demo-target-modsecurity
```

resolved the stale upstream, after which both local and public target requests returned normal application responses.

---

## 2. Controlled source identity

A WAF-blocked marker request was used to determine the source address seen by the local protected path.

Observed source:

```text
172.18.0.1
```

This source was used when creating controlled LOW and MEDIUM recommendations.

---

# LOW enforcement validation

## LOW recommendation used

```text
Scope:
RECORD_SEARCH

Tier:
LOW

Recommended action:
CHALLENGE

Mode:
ENFORCE

Policy version:
confidence-enforcement-v2

Source:
172.18.0.1
```

## Observed behavior

The browser was allowed to access the normal records page until the LOW threshold was crossed.

The verification page then appeared:

```text
Verification required
```

The Cloudflare always-pass test widget completed quickly, causing the verification page to appear briefly and then disappear after the portal automatically reloaded.

A successful LOW grant was persisted in PostgreSQL:

```text
source_ip:
172.18.0.1

scope:
RECORD_SEARCH

enforcement_tier:
LOW

policy_version:
confidence-enforcement-v2

verified_at:
2026-07-21 16:33:57.250067+00

expires_at:
2026-07-21 16:38:57.250067+00
```

After the grant existed:

- the records page remained accessible
- repeated refreshes remained allowed
- the LOW request window was not recreated or incremented

Observed state after the valid grant:

```text
enforcement_challenge_grants:
1 LOW row

enforcement_request_windows:
0 rows
```

This is consistent with the intended LOW behavior:

```text
Valid LOW grant
→ ALLOW
→ skip LOW_LIGHT counter increment
```

## LOW result

```text
PASS
```

## Evidence limitation

The LOW transition was functionally observed, including a prior `LOW_LIGHT = 6` state and the challenge page.

However, the request-window table was manually truncated during troubleshooting after the challenge had already succeeded. Because refreshes were also performed quickly, a perfectly controlled screenshot pair showing exactly:

```text
5 → 6
```

was not preserved.

This does not invalidate the functional result, but a polished appendix may rerun the exact transition one request at a time.

---

# MEDIUM enforcement validation

## MEDIUM recommendation used

```text
Scope:
RECORD_SEARCH

Tier:
MEDIUM

Recommended action:
THROTTLE

Mode:
ENFORCE

Policy version:
confidence-enforcement-v2

Source:
172.18.0.1
```

## Immediate challenge

The first MEDIUM request displayed:

```text
Verification required
```

The Cloudflare always-pass test widget verified successfully.

A MEDIUM challenge grant was persisted:

```text
source_ip:
172.18.0.1

enforcement_tier:
MEDIUM

policy_version:
confidence-enforcement-v2

verified_at:
2026-07-21 16:40:30.239594+00

expires_at:
2026-07-21 16:45:30.239594+00
```

## Request counting and throttling

After verification, MEDIUM requests were counted using fixed 60-second windows.

Observed database windows included:

```text
16:40:00–16:41:00 → 6 requests
16:41:00–16:42:00 → 12 requests
16:42:00–16:43:00 → 39 requests
16:43:00–16:44:00 → 15 requests
```

A subsequent query showed the latest window increasing to:

```text
16 requests
```

The high counts were caused by intentionally repeated browser refreshes.

When the request limit was exceeded, the portal displayed:

```text
Search temporarily limited
```

with positive retry messages such as:

```text
Please wait 17 seconds before trying again.
```

and later:

```text
Please wait 3 seconds before trying again.
```

This demonstrated that `retry_after_seconds` was positive and decreased toward the end of the current fixed window.

The observed behavior matched the intended policy:

```text
MEDIUM with valid grant
→ requests 1–10 allowed
→ request 11 and later throttled
→ retry until current 60-second window ends
```

## MEDIUM result

```text
PASS
```

## Evidence limitation

Because refreshes were intentionally spammed during manual testing, the screenshots do not preserve a perfectly controlled one-at-a-time sequence of:

```text
10 → 11
```

The functional behavior was nevertheless demonstrated:

- a valid MEDIUM grant existed
- request counts exceeded 10
- the throttle page appeared
- retry time was positive
- separate fixed windows were persisted

A polished appendix may rerun the exact boundary one request at a time.

---

# Invalid Turnstile validation

## Test configuration

The failure test used Cloudflare's published always-fail test pair.

Observed browser behavior:

```text
Verification required
```

followed by:

```text
Verification failed. Please try again.
```

The Cloudflare test widget displayed its failure state and troubleshooting interface.

The protected records remained hidden.

## Database evidence

After the failed verification:

```text
enforcement_challenge_grants:
0 rows

enforcement_request_windows:
0 rows
```

This proves:

```text
Failed challenge
→ no grant
→ no MEDIUM request window
→ no protected access
```

The failure occurred at the widget level before a successful application challenge POST was completed.

## Invalid Turnstile result

```text
PASS
```

---

# Backend outage fail-open validation

## Test method

A fresh active MEDIUM recommendation remained in PostgreSQL.

The CyberTrace backend container was stopped while:

- ModSecurity remained available
- the demo portal remained available
- PostgreSQL remained available

The protected search page was repeatedly refreshed while the backend was offline.

## Observed browser behavior

The normal records page remained accessible.

The following did not appear:

```text
Verification required
Search temporarily limited
500 error
502 error
```

This demonstrates the intended evaluation-failure behavior:

```text
CyberTrace policy evaluation unavailable
→ portal fails open
→ search remains usable
```

## Database evidence

The final fail-open snapshot showed:

```text
Recommendation:
RECORD_SEARCH
MEDIUM
THROTTLE
ENFORCE
confidence-enforcement-v2
```

while:

```text
enforcement_request_windows:
0 rows

enforcement_challenge_grants:
0 rows
```

This proves the outage path did not fabricate:

- a challenge grant
- a request counter
- an enforcement decision state in PostgreSQL

## Backend outage result

```text
PASS
```

---

# Final stack health

After the outage test, the backend was restarted.

Observed status:

```text
backend:
healthy

demo-portal:
healthy

demo-target-modsecurity:
healthy

frontend:
running

demo-target-bridge:
running

PostgreSQL:
running
```

The protected route returned:

```text
HTTP 200
```

---

# Security observations

The browser challenge flow used the same-origin route:

```text
POST /records/search/challenge
```

The test did not reveal any evidence of the following appearing in browser storage or public request headers:

```text
ENFORCEMENT_CHECK_API_KEY
Turnstile secret
DATABASE_URL
server-side challenge grant
```

The challenge grant was stored server-side in PostgreSQL using bounded metadata:

```text
source_ip
scope
tier
policy_version
verified_at
expires_at
```

Raw Turnstile tokens and service secrets were intentionally excluded from screenshots and evidence.

---

# Acceptance conclusion

The controlled full-stack PR5 manual E2E test is accepted.

The following integrated behaviors were demonstrated:

```text
LOW
→ recommendation matched
→ challenge occurred after threshold
→ Turnstile verification succeeded
→ grant persisted
→ portal reloaded to ALLOW
→ LOW counter was bypassed while grant remained valid

MEDIUM
→ first request challenged
→ Turnstile verification succeeded
→ grant persisted
→ requests were counted in fixed windows
→ request volume above the configured limit caused THROTTLE
→ positive retry countdown was displayed

Invalid challenge
→ user remained blocked
→ no grant created
→ no request window created

Backend outage
→ policy evaluation failed open
→ search remained usable
→ no fake grant or counter was persisted
```

## Overall result

```text
PR5 CONTROLLED FULL-STACK E2E: PASS
```

---

# Limitations and exclusions

This report does not prove:

```text
Hosted production ENFORCE
Production deployment safety
Cloudflare-only origin access
Direct-origin blocking
Hosted Cloudflare Tunnel topology
Trustworthiness of hosted CF-Connecting-IP
Production WAF source verification
Production Turnstile credentials
```

No hosted ENFORCE or production deployment was performed.

The hosted Cloudflare topology remains a separate deployment acceptance gate.

---

# Evidence checklist

```text
[x] Local protected portal returned HTTP 200
[x] ModSecurity reached the current demo portal upstream
[x] Demo target bridge posted successfully
[x] Controlled source IP identified
[x] LOW recommendation created
[x] LOW challenge observed
[x] LOW grant persisted
[x] LOW refresh under valid grant remained allowed
[x] LOW counter skipped while grant valid
[x] MEDIUM immediate challenge observed
[x] MEDIUM grant persisted
[x] MEDIUM fixed-window counts persisted
[x] MEDIUM throttle page observed
[x] Positive retry countdown observed
[x] Invalid Turnstile failure page captured
[x] Invalid Turnstile created no grant
[x] Invalid Turnstile created no request window
[x] Backend outage failed open
[x] Backend outage created no fake grant
[x] Backend outage created no fake request window
[x] Stack restored healthy
[ ] Hosted Cloudflare topology proof
[ ] Production ENFORCE
```

---

# Recommended repository location

```text
reports/active-enforcement/PR5_CONTROLLED_E2E_PROOF.md
```
