# PR7 Block 3C Evidence

Status: **Materially verified for the approved controlled local resilience scope; exhaustive fault matrix deferred**

## Implemented and verified

- `docker-compose.pr7-block3c.yml` provides a deterministic local profile with
  persistent WAF state/audit volumes and portal sentinel evidence.
- Portal evidence writing and parsing are schema-exact and bounded to 256 KiB;
  the writer serializes concurrent appends and rejects invalid IDs, stages,
  methods, paths, and extra fields without affecting enforcement; size-limit
  warnings are coalesced per path.
- WAF reconcile events now include monotonic `total_ms` for success, rejection,
  activation failure, and rollback failure without logging response bodies or
  credentials.
- A deterministic local fault server covers authorization, server errors,
  redirects, content-type/schema/body faults, and bounded timeouts. Compose
  controls cover stop/start/recreate/kill and network disconnect/reconnect;
  finalizers verify the disable latch and empty selected state before teardown.
- Existing focused tests verify stale revision rejection, same-revision
  checksum conflict, safe-empty startup, disable latch persistence, snapshot
  validation/body/time limits, candidate failure, rollback, rollback failure,
  NGINX probing, and supervisor child failure.
- Existing PostgreSQL tests cover expiry cleanup, revocation with expired rows,
  revision stamping, capacity, and no-resurrection state transitions.
- The WAF worker now preserves bounded `total_ms` reconciliation timings in its
  JSON event allowlist.
- The guarded disposable expiry scenario uses a short test-only recommendation
  TTL, disconnects the backend, proves a matching request is blocked before
  expiry, proves a fresh request reaches the portal after absolute expiry, and
  proves static CRS still returns 403 during the outage.
- Candidate-render capacity measurements for 0, 1, and 64 entries are stored in
  `artifacts/pr7-block3/capacity-20260731.json` (ignored disposable output).
- Automated real disposable lifecycle run `pr7-auto-3c-20260731d` completed
  with **4 passed, 1 skipped in 197.33 seconds**. It used a 60-second
  test-only recommendation TTL and a 600-second bounded startup deadline,
  activated real WAF state, exercised backend disconnect/absolute expiry/static
  CRS continuity/revocation, and completed disabled-empty cleanup with no
  remaining project resources. Timing events are in the ignored artifact
  `artifacts/pr7-block3/pr7-auto-3c-20260731d/waf-timings-pr7-block3-1770e99b.json`.
  The run used actual PostgreSQL, backend, portal, WAF, bridge, source-client,
  and real-model services at head
  `512e4387716dd16b43267adb38098e810b98f581`.

## Verification

- Portal sentinel unit suite: 38 passed.
- Shared sentinel/Compose tests: 16 passed.
- WAF runtime, enforcement, bridge, artifact, fault-control, and evidence
  selections pass; guarded external and disposable E2E remain explicitly
  skipped unless opted in.
- Both merged Compose profiles validated with `config --quiet`.
- Full repository pytest initially fails under the local `.env` because it
  enables a required notification worker while SQLite lacks
  `public.claim_notification_outbox_batch_v62`. Re-running with the test
  worker explicitly disabled (`NOTIFICATION_WORKER_ENABLED=false`,
  `NOTIFICATION_WORKER_REQUIRED=false`) passed: **1043 passed, 60 skipped**.
- Historical Block 3A disposable attack-to-block-to-revoke lifecycle:
  **1 passed in 459.64 seconds** against its original locked portal commit.
  Its finalizer disabled PR7, checked empty state, removed the project, and
  reported no cleanup failure.
- Current Block 3 lifecycle regression: **4 passed in 432.26 seconds**.
- Automated current disposable lifecycle: **4 passed, 1 skipped in 197.33
  seconds** with the short-TTL expiry-outage branch enabled.
- Exact skipped test:
  `test_dynamic_rule_expires_while_backend_remains_unavailable` —
  `set PR7_RUN_BLOCK3_EXPIRY_E2E=1 to run expiry during backend outage`.
  This separately guarded wrapper was not represented as passed. The successful
  main lifecycle exercised its short-TTL backend-outage expiry branch through
  `PR7_RUN_BLOCK3_EXPIRY_OUTAGE=1`.
- Verified observable behavior included CRITICAL activation, dynamic WAF
  blocking, backend synchronization outage, absolute expiry while the backend
  was unavailable, portal restoration after expiry, static CRS continuity,
  revocation, representative snapshot rejection behavior, disabled-empty final
  state, and project-scoped cleanup. No disposable containers, networks, or
  volumes remained.
- Current absolute-expiry/backend-outage scenario: **1 passed in 235.20
  seconds**. The run finished with the disable latch and cleanup finalizer.
- Candidate-render capacity run: **10 samples each at 0/1/64 entries**; the
  generated artifact records min/median/p95/max timings and candidate sizes.

## Deferred, non-blocking evidence

The following additional depth was not required for this PR closure and is not
represented as executed:

- A separate reconnect-before-expiry timing run with a recorded propagation
  latency.
- Bridge container kill/recreate with replay evidence captured as a committed
  machine-readable bundle.
- Every NGINX/process-failure variant while non-empty state is selected.
- Persistent non-empty state-volume recreation proof separate from the empty
  startup checks.
- Full runtime activation/reload/probe capacity distributions; the current
  committed measurement covers candidate rendering, while WAF reconcile logs
  now expose `total_ms` for future runtime sampling.
- A final committed timing bundle containing snapshot fetch, validation, reload,
  probe, revocation propagation, expiry-to-allow, and restart recovery fields.

Section 3C is materially verified for the approved controlled local resilience
scope. The real disposable lifecycle demonstrated bounded startup, CRITICAL
activation, WAF enforcement, control-plane outage, data-plane expiry, portal
recovery, static CRS continuity, revocation, snapshot rejection, and safe
cleanup. The explicitly skipped scenario remains documented and is not
represented as passed. The additional exhaustive process-failure and timing
matrix remains deferred and is not claimed as executed.

The safety contract remains:

```text
Expiry = data-plane safety
Revocation = control-plane safety
```

The backend and bridge currently use pinned Python 3.14 images recorded in the
PR7 artifact lock files. The project metadata, Dockerfiles, and GitHub Actions
Python jobs target one Python 3.14 runtime contract.
