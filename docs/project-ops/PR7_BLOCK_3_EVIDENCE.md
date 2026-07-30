# PR7 Block 3 Controlled-Local Evidence

**Status:** Controlled-local attack-to-CRITICAL-WAF lifecycle passed; hosted,
staging, production, and real Cloudflare ingress remain unverified.

**Run date:** 2026-07-30
**Repository:** `G:\AI\PDDDD\injection-alert-system`
**Profile:** disposable PostgreSQL, FastAPI, pinned DistilBERT staging artifact,
local ModSecurity/OWASP CRS WAF, JSONL bridge, and isolated demo portal.

## Result

The guarded lifecycle test passed:

```text
PR7_RUN_BLOCK3_E2E=1 .venv\Scripts\python.exe -m pytest -q --tb=short tests/e2e/test_pr7_block3.py
3 passed in 144.74s
```

The test drove a fixed source client through the WAF with the SQLi vector
`/records/search?id=1%20OR%201=1--`. The audit event was followed from the
shared JSONL volume into `POST /api/internal/waf-events`, triaged by the real
model, and persisted as a verified `SQL Injection` / `CRITICAL` completed alert.
The post-triage coordinator selected the PR7 writer exactly once, and the
Block 1 repository produced an expiring `WAF_BLOCK` effective-state entry and
revision. The Block 2 runtime consumed the authenticated snapshot, activated
the candidate, and returned HTTP 403 for the matching source/path.

The same lifecycle asserted:

- a different fixed source was not blocked;
- `/records/search/` did not match the exact protected path;
- wrong-source, wrong-path, and post-revocation controls returned their exact
  pre-activation baseline status and had non-empty upstream evidence;
- one bounded audit-log transaction contained the external marker, PR7 tag,
  revision, and recommendation correlation;
- the WAF evidence access log recorded HTTP 403 with empty upstream fields for
  the matching request; and
- direct Block 1 revocation removed the active snapshot entry and restored a
  non-blocked request.

## Implementation boundary

- `PostTriageEnforcementCoordinator` owns the single-writer decision after
  alert persistence. Eligible PR7 candidates use the atomic Block 1 repository;
  all other alerts retain the generic recommendation path.
- `PR7_CRITICAL_WAF_MUTATION_ENABLED` defaults to `false` and is accepted only
  for development/testing with WAF snapshot sync enabled,
  `ENFORCEMENT_MODE=enforce`, `cloudflare_tunnel` source verification, and a
  PostgreSQL database.
- The PR7 mutation uses a fresh async database session so the preceding
  triage reload cannot leave an implicit read transaction around the Block 1
  `READ COMMITTED` mutation boundary.
- The controlled bridge skips opt-in Block 2 controller probes. Those probes
  traverse the WAF for activation safety, but forwarding their shared audit
  records would recursively create recommendations. The filter is enabled
  only by `docker-compose.pr7-block3.yml`.
- The bridge follows with `--from-start`; transaction-idempotent ingest permits
  safe replay after a restart instead of silently dropping lines written while
  the bridge was unavailable.
- PR7 state mutation rejects pure IPv6 sources until the runtime snapshot
  contract supports IPv6 entries; IPv4-mapped IPv6 values remain canonicalized
  to IPv4.
- The evidence access log is a WAF-side no-upstream assertion. It does not
  replace a portal-side request sentinel or prove that a deployed portal could
  not be reached through another route.

## Model evidence

The exact vector is separately covered by the guarded real-model test:

```text
PR7_RUN_REAL_MODEL=1 .venv\Scripts\python.exe -m pytest -q --tb=short tests/ml/test_pr7_critical_vector.py
1 passed in 8.49s
```

The pinned artifact is
`ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755`,
with checkpoint SHA-256
`8f43f4e85a4c728ea24aff7c1d0e453661f1257252cd62845bd5051120eb21a2`.
The observed vector confidence was `0.998841` and the configured CRITICAL
threshold was `0.90`. This proves vector selection and model output only; the
full lifecycle result above is the authoritative attack-to-WAF evidence.
The machine-readable lock also verifies the manifest, tokenizer, model
configuration, pinned PostgreSQL/Python/WAF inputs, and the exact clean portal
checkout before the lifecycle starts. The model weights remain an external,
secure artifact dependency and are not committed to Git.

## Earlier failed attempts retained for review

- The first disposable run raced PostgreSQL initialization during Alembic
  startup. The compose override now waits with a synchronous `psycopg` probe
  before running migrations.
- The first readiness-loop repair used `asyncio.run()` for connect and close,
  which caused an asyncpg cross-event-loop error. It was replaced with a
  same-process synchronous readiness probe.
- The first route integration attempt reused the triage session and failed
  with SQLAlchemy `InvalidRequestError` because the triage reload had opened an
  implicit transaction. The fresh-session dependency fixed that boundary.
- The first harness client probe used invalid multiline Python after Docker
  Compose argument normalization. It was replaced with a single-line HTTP
  error-preserving opener.
- The first complete lifecycle admitted Block 2 probe audit records into the
  bridge, creating extra loopback recommendations. The opt-in internal-probe
  filter fixed the shared-volume recursion, and the final lifecycle passed.
- The lifecycle preflight now fails before Compose startup when the locked model
  hashes, portal commit, clean portal checkout, or disposable image references
  do not match `pr7-block3-artifact-lock.json`.
- The first hardened rerun raced WAF startup. An exact readiness gate was
  added. A subsequent host-side readiness request polluted the audit lifecycle,
  so readiness now uses the dedicated loopback probe from inside the WAF
  container and asserts HTTP 204 without entering external ingest.
- An intermediate readiness request negotiated compressed response content;
  binary response bytes caused the UTF-8 audit follower to exit. The final
  lifecycle avoids that path entirely by using the no-upstream internal probe.
- An intermediate async state poll disposed its engine on a different event
  loop. Engine creation, reusable session-factory polling, and disposal now run
  on one event loop.
- After enabling bridge replay, one local rerun exceeded the 300-second Compose
  startup budget while PostgreSQL initialization and migrations were still
  running; cleanup also reported that the WAF was not ready for disable. The
  harness startup budget is now 420 seconds, and this failed attempt remains
  uncounted as lifecycle evidence.

## Completion classification

**Fully implemented for controlled local scope:** attack → CRS audit JSONL →
bridge → real ML triage → verified CRITICAL → atomic PR7 state → authenticated
snapshot → Block 2 WAF 403 → source/path isolation → evidence correlation →
revocation.

**Partially completed:** trusted source provenance is represented by fixed
Docker source clients and the existing Cloudflare-provenance contract; no real
Cloudflare tunnel, target isolation, or hosted ingress was exercised in this
run. Portal no-upstream is evidenced at the WAF boundary, but no portal-side
sentinel was added. PR6 application-block behavior was not enabled in this
WAF-only disposable profile.

**Not completed:** hosted/staging/production ENFORCE, real Cloudflare source
equivalence, production rollout approval, and a claim of production readiness.

**Follow-up:** run the separately authorized Cloudflare/origin trust proof,
add a portal-owned no-upstream sentinel if stronger evidence is required, and
execute a combined PR6/PR7 portal profile before considering any hosted rollout.
