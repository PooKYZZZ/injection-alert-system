# PR7 Block 2 controlled local WAF runtime evidence

Date: 2026-07-29
Head commit: 1a17241

## Implemented

- Strict synchronous snapshot client with fixed HTTP origin, bearer auth,
  no redirects, `trust_env=False`, identity encoding, bounded streaming,
  content-type/UTF-8 checks, duplicate-key rejection, strict schema checks,
  IPv4-only whole-snapshot policy, and exact Block 1 checksum compatibility.
- Deterministic ModSecurity candidate renderer with canonical ordering,
  IDs `10000`–`10511`, exact `/records/search`, source matching, absolute
  expiry, generic 403 action, and candidate SHA-256.
- Persistent `/pr7-state` store with permanent activation lock, atomic files,
  selected/previous/canonical-empty candidates, metadata, disabled latch, and
  bounded pruning.
- Synchronous reconciliation, OFF/DRY_RUN/ENFORCE mode semantics, disable /
  enable / status control, redacted JSON events, and minimal PID-1
  supervision.
- Candidate activation now validates the actual selected include with the
  pinned NGINX configuration, confirms a new worker generation, performs a
  fresh local HTTP probe, and reloads/probes the previous confirmed state on
  every failed or inconclusive post-selection activation. Authoritative empty
  snapshots revoke the previous candidate through the same reload/probe path;
  two-level rollback falls back to canonical empty and fails closed if neither
  state can be confirmed. Selected metadata is authoritative only after
  confirmation; lower revisions and equal-revision checksum conflicts are
  ignored/rejected without mutation.
- First boot forces canonical empty before NGINX starts, validates the complete
  generated configuration, waits for a ready worker generation, and only then
  starts synchronization. SIGQUIT is forwarded to NGINX while the sync child
  receives SIGTERM.
- The loopback-only probe listener trusts its dedicated source header only from
  loopback, proves matching source/path PR7 blocking with a tagged ModSecurity
  audit record, proves wrong source/path 204 responses, and checks a separate
  normal-listener CRS block. Empty probes require exactly HTTP 204.
- First boot seeds the persistent selected include before NGINX starts;
  runtime/control configuration uses the fixed snapshot path, a 32-character
  minimum sync key, a loopback-only probe URL, positive finite timeouts, and a
  pinned direct `httpx==0.28.1` runtime dependency; the pinned base image
  supplies the remaining OS/runtime layers.
- OFF, disable, and authoritative-empty transitions use empty-only recovery:
  they retry canonical empty and raise a fatal rollback error if empty cannot
  be confirmed. Normal non-empty activation retains the previous-then-empty
  rollback hierarchy.
- Candidate probes require the exact revision and recommendation tags, choose
  the latest sufficiently unexpired item as the representative, and retry a
  fresh positive request while graceful-reload workers drain. The CRS control
  also requires `attack-sqli` or rule `942100` audit metadata.
- The PR7 Compose profile starts after the backend container starts rather than
  requiring backend health, allowing startup-empty/degraded recovery proof.
- Local-only derived WAF image based on the pinned CRS digest; the original
  `/docker-entrypoint.sh` and ordered bootstrap scripts remain the NGINX child
  bootstrap. Static CRS includes remain independent from the dynamic include.

## Verification

| Check | Result |
| --- | --- |
| New runtime tests | PASS: 50 passed locally |
| PR7 snapshot/contract plus runtime tests | PASS remotely in GitHub CI |
| Existing unit, migration, and script suites | PASS: 796 passed |
| Full repository pytest | NOT_GREEN: 854 passed, 53 skipped, 8 failed, 66 errors; local integration startup is blocked by the required notification worker/PostgreSQL fixture (`OperationalError`) |
| Ruff on runtime/tests | PASS |
| Python compileall | PASS |
| Compose config | PASS |
| Derived image build | PASS: `pr7-waf-review`, pinned CRS digest retained |
| Container config/state-seed smoke | PASS: image imports runtime, validates config, and creates empty `selected.conf` |
| Controlled pinned-image activation | PASS: matching source/path 403 plus PR7-tagged audit record; wrong source/path 204; separate CRS probe 403 |
| Authoritative empty revocation | PASS: revision 11 selected canonical empty and matching source/path returned 204 |
| Safe restart in OFF mode | PASS: persisted active state was forced to `mode_empty` before synchronization and returned 204 |
| Maximum-size matrix | PASS: final pinned image validated 0, 1, 64, 128, and 512 candidates; representative first/middle/last rules returned 403 |
| Docker WAF CI coverage | PASS remotely: `.github/workflows/ci.yml` builds the pinned image and runs the bounded smoke matrix |
| Container startup with an unavailable backend | PASS: disposable WAF container started against loopback port 9, remained startup-empty, and later OFF restart remained empty |
| Full Docker Compose backend/WAF activation and HTTP source-correlation E2E | NOT_RUN: external source provenance remains Block 3 |
| GitHub CI overall | PASS: backend, PostgreSQL, migrations, frontend, authentication E2E, secret scan, and PR7 WAF runtime |
| PostgreSQL CI job | PASS remotely; the local environment was not used as the PostgreSQL proof |
| Hosted/staging/production enforcement | NOT_RUN and unchanged |

## Safety boundary

The runtime is local-only and disabled by default. No real Supabase data was
changed. No hosted, staging, or production configuration was enabled. PR5,
PR6, ML artifacts, and the existing technical/demo WAF profiles were not
changed. The disposable Docker volumes and test containers used for image
validation were removed after each probe.

The controlled proof above is disposable loopback/image evidence, not source-
provenance evidence from the repository backend. Full Compose backend/source-
correlation, and PR6 regression matrices remain separate proof obligations.
This document does not convert local runtime or image-build checks into hosted
or production readiness.
