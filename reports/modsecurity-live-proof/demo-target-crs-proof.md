# Demo-target CRS/WAF Evidence Report

## Purpose

Record observed local-only ModSecurity/OWASP CRS behavior for the separate land-records portal demo target through the optional WAF path.

This report is evidence for the demo-target WAF route only. It is not a full penetration test, not scanner/fuzzer coverage, and not a production deployment claim.

## Environment

| Item | Observed Value |
| --- | --- |
| Date/time | `2026-06-24 18:58:48 +08:00` |
| Git commit | `08d79ed` |
| Portal direct path | `http://localhost:3010` |
| WAF path | `http://localhost:8089` |
| WAF upstream | `host.docker.internal:3010` |
| Audit log | `logs/modsecurity/demo-target/modsec_audit.jsonl` |
| Audit mode | `RelevantOnly` from `docker-compose.demo-target.yml` |
| CRS paranoia level | `PL1` from `PARANOIA=1` and observed `paranoia-level/1` audit tags |
| WAF container | `injection-alert-system-demo-target-modsecurity-1` |

Research sources checked before the local proof:

- OWASP WSTG SQL Injection testing guidance.
- OWASP WSTG reflected and stored XSS testing guidance.
- OWASP CRS paranoia-level and false-positive tuning guidance.
- Official OWASP CRS Docker image reverse-proxy guidance for `BACKEND`.
- Community false-positive tuning discussion from Netnea/Christian Folini.

## Preflight

| Check | Observed Result | Verdict |
| --- | --- | --- |
| Portal direct path `http://localhost:3010/` | HTTP `200`, response length `106450` | PASS |
| WAF path `http://localhost:8089/` | HTTP `200`, response length `106450` | PASS |
| `demo-target-modsecurity` container | `Up 11 minutes (healthy)` | PASS |
| WAF port publish | `0.0.0.0:8089->8080/tcp`, `[::]:8089->8080/tcp` | PASS |
| Audit log path | `logs/modsecurity/demo-target/modsec_audit.jsonl` exists | PASS |

## Summary Table

| Test | Method | Request | HTTP | Audit Event | Transaction ID | CRS Rule IDs | Verdict |
| --- | --- | --- | --- | --- | --- | --- | --- |
| home-page | GET | `/?ctprobe=portal-proof-20260624-185832-home-page` | `200` | `N/A` | `N/A` | `N/A` | RECORDED |
| normal-search | GET | `/records/search?query=Pasig&ctprobe=portal-proof-20260624-185832-normal-search` | `200` | `N/A` | `N/A` | `N/A` | RECORDED |
| record-detail | GET | `/records/LND-2026-0001?ctprobe=portal-proof-20260624-185832-record-detail` | `200` | `N/A` | `N/A` | `N/A` | RECORDED |
| normal-transaction-status | GET | `/transactions/status?ref=SUP-2026-0001&ctprobe=portal-proof-20260624-185832-normal-transaction-status` | `200` | `N/A` | `N/A` | `N/A` | RECORDED |
| sqli-search | GET | `/records/search?query=...&ctprobe=portal-proof-20260624-185832-sqli-search` | `403` | Yes | `178229871889.955563` | `942100; 942190; 942360; 949110` | RECORDED |
| xss-status-ref | GET | `/transactions/status?ref=...&ctprobe=portal-proof-20260624-185832-xss-status-ref` | `403` | Yes | `17822987197.130806` | `941100; 941110; 941160; 949110` | RECORDED |
| xss-comments-post | POST | `/comments/submit?ctprobe=portal-proof-20260624-185832-xss-comments-post` | `403` | Yes | `178229871982.443098` | `941100; 941120; 941160; 949110` | RECORDED |
| sqli-login-post | POST | `/login/submit?ctprobe=portal-proof-20260624-185832-sqli-login-post` | `403` | Yes | `178229872018.564891` | `942100; 949110` | RECORDED |

## Detailed Observed Evidence

### home-page

- Marker: `portal-proof-20260624-185832-home-page`
- Request: `GET /?ctprobe=portal-proof-20260624-185832-home-page`
- HTTP status: `200`
- Audit event: `N/A`
- Note: No relevant audit event was expected for normal HTTP 200 traffic while audit mode is `RelevantOnly`.

### normal-search

- Marker: `portal-proof-20260624-185832-normal-search`
- Request: `GET /records/search?query=Pasig&ctprobe=portal-proof-20260624-185832-normal-search`
- HTTP status: `200`
- Audit event: `N/A`
- Note: No relevant audit event was expected for normal HTTP 200 traffic while audit mode is `RelevantOnly`.

### record-detail

- Marker: `portal-proof-20260624-185832-record-detail`
- Request: `GET /records/LND-2026-0001?ctprobe=portal-proof-20260624-185832-record-detail`
- HTTP status: `200`
- Audit event: `N/A`
- Note: No relevant audit event was expected for normal HTTP 200 traffic while audit mode is `RelevantOnly`.

### normal-transaction-status

- Marker: `portal-proof-20260624-185832-normal-transaction-status`
- Request: `GET /transactions/status?ref=SUP-2026-0001&ctprobe=portal-proof-20260624-185832-normal-transaction-status`
- HTTP status: `200`
- Audit event: `N/A`
- Note: No relevant audit event was expected for normal HTTP 200 traffic while audit mode is `RelevantOnly`.

### sqli-search

- Marker: `portal-proof-20260624-185832-sqli-search`
- Request: `GET /records/search?query=<controlled SQLi check>&ctprobe=portal-proof-20260624-185832-sqli-search`
- HTTP status: `403`
- Audit event: Yes
- transaction_id: `178229871889.955563`
- source_ip: `172.21.0.1`
- request_uri: `/records/search?query=%27%20UNION%20SELECT%20null,null,null--%20&ctprobe=portal-proof-20260624-185832-sqli-search`
- audit response status: `403`
- CRS rule IDs: `942100; 942190; 942360; 949110`
- Matched messages: SQL injection via libinjection; MSSQL code execution/information gathering; concatenated basic SQL injection/SQLLFI; inbound anomaly score exceeded.
- Relevant tags: `attack-sqli`, `paranoia-level/1`, `OWASP_CRS`, `attack-generic`

### xss-status-ref

- Marker: `portal-proof-20260624-185832-xss-status-ref`
- Request: `GET /transactions/status?ref=<controlled XSS check>&ctprobe=portal-proof-20260624-185832-xss-status-ref`
- HTTP status: `403`
- Audit event: Yes
- transaction_id: `17822987197.130806`
- source_ip: `172.21.0.1`
- request_uri: `/transactions/status?ref=%3Cscript%3Ealert%281%29%3C%2Fscript%3E&ctprobe=portal-proof-20260624-185832-xss-status-ref`
- audit response status: `403`
- CRS rule IDs: `941100; 941110; 941160; 949110`
- Matched messages: XSS via libinjection; script tag vector; HTML injection; inbound anomaly score exceeded.
- Relevant tags: `attack-xss`, `paranoia-level/1`, `OWASP_CRS`, `attack-generic`

### xss-comments-post

- Marker: `portal-proof-20260624-185832-xss-comments-post`
- Request: `POST /comments/submit?ctprobe=portal-proof-20260624-185832-xss-comments-post`
- Controlled payload summary: form-encoded display name contained an image event-handler XSS check; message was `ComplianceTest`.
- HTTP status: `403`
- Audit event: Yes
- transaction_id: `178229871982.443098`
- source_ip: `172.21.0.1`
- request_uri: `/comments/submit?ctprobe=portal-proof-20260624-185832-xss-comments-post`
- audit response status: `403`
- CRS rule IDs: `941100; 941120; 941160; 949110`
- Matched messages: XSS via libinjection; event handler vector; HTML injection; inbound anomaly score exceeded.
- Relevant tags: `attack-xss`, `paranoia-level/1`, `OWASP_CRS`, `attack-generic`

### sqli-login-post

- Marker: `portal-proof-20260624-185832-sqli-login-post`
- Request: `POST /login/submit?ctprobe=portal-proof-20260624-185832-sqli-login-post`
- Controlled payload summary: form-encoded password contained a basic boolean SQLi check.
- HTTP status: `403`
- Audit event: Yes
- transaction_id: `178229872018.564891`
- source_ip: `172.21.0.1`
- request_uri: `/login/submit?ctprobe=portal-proof-20260624-185832-sqli-login-post`
- audit response status: `403`
- CRS rule IDs: `942100; 949110`
- Matched messages: SQL injection via libinjection; inbound anomaly score exceeded.
- Relevant tags: `attack-sqli`, `paranoia-level/1`, `OWASP_CRS`, `attack-generic`

## Findings

- The optional WAF route `localhost:8089 -> ModSecurity/OWASP CRS -> host.docker.internal:3010` was reachable.
- Normal portal pages and lookups returned HTTP `200`.
- Normal HTTP `200` traffic did not produce audit events under `RelevantOnly`, which is expected behavior for this configuration.
- Controlled SQLi-looking and XSS-looking requests were blocked by ModSecurity/OWASP CRS with HTTP `403`.
- Audit events for blocked requests included transaction IDs, request URIs, response statuses, CRS rule IDs, messages, and CRS tags.
- Observed CRS rule IDs were `941100`, `941110`, `941120`, `941160`, `942100`, `942190`, `942360`, and `949110`.

## Interpretation

ModSecurity/OWASP CRS is the blocking and detection layer in this proof.

This proof is separate from ML triage and dashboard proof. It does not show that the ML model blocked these requests, and it does not depend on dashboard evidence.

The report proves observed behavior only for this local run and this small controlled request set. It does not prove full WAF coverage and does not claim production protection.

## Limitations

- Local demo-only proof.
- Small controlled test set.
- Not a full penetration test.
- Not scanner or fuzzer coverage.
- Does not prove all SQLi or XSS payloads are blocked.
- POST requests may write demo rows if they reach the app; in this run the controlled POST checks returned HTTP `403`.
- CRS false positives and tuning still require real application traffic review.
- No production SIEM or Wazuh claim.
- No full WAF coverage claim.
- No production deployment claim.

## Result

PASS: The local portal demo-target WAF path produced observed evidence for normal traffic and controlled CRS checks. Blocked CRS checks included HTTP `403`, transaction IDs, CRS rule IDs, matched messages, and relevant tags where audit events existed.
