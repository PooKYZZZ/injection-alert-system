# PR4 Local Compose Proof — 2026-07-21

This is sanitized local evidence. It contains no API keys, cookies,
authorization headers, database credentials, raw request bodies, or raw source
addresses.

## Tested source pair

- CyberTrace backend: `7587bdf24df58adf534328ff468520bb9932cfef`
- land-records portal PR89: `8e8dabc725d1ea0d171210296f2bfe4569e995ab`
- The portal runtime `Dockerfile` and `.dockerignore` are committed in the
  PR89 branch; the tested image no longer depends on uncommitted portal files.

## Single-stack environment

- Compose root: `G:\AI\PDDDD\injection-alert-system`
- Portal build context: `G:\AI\land-records-portal`
- Project: `injection-alert-system`
- Services: backend, frontend, demo-portal, demo-target-modsecurity,
  demo-target-bridge
- Shadow mode: enabled
- Enforcement timeout used for this local proof: 1000 ms. This is a local proof
  budget, not a production recommendation. The prior 250 ms setting produced
  measured portal degradations in this topology.
- Duplicate `pr4-shadow-enforcement` project: removed; no matching containers
  remain. Volumes were not removed.

## Automated validation

- `docker compose -f docker-compose.yml -f docker-compose.demo-target.yml --profile demo-target config --quiet`: PASS
- Backend targeted PR4 suite with process-only notification-worker overrides: **52 passed, 1 skipped**.
- Portal `npm run typecheck`: PASS
- Portal `npm run lint`: PASS
- Portal `npm run build`: PASS
- `git diff --check`: PASS
- Final rebuilt source pair: backend `7587bdf24df58adf534328ff468520bb9932cfef`,
  portal `8e8dabc725d1ea0d171210296f2bfe4569e995ab`.

The first unmodified local backend test invocation had 2 setup failures in the
SQLite TestClient cases because the ignored `.env` enables the required
PostgreSQL notification worker. The same tests passed with only
`NOTIFICATION_WORKER_ENABLED=false` and `NOTIFICATION_WORKER_REQUIRED=false`
set in the test process.

## Runtime proof

- Healthy no-match: **PASS**. Direct shadow use-case evidence returned
  `matched=false`, `actual_decision=ALLOW` for an isolated source; portal
  `/records/search` returned HTTP 200.
- WAF to recommendation to later match: **PASS**. The maintained
  `run_final_demo_smoke.py --mode demo-target-8089 --require-backend-lookup --json`
  passed with a fresh marker, correlated ModSecurity transaction, HTTP 403 for
  the malicious request, and persisted backend lookup. The later benign
  `/records/search` returned HTTP 200. Direct structured check evidence showed
  `matched=true`, `CRITICAL`, `WAF_BLOCK`, policy
  `confidence-enforcement-v1`, and `actual_decision=ALLOW`.
- Backend unavailable: **PASS**. Backend stopped; portal returned HTTP 200 and
  logged only `TIMEOUT_OR_NETWORK` with `actual_decision=ALLOW`.
- Credential mismatch: **PASS**. Controlled wrong portal credential produced
  backend HTTP 401 behavior; portal returned HTTP 200 and logged only
  `HTTP_ERROR` with `actual_decision=ALLOW`. The valid credential was restored.
- Timeout: **PASS**. Paused backend produced 20 portal HTTP 200 responses;
  degraded samples were bounded at approximately 1019.6 ms p50 and 1022.6 ms
  max, with no retries observed.
- Expiration: **NOT RUN**. The configured minimum TTL is 60 seconds, and the
  live database already contains active recommendations for the shared local
  WAF source. No recommendation rows were deleted or altered to force this
  case.

- Final exact-pair golden-path smoke: **PASS**. Marker
  `CYBERTRACE_SMOKE_20260720T190332_e5db5f83be7d4b63ba4138bbbf3f57f9` produced
  a correlated ModSecurity transaction and backend lookup; the SQLi request
  returned HTTP 403 and the later portal path remained HTTP 200.
- Final exact-pair fail-open smoke: **PASS**. With only the backend stopped, the
  portal returned HTTP 200 in approximately 1142 ms and logged only
  `TIMEOUT_OR_NETWORK` with `actual_decision=ALLOW`; backend health was restored.

The malicious request was blocked by ModSecurity/CRS. The later matching
request produced a shadow recommendation/evaluation; the actual portal
decision remained ALLOW.

## Security checks

- Enforcement credential absent from generated browser assets: PASS
- Enforcement credential absent from backend, portal, and bridge logs: PASS
- Generated browser assets contain neither the internal backend URL nor the
  enforcement endpoint: PASS
- Browser-to-FastAPI direct path: PASS by source/build inspection; the check is
  server-side in the portal route and no enforcement endpoint appears in client
  assets.
- Browser sanity check: **PASS**. The in-app browser opened
  `/records/search?query=browser-sanity`, rendered the search page, and showed
  the expected no-results state. No DevTools credential inspection was needed
  because generated-asset and log scans already covered that boundary.

## Portal latency (end-to-end through `localhost:8089`)

All samples returned HTTP 200. Warmups were performed before measurement.

| mode | samples | p50 ms | p95 ms | p99 ms | max ms |
|---|---:|---:|---:|---:|---:|
| off | 105 | 20.3 | 31.3 | 36.7 | 119.7 |
| shadow healthy | 105 | 319.5 | 332.9 | 482.5 | 510.9 |
| shadow degraded | 20 | 1019.6 | 1022.1 | 1022.1 | 1022.6 |

These are portal end-to-end measurements, not backend-only latency.

## Latency discrepancy resolution

The earlier backend-only evidence of p50 `4.67 ms` and p95 `27.15 ms` came
from a different measurement/runtime and is not comparable to the final
single-stack portal proof. On the final exact-pair stack, 30 authenticated
checks issued from the portal container to `backend:8000` measured p50 `297.1
ms`, p95 `347.2 ms`, p99 `450.8 ms`, and max `474.6 ms`. Thirty complete WAF
portal requests measured p50 `320.0 ms`, p95 `328.4 ms`, p99 `337.4 ms`, and
max `355.4 ms`.

The current evidence therefore attributes most of the observed ~300 ms cost to
the portal-to-backend enforcement path in this local database/runtime topology;
it does not isolate database RTT, connection acquisition, or query execution
individually. Shadow mode does not alter the allow/block outcome, but it does
introduce measurable synchronous request-path latency while enabled. Hosted
shadow enablement remains deferred pending measurement in the target topology.
