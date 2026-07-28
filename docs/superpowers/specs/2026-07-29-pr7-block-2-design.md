# PR7 Block 2 Controlled Local WAF Runtime Design

**Status:** Approved for implementation on 2026-07-29.

## Goal

Consume the authenticated Block 1 WAF snapshot inside one controlled local
NGINX/ModSecurity container and safely activate deterministic, expiring,
source-bound rules with confirmation and rollback.

## Boundaries

The runtime calls only `GET /api/internal/waf-enforcement/snapshot` with the
configured bearer token. It does not access PostgreSQL, recalculate ML policy,
modify the portal, change PR5/PR6, touch hosted or production configuration,
use Docker socket access, or add infrastructure. Static OWASP CRS rules remain
independent and active in every mode.

## Architecture

The WAF derivative retains the pinned `owasp/modsecurity-crs` bootstrap and
runs a small Python PID-1 supervisor. The supervisor owns foreground NGINX
and one synchronous reconciliation loop. Runtime code is separated into
strict configuration/client and snapshot validation, deterministic rendering,
persistent state, NGINX control/probing, reconciliation/controls, and process
supervision. `/pr7-state` is a named persistent volume containing a permanent
activation lock, canonical empty candidate, immutable candidates, selected and
previous metadata, and a disabled latch.

## Activation sequence

Fetch bytes with bounded streaming and no redirects, parse with duplicate-key
rejection, validate the complete snapshot and Block 1 checksum, render a
deterministic candidate, validate it with the real pinned stack, atomically
select it under the persistent lock, reload NGINX, observe a new worker
generation, and perform fresh-connection content probes. Selected metadata is
written only after confirmation. Any incomplete activation rolls back to the
previous confirmed candidate or canonical empty candidate; unrecoverable
rollback terminates the container nonzero.

## Modes and safety

`OFF` leaves the runtime empty and inactive, `DRY_RUN` validates and measures
without activation, and `ENFORCE` is local-only and remains disabled by the
persistent `DISABLED` latch until an explicit local enable control. Runtime
IPv6 enforcement is rejected as a whole snapshot; only canonical IPv4 entries
are rendered. Rules use the fixed `/records/search` path, exact source match,
generic 403 responses, deterministic IDs `10000` through `10511`, and absolute
expiry. Static CRS positive controls must continue to work.

## Verification

Tests are written first for parser/client, checksum and renderer behavior,
state atomicity, NGINX control and rollback, reconciliation, supervision,
and controlled local Docker/Compose behavior. Results are classified as
PASS, FAIL, or NOT_RUN; local proof is not presented as hosted or production
readiness. The final local state is latched disabled and empty.
