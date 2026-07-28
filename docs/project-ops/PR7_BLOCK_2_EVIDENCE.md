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
- Local-only derived WAF image based on the pinned CRS digest; the original
  `/docker-entrypoint.sh` and ordered bootstrap scripts remain the NGINX child
  bootstrap. Static CRS includes remain independent from the dynamic include.

## Verification

| Check | Result |
| --- | --- |
| New runtime tests | PASS: 23 passed |
| Existing unit + migration suites | PASS: 684 passed |
| Ruff on runtime/tests | PASS |
| Python compileall | PASS |
| Compose config | PASS |
| Derived image build | PASS |
| Empty candidate through pinned NGINX/ModSecurity/CRS `nginx -t` | PASS |
| Non-empty generated candidate through pinned stack `nginx -t` | PASS |
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
upstream, and source-correlation fixtures. This document does not convert
the pure/runtime or pinned syntax checks into hosted or production readiness.
