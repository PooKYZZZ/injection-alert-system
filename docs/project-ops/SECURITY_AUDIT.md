# SECURITY_AUDIT.md — Injection Alert System
# Full Security Audit Findings — Agent Reference Document

**Audit date:** 2026-03-22
**Audited by:** Froilan (Team 13) with Claude Sonnet 4.6
**Linked tasks:** docs/project-ops/TASKS.md
**Status key:** `OPEN` `IN_PROGRESS` `RESOLVED` `DEFERRED`

---

## How agents use this file

This file is the authoritative record of every security and logic issue found in the codebase. When implementing a fix, read the relevant finding here first to understand the full context before touching any file. After a fix is implemented and verified, update the finding status from `OPEN` to `RESOLVED` and add the commit hash.

Do not resolve a finding unless the corresponding TASKS.md task is also `[x]`.

---

## Summary Table

| ID | Severity | Area | Title | Status | Task |
|----|----------|------|-------|--------|------|
| S-01 | 🔴 HIGH | FastAPI | No body size limit on inference endpoints | OPEN | 1.1 |
| S-02 | 🔴 HIGH | FastAPI | No security headers on any response | OPEN | 1.2 |
| S-03 | 🟡 MEDIUM | FastAPI | CORS allows unused HTTP methods in production | OPEN | 1.3 |
| S-04 | 🟡 MEDIUM | FastAPI | is_development flag can be overridden in .env | OPEN | 1.4 |
| S-05 | 🟡 MEDIUM | FastAPI | ModelService dead aliases pollute response shape | OPEN | 1.5 |
| S-06 | 🔴 HIGH | Frontend | next.config.ts missing entirely | OPEN | 1.6 |
| S-07 | 🟡 MEDIUM | Frontend | No security headers on Next.js responses | OPEN | 1.7 |
| S-08 | 🟡 MEDIUM | Frontend | Session maxAge is 30-day default | OPEN | 1.8 |
| S-09 | 🟡 MEDIUM | Frontend | timezone param forwarded raw to FastAPI | OPEN | 1.9 |
| S-10 | 🟢 LOW | Docs | AGENTS.md describes Supabase as planned | OPEN | 1.10 |
| S-11 | 🟡 MEDIUM | Database | labeled_at column missing timezone=True | OPEN | 2.1 |
| S-12 | 🔴 HIGH | Database | RLS not enabled on traffic_logs | OPEN | 2.2 |
| S-13 | 🟢 LOW | Repo | injection_alerts.db may not be gitignored | OPEN | 2.3 |
| S-14 | 🔴 HIGH | Dependencies | npm packages not audited for CVEs | OPEN | 3.1 |
| S-15 | 🔴 HIGH | Dependencies | pip packages not audited for CVEs | OPEN | 3.2 |

---

## Detailed Findings

---

### S-01 — No body size limit on inference endpoints

**Severity:** 🔴 HIGH
**Status:** OPEN
**Task:** 1.1
**Resolved in commit:** —

**Location:**
- `web_app/presentation/app.py` — no body size middleware registered
- `web_app/presentation/middleware/` — folder exists but is empty

**Description:**
FastAPI has no middleware-level body size cap. A malicious client can send a multi-gigabyte payload to `POST /api/triage` or `POST /api/predict`. The body gets read into memory before Pydantic validation runs, meaning the `max_length=65536` on `PredictionRequest.http_request` offers no DoS protection — the damage is done before the validator fires.

**Impact:**
- DistilBERT inference thread can be starved or crashed
- Server memory can be exhausted
- Demo can be taken down by a single malformed request

**Fix:**
Create `web_app/presentation/middleware/body_limit.py` with a Starlette `BaseHTTPMiddleware` that checks `Content-Length` and returns HTTP 413 before the body is read. Register it as the first middleware in `create_app()`.

**Verify after fix:**
```powershell
# Should return 413
curl -X POST http://localhost:8000/api/triage \
  -H "Content-Length: 2000000" \
  -H "Authorization: Bearer $API_SECRET_KEY"
```

---

### S-02 — No security headers on FastAPI responses

**Severity:** 🔴 HIGH
**Status:** OPEN
**Task:** 1.2
**Resolved in commit:** —

**Location:**
- `web_app/presentation/app.py`
- `web_app/presentation/middleware/` — empty

**Description:**
Every FastAPI response is bare JSON with no browser security headers. Without `X-Content-Type-Options: nosniff`, browsers can MIME-sniff responses and execute them as scripts. Without `X-Frame-Options: DENY`, the API responses can be framed. Without `Referrer-Policy`, internal API paths leak in the Referer header.

**Impact:**
- MIME confusion attacks possible
- Clickjacking via framing
- Internal URL path disclosure

**Fix:**
Create `web_app/presentation/middleware/security_headers.py` with a Starlette `BaseHTTPMiddleware` that stamps security headers on every outgoing response. Register after body_limit, before CORS.

**Headers to add:**
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```

---

### S-03 — CORS allows unused HTTP methods in production

**Severity:** 🟡 MEDIUM
**Status:** OPEN
**Task:** 1.3
**Resolved in commit:** —

**Location:**
- `web_app/presentation/app.py` lines ~105–113

**Description:**
The production CORS config allows `["GET", "POST", "PUT", "PATCH", "DELETE"]`. The BFF only ever sends `GET` and `PATCH` to FastAPI. `PUT` and `DELETE` are advertised surface area that is never used, violating the principle of least privilege for cross-origin access.

**Fix:**
Change production `allow_methods` to `["GET", "POST", "PATCH"]`.

---

### S-04 — is_development flag can be overridden in .env

**Severity:** 🟡 MEDIUM
**Status:** OPEN
**Task:** 1.4
**Resolved in commit:** —

**Location:**
- `web_app/config.py`

**Description:**
`is_development` is a settable `bool` Pydantic field with a default of `False`. This means setting `IS_DEVELOPMENT=true` in `.env` while `APP_ENV=production` puts the app into development mode — enabling model fallback to mock mode instead of failing fast. This is a silent safety bypass.

**The other environment properties (`is_production`, `is_testing`, `is_staging`) are correctly implemented as read-only `@property` methods derived from `app_env`. `is_development` should match this pattern.**

**Fix:**
Remove `is_development: bool = False` field and the validator logic that sets it. Add `@property` that returns `self.app_env == "development"`.

---

### S-05 — ModelService dead aliases pollute response shape

**Severity:** 🟡 MEDIUM
**Status:** OPEN
**Task:** 1.5
**Resolved in commit:** —

**Location:**
- `web_app/services/model_service.py` — `_build_response()` method

**Description:**
`_build_response()` adds `response["class"]` and `response["confidence_level"]` as aliases with a TODO comment saying they should be removed once `TriageUseCase` migrates. `TriageUseCase` already reads `raw_result.get("prediction")` and `raw_result.get("confidence_level") or raw_result.get("confidence_tier")` — the migration is done. The aliases are dead but still pollute every prediction response, causing ambiguity in what the canonical shape is.

**Fix:**
Remove the two alias lines and the TODO comment from `_build_response()`.

---

### S-06 — next.config.ts missing entirely

**Severity:** 🔴 HIGH
**Status:** OPEN
**Task:** 1.6
**Resolved in commit:** —

**Location:**
- `frontend/` — no `next.config.ts` or `next.config.js` exists

**Description:**
Next.js sends `X-Powered-By: Next.js` on every response, revealing the framework. No security headers are configured at the Next.js level. No CSP is set. This is the most visible security gap on the frontend — any automated scanner will flag it immediately.

**Impact:**
- Stack disclosure via `X-Powered-By` header
- No CSP protecting against XSS
- No frame protection at the framework level

**Fix:**
Create `frontend/next.config.ts` with `poweredByHeader: false` and a `headers()` function setting `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`, and a static CSP.

**Note:** Use static CSP (not nonce-based) to avoid forcing all pages into dynamic rendering.

---

### S-07 — No security headers on Next.js middleware responses

**Severity:** 🟡 MEDIUM
**Status:** OPEN
**Task:** 1.7
**Resolved in commit:** —

**Location:**
- `frontend/middleware.ts`

**Description:**
`middleware.ts` is a thin NextAuth export that adds no security headers to responses. Belt-and-suspenders approach requires headers at both the `next.config.ts` level and the middleware level since middleware runs on the edge and processes responses before config headers in some cases.

**Fix:**
Wrap the NextAuth middleware to also stamp `X-Content-Type-Options` and `X-Frame-Options` on every response.

---

### S-08 — Session maxAge is 30-day NextAuth default

**Severity:** 🟡 MEDIUM
**Status:** OPEN
**Task:** 1.8
**Resolved in commit:** —

**Location:**
- `frontend/auth.ts`

**Description:**
`session: { strategy: 'jwt' }` uses NextAuth's default `maxAge` of 30 days. A stolen or forgotten session token remains valid for a month. For a SOC analyst dashboard where sessions should expire after a shift, this is inappropriate.

**Industry standard for security-sensitive tools:** 8–12 hour session lifetime.

**Fix:**
Add `maxAge: 8 * 60 * 60` (28800 seconds = 8 hours) to the session config.

---

### S-09 — timezone param forwarded raw to FastAPI

**Severity:** 🟡 MEDIUM
**Status:** OPEN
**Task:** 1.9
**Resolved in commit:** —

**Location:**
- `frontend/lib/bff-client.ts` — `getStats()` function

**Description:**
The `timezone` URL query parameter is forwarded directly to FastAPI with no validation or sanitization. A user could send `timezone=../../../../etc/passwd` or any arbitrary string. FastAPI accepts it as an optional plain string with no format enforcement on the backend either.

**Fix:**
Validate against IANA timezone pattern `^[A-Za-z]+\/[A-Za-z_]+$` before forwarding. Silently drop invalid values.

---

### S-10 — AGENTS.md describes Supabase as planned

**Severity:** 🟢 LOW
**Status:** OPEN
**Task:** 1.10
**Resolved in commit:** —

**Location:**
- `AGENTS.md` — intro paragraph and Stack section

**Description:**
AGENTS.md says "It is not yet the full Docker/ModSecurity/Redis/Supabase deployment target" and lists Supabase as "the planned production boundary." Supabase is live with 84 rows. This misleads agents into treating the database as not yet connected.

**Fix:**
Update the description to accurately state Supabase is the live production database and Docker/ModSecurity/Redis are not yet implemented.

---

### S-11 — labeled_at column missing timezone=True

**Severity:** 🟡 MEDIUM
**Status:** OPEN
**Task:** 2.1
**Resolved in commit:** —

**Location:**
- `web_app/infrastructure/database.py` — `TrafficLog.labeled_at`
- Needs Alembic migration `000006`

**Description:**
Every datetime column in `TrafficLog` uses `DateTime(timezone=True)` (TIMESTAMPTZ in PostgreSQL) except `labeled_at`, which uses plain `DateTime` (TIMESTAMP without timezone). This inconsistency means analyst feedback timestamps are stored without timezone info, causing unpredictable sort order and display inconsistency when timestamps from different timezones are compared.

**Squawk linter flags this pattern as `prefer-timestamptz` violation.**

**Fix:**
Write manual Alembic migration using `op.alter_column` with `USING labeled_at AT TIME ZONE 'UTC'`. Update `database.py` to use `DateTime(timezone=True)`.

**Note:** Autogenerate cannot detect this change — must be written manually.

---

### S-12 — RLS not enabled on traffic_logs in Supabase

**Severity:** 🔴 HIGH
**Status:** OPEN
**Task:** 2.2
**Resolved in commit:** —

**Location:**
- Supabase dashboard → traffic_logs table

**Description:**
Row Level Security is disabled on the `traffic_logs` table. If the Supabase connection string or anon key is ever exposed, any authenticated Supabase client can read or write every row. For a system storing HTTP request payloads (which may contain sensitive data), this is a significant data exposure risk.

**Fix:**
Enable RLS via Supabase dashboard. Add service role bypass policy so the FastAPI backend (which uses the service role key) retains full access.

**This is a 2-minute dashboard action, not a code change.**

---

### S-13 — injection_alerts.db may not be gitignored

**Severity:** 🟢 LOW
**Status:** OPEN
**Task:** 2.3
**Resolved in commit:** —

**Location:**
- `.gitignore` (verify)
- `injection_alerts.db` (root level)

**Description:**
A local SQLite database file exists at the repo root containing real traffic log data. If not gitignored, it could be accidentally committed and pushed, exposing HTTP request payloads stored during development.

**Fix:**
Verify `injection_alerts.db` is in `.gitignore`. If not, add it.

---

### S-14 — npm packages not audited for CVEs

**Severity:** 🔴 HIGH
**Status:** OPEN
**Task:** 3.1
**Resolved in commit:** —

**Location:**
- `frontend/package.json`
- `.github/workflows/ci.yml`

**Description:**
`npm audit` is not run as part of CI. In 2025, over 99% of open source malware occurred on npm. The average npm project has 79 transitive dependencies. An unaudited dependency tree is a significant supply chain risk, especially for a security-focused project.

**Fix:**
Run `npm audit --audit-level=high` in `frontend/`. Fix any high/critical CVEs. Add the command to CI.

---

### S-15 — pip packages not audited for CVEs

**Severity:** 🔴 HIGH
**Status:** OPEN
**Task:** 3.2
**Resolved in commit:** —

**Location:**
- `requirements.txt`
- `.github/workflows/ci.yml`

**Description:**
`pip-audit` is not run as part of CI. Python dependencies including FastAPI, SQLAlchemy, and Transformers have active CVE discovery pipelines. An unaudited Python dependency tree is a silent vulnerability source.

**Fix:**
Install `pip-audit`. Run `pip-audit -r requirements.txt`. Fix any reported vulnerabilities. Add to CI.

---

## Deferred Findings (Out of Scope for PD1)

These were identified but intentionally excluded from the implementation plan. Document them here for the May defense sprint.

| ID | Title | Reason deferred |
|----|-------|-----------------|
| D-01 | Redis IP blocklist and rate-limit state | Single-instance demo, in-memory sufficient |
| D-02 | Nonce-based CSP | Forces full SSR, breaks performance |
| D-03 | Per-request statement timeout | Irrelevant at 84-row demo scale |
| D-04 | Rolling session updateAge | maxAge=8h sufficient for demo |
| D-05 | Per-user Supabase RLS policies | Multi-tenant feature, not applicable |
| D-06 | OpenTelemetry structured logging | Post-defense enhancement |
| D-07 | Login brute-force lockout | Low risk for 1-user demo, noted for panel |

---

## What is confirmed NOT a vulnerability

These were investigated and found to be correctly implemented:

```
✅ POST /api/feedback IS protected — on internal_router with bearer auth
✅ ALL routes use internal_router — auth is router-level, not per-route
✅ verify_internal_token uses secrets.compare_digest — timing-safe
✅ INTERNAL_API_KEY is server-only, never sent to browser
✅ Zod validates all BFF responses before forwarding to UI
✅ parseAlertId regex prevents non-numeric IDs reaching FastAPI
✅ Error messages are browser-safe — no internal details leak
✅ ModelService loads at startup via lifespan, not per-request
✅ run_in_threadpool correctly used for sync ML inference
✅ PgBouncer statement_cache_size=0 fix already applied
✅ pool_pre_ping=True prevents dead connection errors
✅ enable_api_docs correctly disabled in production via settings
✅ triage_status validated at both BFF and application layer
✅ isMockMode() reads server-only env — never exposed to browser
```
