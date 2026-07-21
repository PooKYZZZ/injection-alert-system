# PR5 Active LOW/MEDIUM Enforcement Design

**Status:** Approved for implementation on 2026-07-21

## Goal

Extend PR4's durable shadow recommendation path into a controlled, local/test-only active enforcement slice for `/records/search`. PR4 `SHADOW` rows and their fail-open `ALLOW` behavior remain unchanged; hosted and production `ENFORCE` remain disabled by default.

## Architecture

Completed WAF/ML events continue to create durable recommendations in `enforcement_recommendations`. In `ENFORCE`, only explicit `ENFORCE` rows using `confidence-enforcement-v2` and a trusted/explicitly test-enabled source are eligible for a single backend evaluator. The evaluator owns LOW/MEDIUM fixed-window counters and tier-bound challenge grants in PostgreSQL and returns `ALLOW`, `CHALLENGE`, or `THROTTLE` to the existing server-only portal boundary.

The portal remains responsible for deriving the visitor source, calling the backend with its server credential, rendering challenge/throttle state, and submitting a Turnstile token through a same-origin server route. CyberTrace remains authoritative for Siteverify, recommendation re-checking, grant persistence, and final policy decisions. No browser request reaches FastAPI directly.

## Policy

- `OFF`: no recommendation recording or enforcement state changes.
- `SHADOW`: historical PR4 `confidence-enforcement-v1` recommendations remain non-disruptive and return `ALLOW`.
- `ENFORCE`: new recommendations use `confidence-enforcement-v2`; only LOW and MEDIUM are active.
- LOW: fixed 60-second window; counts 1-5 allow, count 6+ challenges; a valid LOW grant allows without incrementing the LOW counter.
- MEDIUM: no grant challenges immediately; a valid MEDIUM grant allows counts 1-10 per 60-second window and throttles count 11+ with authoritative `retry_after_seconds`.
- HIGH and CRITICAL remain non-disruptive and cannot mask active LOW/MEDIUM recommendations.
- Grants are keyed by source, scope, tier, and policy version; TTL is at most 300 seconds and never exceeds the recommendation expiry.

## Trust and failure behavior

Active hosted eligibility requires a verified triggering source and the stricter Cloudflare source path. A test-only `ENFORCEMENT_ALLOW_UNVERIFIED_SOURCE_FOR_TESTS` escape hatch is false by default and rejected in staging/production. Turnstile uses separate enforcement configuration, server-side Siteverify, fixed action and hostname checks, a bounded timeout, and no token persistence. Invalid tokens and provider failures create no grant. Backend/database evaluation failures and malformed decisions fail open to portal `ALLOW` so unrelated portal availability is preserved.

## Persistence and concurrency

Add `enforcement_request_windows` and `enforcement_challenge_grants` in one child migration after PR4. Counter increments use PostgreSQL `INSERT ... ON CONFLICT DO UPDATE ... RETURNING`; no read-modify-write, Redis, locking service, cleanup worker, or generic policy-state table is introduced. SQLite adapters are retained for unit tests, while PostgreSQL integration tests prove concurrent increments.

## Validation

The implementation must include unit tests for policy/evaluator transitions, repository and migration tests, API contract/auth tests, Turnstile success/failure/replay/outage tests, portal source/config/fail-open/challenge/throttle tests, a controlled local end-to-end proof, and full backend/portal regressions. Documentation must separate local/test evidence from hosted readiness and retain the unresolved Cloudflare topology gates.

## Explicit exclusions

No PR6 HIGH blocking, PR7 CRITICAL/WAF control, Redis, global middleware, multi-route enforcement, WAF mutation, model changes, retraining, or unrelated refactoring.
