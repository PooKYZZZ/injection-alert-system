# PR7 Block 3C Evidence

Status: **Local runtime contracts verified; disposable resilience E2E NOT_RUN**

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
  `NOTIFICATION_WORKER_REQUIRED=false`) passed: **1032 passed, 59 skipped**.
- Historical Block 3A disposable attack-to-block-to-revoke lifecycle:
  **1 passed in 459.64 seconds** against its original locked portal commit.
  Its finalizer disabled PR7, checked empty state, removed the project, and
  reported no cleanup failure.

## Not executed

The disposable container scenarios for network disconnect/reconnect, outage
past absolute expiry, process killing/recreation, bridge accumulation/replay,
fresh-connection portal restoration timing, and 0/1/64 runtime measurements
are **NOT_RUN** in this evidence record. Therefore no measured revocation SLO,
expiry latency, capacity distribution, or end-to-end resilience completion
claim is made.

The safety contract remains:

```text
Expiry = data-plane safety
Revocation = control-plane safety
```

The backend and bridge use pinned Python 3.11 images. Python 3.14 was tested
as a disposable image candidate and rejected because `torch==2.13.0` had no
compatible distribution; this is recorded rather than silently mixing runtime
contracts.
