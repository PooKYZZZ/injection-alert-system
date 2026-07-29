# PR7 Block 2 controlled local WAF runtime evidence

Date: 2026-07-29

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
  every failed or inconclusive post-selection activation. Selected metadata
  is authoritative only after confirmation; lower revisions and equal-revision
  checksum conflicts are ignored/rejected without mutation.
- First boot seeds the persistent selected include before NGINX starts;
  runtime/control configuration uses the fixed snapshot path, a 32-character
  minimum sync key, a loopback-only probe URL, positive finite timeouts, and a
  pinned `httpx==0.28.1` dependency.
- Local-only derived WAF image based on the pinned CRS digest; the original
  `/docker-entrypoint.sh` and ordered bootstrap scripts remain the NGINX child
  bootstrap. Static CRS includes remain independent from the dynamic include.

## Verification

| Check | Result |
| --- | --- |
| New runtime tests | PASS: 35 passed |
| PR7 snapshot/contract plus runtime tests | PASS: 54 passed |
| Existing unit, migration, and script suites | PASS: 796 passed |
| Full repository pytest | NOT_GREEN: 854 passed, 53 skipped, 8 failed, 66 errors; local integration startup is blocked by the required notification worker/PostgreSQL fixture (`OperationalError`) |
| Ruff on runtime/tests | PASS |
| Python compileall | PASS |
| Compose config | PASS |
| Derived image build | PASS: `pr7-waf-review`, pinned CRS digest retained |
| Container config/state-seed smoke | PASS: image imports runtime, validates config, and creates empty `selected.conf` |
| Empty/non-empty candidate through pinned NGINX/ModSecurity/CRS `nginx -t` | NOT_RUN in this remediation pass |
| Container startup with a standalone unresolved backend | NOT_RUN as a success; expected failure because NGINX resolves upstream names at startup |
| Full Docker Compose backend/WAF activation and HTTP source-correlation E2E | NOT_RUN |
| PostgreSQL CI job | NOT_RUN locally |
| Hosted/staging/production enforcement | NOT_RUN and unchanged |

## Safety boundary

The runtime is local-only and disabled by default. No real Supabase data was
changed. No hosted, staging, or production configuration was enabled. PR5,
PR6, ML artifacts, and the existing technical/demo WAF profiles were not
changed. The disposable Docker volumes and test containers used for image
validation were removed after each probe.

The full controlled E2E remains a separate proof obligation: it requires the
repository backend, a healthy snapshot-enabled local environment, a reachable
upstream, and source-correlation fixtures. The fresh local probe is not source-
provenance evidence by itself; the candidate-specific HTTP/source/path,
no-upstream, expiry, revocation, static-CRS, and PR6 regression matrix remains
`NOT_RUN`. This document does not convert pure/runtime or image-build checks
into hosted or production readiness.
