# SSE Real-Stack E2E Design

## Goal

Prove locally, in a real Chromium browser, that a newly committed WAF alert
travels through FastAPI SSE and the authenticated Next.js BFF and appears in
the dashboard without a page reload.

## Architecture

Extend the existing disposable authentication E2E environment rather than
creating a parallel login harness. An opt-in real-API mode starts FastAPI on a
loopback-only ephemeral port against the same disposable PostgreSQL database
that receives the real Alembic migration chain. Next.js receives only generated
test credentials, uses `USE_MOCK_API=false`, and keeps the browser boundary at
`Browser -> Next.js Route Handler -> FastAPI`.

One SSE-specific Playwright configuration runs Chromium and the existing auth
global setup. The test completes the real password-plus-TOTP journey and visits
the dashboard, installs a main-frame navigation-request recorder, then explicitly
navigates once to the alerts page. It first waits for the initial alerts response to settle and
proves the unique path is absent, then waits for the browser SSE response.
After submitting a uniquely tagged WAF event directly to loopback FastAPI, it
requires a second alerts response containing the unique path before a retrying
locator assertion proves the row appears. The main-frame document-request count
is baselined after the explicit alerts navigation and must not increase after
ingest. Because alerts have no periodic refetch interval, this ordering proves the
post-ingest query was triggered by stream synchronization rather than the
initial page load.

## Isolation And Cleanup

- PostgreSQL, PostgREST, credentials, account rows, and alert rows are generated
  for one run and removed by the existing labeled-resource cleanup.
- FastAPI binds to `127.0.0.1` only and is stopped in `finally` before Docker
  cleanup. It runs from an empty temporary working directory with repository
  `PYTHONPATH`, so Pydantic cannot discover the repository `.env`.
- Playwright/Next.js and FastAPI receive allowlisted child environments plus
  explicit generated test configuration. FastAPI sets `APP_ENV=testing`, fake
  email, disabled/optional notification worker settings, missing absolute model
  paths, and distinct generated API/WAF keys.
- No `.env` file is written and no live or hosted credential is forwarded to a
  test child process.
- Existing auth E2E remains mock-backed unless the new SSE runner explicitly
  enables real-API mode.

## Test Matrix

The browser test supplies the missing vertical proof. Edge cases remain a named
second layer, executed with these owners:

- Backend protocol/lifecycle/auth/races:
  `tests/unit/test_alert_event_broadcaster.py`,
  `tests/unit/test_alert_stream_route.py`,
  `tests/unit/test_triage_use_case.py`,
  `tests/unit/test_traffic_log_repository.py`, and
  `tests/integration/test_api.py`.
- BFF/browser synchronization/security:
  `frontend/lib/bff-alert-stream.test.ts`,
  `frontend/app/api/alerts/stream/route.test.ts`, and
  `frontend/components/alerts/AlertStreamSync.test.tsx`.

Together those suites cover named minimal payloads, bounded slow-subscriber
queues, disconnect cleanup, five-minute recycling, reconnect invalidation,
lost-owner races, bearer/account/RBAC denial, handshake timeout, redirect and
MIME rejection, rejected-body cancellation, generic errors, and safe headers.

Hosted Cloudflare/reverse-proxy buffering and reconnection remain unverified
because official Next.js guidance makes streaming support dependent on every
deployment hop.

## Failure Handling

Startup readiness uses condition polling, not fixed sleeps. A dedicated managed
child handle races readiness against early process exit, retains only bounded
stdout/stderr tails, redacts URL credentials/bearer-like values before failure
output, and performs idempotent bounded termination on startup, Playwright,
cleanup failures, `SIGINT`, and `SIGTERM`. Forced Windows tree termination first
rechecks that the retained child has not already exited to reduce PID-reuse
risk. Backend process exit, health timeout, failed WAF ingest, absent SSE
response, absent post-ingest refetch, or absent unique alert row fails the run.

## Rollback

Remove the SSE-specific runner, Playwright configuration/spec, and the opt-in
real-API branch in the existing disposable environment. Production code and
contracts are unaffected.
