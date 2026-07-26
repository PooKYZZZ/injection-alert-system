# Active Enforcement Evidence

**Status:** Local/test implementation only; hosted/production `ENFORCE` remains disabled.

This report folder is reserved for observed PR5/PR6 evidence. Do not use unit tests,
image builds, or local Compose results as hosted destructive-enforcement proof.

## Canonical controlled E2E evidence

[`PR5_CONTROLLED_E2E_PROOF.md`](PR5_CONTROLLED_E2E_PROOF.md) records the PASS
result for the controlled local Docker Compose full-stack validation through
`http://localhost:8089/records/search` using disposable PostgreSQL 16 and
Cloudflare-published Turnstile test credentials. It is local acceptance evidence,
not hosted destructive-enforcement proof.

[`PR6_HIGH_APPLICATION_BLOCK_PROOF.md`](PR6_HIGH_APPLICATION_BLOCK_PROOF.md)
records the coordinated HIGH application-block implementation, automated
validation, and disposable controlled-local E2E. It also records that hosted
activation remains disabled and CRITICAL remains outside PR6.

## Implemented locally

- `ENFORCE` creates explicit `confidence-enforcement-v2` recommendations.
- LOW uses a 60-second fixed window and challenges the first request above the configured maximum (default 5).
- MEDIUM challenges before access, then allows the configured post-challenge window (default 10) and returns `retry_after_seconds` on the first excess request.
- Request windows use PostgreSQL atomic upserts; challenge grants are tier-bound and capped by recommendation expiry.
- Turnstile Siteverify is server-side only, validates action `record_search_enforcement` and configured hostname, and persists no token.
- Cloudflare's published dummy response was observed without the production
  action field, so controlled provider proof uses explicit test mode with a
  published test secret. Test mode is forbidden in staging/production; normal
  mode still requires the production action and hostname.
- The portal applies exact `ALLOW`, `CHALLENGE`, `THROTTLE`, and PR6 `BLOCK`
  decisions only at `/records/search`.
- The controlled E2E report validates LOW/MEDIUM challenge, grant, counter,
  throttle, invalid-challenge, and evaluation-outage behavior; hosted Cloudflare
  topology and production ENFORCE remain pending/disabled.

## Not proven here

- Cloudflare Worker header behavior, Pseudo IPv4 handling, direct-origin isolation, and immediate tunnel-peer trust remain unresolved topology gates.
- No hosted or production user traffic has been placed in active enforcement.
- CRITICAL/WAF mutation, Redis, and global/multi-route enforcement remain out of scope.

## Evidence template

Record command, commit SHA, environment, source-eligibility setting, migration
revision, exact test counts, LOW/MEDIUM transition outputs, concurrency result,
provider result categories, portal response behavior, and secret/token leakage
checks. Keep credentials and raw Turnstile tokens out of this report.
