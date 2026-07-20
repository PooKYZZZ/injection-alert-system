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
