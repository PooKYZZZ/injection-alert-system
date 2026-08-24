# Audit Remediation Design

## Goal

Resolve the approved audit findings as a sequence of narrow, independently
validated commits while preserving the existing Browser -> Next.js BFF ->
FastAPI boundary, model integrity checks, authorization rules, and controlled-
local retraining policy.

## Scope and constraints

- Work only on the fourteen approved findings and directly required tests or
  documentation.
- Keep the hosted Supabase database outside the normal local Compose migration
  path. Local startup must fail closed before Alembic can contact a remote host.
- Keep canonical timestamps in UTC. Localize only operator-facing presentation.
- Preserve the existing database schema, API response contracts, confidence
  thresholds, transport actions, and production model registry protections.
- Use one focused commit per completed issue. Closely coupled findings may share
  a commit only when separating them would leave an incomplete or unsafe state.
- Do not add dependencies, broad infrastructure, or repository-wide lint gates.

## Architecture decisions

### Local database safety

The base Compose backend will call a small migration entrypoint that validates
`DATABASE_URL` before invoking Alembic. SQLite and explicitly local hosts are
allowed; remote hosts fail closed. A local Compose overlay will provide a
PostgreSQL service and override the backend URL, so the documented development
workflow is explicit and does not depend on an ignored `.env` database value.
Remote migrations remain an explicit operator action outside normal local
startup.

### BFF reliability and privacy

The existing BFF client remains the owner of FastAPI calls. A single bounded
timeout and consistent upstream error mapping will be applied there. Logging
will keep status and route identity while dropping query strings, payloads, and
upstream response bodies. Browser timezone will be obtained at the browser
boundary, validated by the BFF, and forwarded explicitly; the Next.js server
timezone will not be presented as the requester's timezone.

### Telegram presentation

Notification payload timestamps remain canonical ISO-8601 instants. The
Telegram renderer will parse timezone-aware timestamps and format them in a
configured `NOTIFICATION_TIMEZONE` at delivery time. The existing small
renderer remains the template boundary; no template framework is introduced.
Malformed or timezone-naive timestamps fail closed as invalid notification
payloads.

### Retraining reliability

The repository root becomes an explicit dependency derived from module
location or application wiring rather than `Path.cwd()`. Blocking filesystem
work in async request paths will be moved to existing threadpool mechanisms
where it is material. Run details will distinguish absent evaluation from
unreadable evidence. Fresh digest validation remains intact; optimization will
only be added if investigation proves a safe invalidation strategy is needed.

### Containers and CI

Compose readiness will use existing health checks. Runtime images will use
small build/runtime stages and non-root users where permissions have been
verified. CI hardening will be incremental: immutable action references,
bounded job runtimes, Compose/image checks, and focused lint/type checks around
touched modules. Existing repository-wide Ruff debt will not become a new
blocking gate.

## Validation strategy

Each issue follows red-green-refactor where behavior is testable, then runs the
narrowest owner-level tests and static checks. The final branch receives the
full backend suite, frontend lint/typecheck/tests/build, Docker builds, Compose
configuration, safe controlled-local startup, BFF integration checks,
retraining tests, Telegram formatter tests, and a final diff/commit review.

## Explicitly out of scope

Redis, Celery, Kafka, Kubernetes, automatic model promotion, production model
registry writes, schema migrations, frontend/backend rewrites, and broad
formatting or lint cleanup are not part of this remediation.
