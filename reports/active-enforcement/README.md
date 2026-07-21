# PR5 Active Enforcement Evidence

**Status:** Local/test implementation only; hosted/production `ENFORCE` remains disabled.

This report folder is reserved for observed PR5 evidence. Do not use unit tests,
image builds, or local Compose results as hosted destructive-enforcement proof.

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
- The portal applies `ALLOW`, `CHALLENGE`, and `THROTTLE` only at `/records/search`.

## Not proven here

- Cloudflare Worker header behavior, Pseudo IPv4 handling, direct-origin isolation, and immediate tunnel-peer trust remain unresolved topology gates.
- No hosted or production user traffic has been placed in active enforcement.
- HIGH/CRITICAL blocking, WAF mutation, Redis, and global/multi-route enforcement remain out of scope.

## Evidence template

Record command, commit SHA, environment, source-eligibility setting, migration
revision, exact test counts, LOW/MEDIUM transition outputs, concurrency result,
provider result categories, portal response behavior, and secret/token leakage
checks. Keep credentials and raw Turnstile tokens out of this report.
