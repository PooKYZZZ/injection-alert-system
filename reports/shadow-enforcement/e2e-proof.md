# PR4 Final E2E Proof

Final reproducible source pair:

- Backend: `7587bdf24df58adf534328ff468520bb9932cfef`
- Portal PR89: `8e8dabc725d1ea0d171210296f2bfe4569e995ab`

The final single Compose project was rooted at
`G:\AI\PDDDD\injection-alert-system` and built the portal from
`G:\AI\land-records-portal`. The bridge services receive only WAF-specific
configuration; the enforcement credential is passed only to backend and portal
server environments.

Final checks:

- Compose config: PASS
- Backend focused PR4 tests: `52 passed, 1 skipped`
- Portal enforcement tests, typecheck, lint, build: PASS
- WAF/CRS → audit → bridge → ingest → ML → TrafficLog → recommendation smoke:
  PASS
- Final backend-unavailable fail-open smoke: PASS; portal HTTP 200 and safe
  degraded log
- Browser `/records/search` sanity check: PASS
- Credential absent from browser assets and logs: PASS
- Duplicate temporary Compose project: removed

The final WAF smoke used marker
`CYBERTRACE_SMOKE_20260720T190332_e5db5f83be7d4b63ba4138bbbf3f57f9` and
correlated transaction `178457421221.555243`. The malicious request was blocked
by ModSecurity/CRS. A later benign request matched the shadow recommendation,
while the actual portal decision remained `ALLOW` and the portal returned HTTP
200.

Final latency evidence is documented in
`reports/shadow-enforcement/local-compose-proof-2026-07-21.md`: shadow healthy
portal p50 was `320.0 ms` versus `20.3 ms` with enforcement off; the direct
portal-container-to-backend check was `297.1 ms` p50. The earlier `4.67 ms`
backend-only result came from a different measurement/runtime and is not
comparable. Hosted shadow enablement remains deferred pending target-topology
measurement. Live expiration was not destructively forced; automated expiry,
stale replay, retry repair, and expired-lookup tests remain the authoritative
coverage for those semantics.

## Post-merge manual runtime validation — 2026-07-21

This section records fresh validation performed after PR #88 and PR #89 were
merged. It supplements the exact tested source-pair evidence above; it does not
replace it.

Merged source state:

- Backend PR #88 merge: `ad170c36462eb12293a268a9a049c6fd2188f933`
- Portal PR #89 merge: `bdeef868a8a3d9e56f9593f3b3f776cff165c26a`
- Backend `master` and `origin/master` were synchronized during validation.
- Portal `stable/portal-pre-waf` was synchronized with origin during validation.

The single Compose project rendered and built successfully from the normal
CyberTrace root, using the sibling portal repository as the demo-target build
context. The expected backend, frontend, portal, ModSecurity, and bridge
services were running under project `injection-alert-system`. A transient
startup report that the backend was unhealthy cleared without a rebuild; the
backend subsequently remained healthy and returned HTTP 200 from `/health`.
This is retained as a non-blocking startup/readiness follow-up, not a PR4
functional failure.

The maintained command below passed:

```powershell
.venv\Scripts\python.exe scripts\run_final_demo_smoke.py --mode demo-target-8089 --require-backend-lookup --json
```

Fresh post-merge result:

- Marker: `CYBERTRACE_SMOKE_20260721T075259_9257a1df24d04592901678ed78e78e5e`
- Transaction: `178462037951.608611`
- Demo portal home: HTTP 200
- Controlled SQLi: ModSecurity/CRS HTTP 403
- Audit transaction correlation: PASS
- Backend transaction lookup: PASS

A later benign `/records/search` request returned HTTP 200 and the portal
called the server-side internal enforcement check successfully. Direct
execution of the production repository/use-case code against the running
PostgreSQL state produced this sanitized healthy-path result:

```text
matched=True
tier=CRITICAL
recommended_action=WAF_BLOCK
policy_version=confidence-enforcement-v1
actual_decision=ALLOW
degraded=False
```

The recommendation is hypothetical shadow intent. The original malicious
request was blocked independently by ModSecurity/CRS; CyberTrace did not
retroactively block it. Source correlation in this local Docker topology is
observational and does not establish attacker identity.

For fail-open validation, the backend was stopped without rebuilding the
stack. The portal remained available and returned HTTP 200, while logging the
sanitized `TIMEOUT_OR_NETWORK` degraded reason with `actual_decision=ALLOW`.
The degraded path took approximately one second under the local proof timeout.
After backend restart, health returned to HTTP 200 and a recovered portal
request returned HTTP 200. A second post-recovery full smoke also passed:

- Marker: `CYBERTRACE_SMOKE_20260721T083558_1c8178bfd57f49fa81900dc33d1eaeb4`
- Demo home: HTTP 200
- Controlled SQLi: HTTP 403
- Audit and backend correlation: PASS

The successful shadow-check structured log was not visible in the attempted
container-stdout search, although the endpoint response and direct use-case
evaluation verified the behavior. The degraded structured event was visible.
This remains a non-blocking observability follow-up and is not described as a
functional defect.

PR4 therefore remains **MERGED, POST-MERGE RUNTIME VALIDATED, and FROZEN**.
PR5 — LOW/MEDIUM End-to-End Enforcement is the next planned implementation
phase. Hosted shadow enablement remains deferred until target-topology latency
and source-trust evidence are measured.
