# SSE Security Hardening Design

**Date:** 2026-07-19

## Goal

Harden the existing thesis-scale alert SSE path against stale authorization,
post-commit notification failures, unsafe upstream behavior, and documentation
drift without changing the event payload or introducing distributed runtime
infrastructure.

## Scope

- Keep `alert.created` with `{"changed": true}` as an invalidation signal.
- Keep REST as the alert-data contract.
- Keep FastAPI native SSE, one dashboard EventSource, bounded subscriber queues,
  and TanStack Query invalidation.
- Add finite stream lifetime so reconnects rerun BFF account freshness and RBAC.
- Make publication after persistence explicitly best-effort.
- Harden the BFF handshake, redirect, MIME, error, and cache behavior.
- Reconcile maintained docs that still describe SSE as planned.

## Design

FastAPI will close each stream after five minutes. Native EventSource reconnect
behavior will reopen the BFF route, which reruns Auth.js session validation,
database-backed account freshness, MFA level, role, and permission checks. The
connection remains content-free beyond the existing change signal.

The triage use case will publish through one private helper. Publisher failures
will be logged without request or alert content and will not convert a committed
write into an HTTP failure.

The BFF upstream fetch will use a ten-second connection-establishment timeout,
reject redirects, require an exact `text/event-stream` media type, retain client
abort propagation, and return generic errors. Its response will be explicitly
private and non-cacheable with proxy buffering disabled and MIME sniffing
disabled.

## Deferred

- Distributed pub/sub, durable replay, WebSockets, and Redis.
- Application-level global subscriber caps; public deployments should enforce
  connection/rate controls at the reverse proxy or Cloudflare boundary.
- A forced PostCSS override. The current advisory path is not reachable in this
  slice and the installed Next.js line still pins the affected transitive
  version.

## Verification

Use test-first regression coverage for publisher failure isolation, finite
stream lifetime and cleanup, upstream timeout/redirect/MIME validation, safe
errors, cache headers, and existing EventSource behavior. Then run the full
backend and frontend suites, lint, typecheck, production build, dependency
audits, and `git diff --check`.

## Residual Risk And Rollback

The accepted residual risks are single-process fan-out, no durable replay,
HTTP/1.1 per-origin browser connection limits, and unverified hosted proxy
buffering/reconnect behavior. These are visible thesis constraints rather than
claims of production readiness.

Rollback is isolated: remove the dashboard synchronization component, BFF and
backend stream routes, and post-commit publisher wiring. The unchanged REST
alert/stats contracts remain the source of truth, so polling/manual refresh
continues to function without a data migration or payload-contract rollback.
