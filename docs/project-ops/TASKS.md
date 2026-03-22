# TASKS.md — Injection Alert System
# Atomic Task List for Autonomous Agent Execution

**Last updated:** 2026-03-22
**Linked plan:** docs/project-ops/IMPLEMENTATION_PLAN.md

---

## How to use this file

**Agent instructions:**
1. Read `AGENTS.md` and `IMPLEMENTATION_PLAN.md` first
2. Find the first task in the current phase with status `[ ]`
3. Read the full task block including Acceptance and Verify sections
4. Implement the change
5. Run every command in the Verify block — all must pass
6. Update this file: change `[ ]` to `[x]` for the completed task
7. Update `docs/project-ops/STATUS.md` current state section
8. Commit on a `fix/<scope>` or `feat/<scope>` branch
9. Start a NEW conversation for the next task

**Status legend:**
```
[ ]  Not started
[~]  In progress
[x]  Done and verified
[!]  Blocked — see note
```

**Do not mark [x] unless ALL verify commands pass.**
**Do not work on Phase 2+ tasks until all Phase 1 tasks are [x].**

---

## Phase 1 — Security Hardening

---

### Task 1.1 — Create body size limit middleware

**Status:** `[ ]`
**Branch:** `fix/body-size-limit`
**Files to create:**
- `web_app/presentation/middleware/body_limit.py`

**Files to edit:**
- `web_app/presentation/app.py` — register middleware

**What to implement:**
Create a Starlette `BaseHTTPMiddleware` that reads the `Content-Length` header on every incoming request. If the value exceeds 1MB (1_048_576 bytes), return HTTP 413 immediately before the body is read. If `Content-Length` is absent on a POST/PATCH/PUT request, still allow it through — do not block requests without a Content-Length header since some clients omit it. Register the middleware in `create_app()` BEFORE the CORS middleware so it runs first.

**Constraints:**
- Do not use any new pip packages — Starlette's `BaseHTTPMiddleware` is already available
- Do not touch any route handlers
- Do not change the CORS config in this task

**Acceptance:**
- Middleware file exists at the correct path
- Middleware is registered in `app.py`
- A POST request with `Content-Length: 2000000` header to any route returns 413
- Normal requests under 1MB pass through unaffected

**Verify:**
```powershell
.venv\Scripts\python.exe -m pytest -q
```
All tests must still pass. No new test failures.

---

### Task 1.2 — Create security headers middleware

**Status:** `[ ]`
**Branch:** `fix/fastapi-security-headers`
**Files to create:**
- `web_app/presentation/middleware/security_headers.py`

**Files to edit:**
- `web_app/presentation/app.py` — register middleware

**What to implement:**
Create a Starlette `BaseHTTPMiddleware` that stamps the following headers on every outgoing response. Register it in `create_app()` after body_limit middleware but before CORS middleware:
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: camera=(), microphone=(), geolocation=()
```
Do NOT add `Strict-Transport-Security` — this is HTTP locally and would break the browser.

**Constraints:**
- Do not use any new pip packages
- Do not touch any route handlers or schemas
- Do not add HSTS (HTTP-only local environment)

**Acceptance:**
- Middleware file exists at the correct path
- Middleware is registered in `app.py`
- `curl -I http://localhost:8000/health` response includes `X-Content-Type-Options: nosniff`

**Verify:**
```powershell
.venv\Scripts\python.exe -m pytest -q
```
All tests must still pass.

---

### Task 1.3 — Fix CORS allowed methods in production

**Status:** `[ ]`
**Branch:** `fix/cors-methods`
**Files to edit:**
- `web_app/presentation/app.py`

**What to implement:**
In the production/staging CORS config block, change `allow_methods` from:
```python
["GET", "POST", "PUT", "PATCH", "DELETE"]
```
to:
```python
["GET", "POST", "PATCH"]
```
The BFF only ever sends GET and PATCH to FastAPI. PUT and DELETE are advertised surface area that is never used.

**Constraints:**
- Only change the production/staging branch of the if/else CORS block
- Do not touch the development branch CORS config
- Do not touch any other part of app.py in this task

**Acceptance:**
- Production CORS config lists only GET, POST, PATCH
- Development CORS config is unchanged

**Verify:**
```powershell
.venv\Scripts\python.exe -m pytest -q
```

---

### Task 1.4 — Fix is_development flag in config.py

**Status:** `[ ]`
**Branch:** `fix/config-is-development`
**Files to edit:**
- `web_app/config.py`

**What to implement:**
The `is_development` field is currently a settable `bool` that can be overridden in `.env`, which means someone could set `is_development=true` while `app_env=production` and get mock model fallback in production. Convert it to a read-only `@property` derived purely from `app_env`:

Remove the `is_development: bool = False` field and the `apply_environment_defaults` validator logic that sets it. Add a `@property` that returns `self.app_env == "development"` instead. The `is_production`, `is_testing`, and `is_staging` properties already follow this pattern — match them exactly.

**Constraints:**
- Do not change any other settings fields
- Do not change threshold values
- Ensure `is_development` still works as a boolean in all call sites

**Acceptance:**
- `is_development` is a `@property` not a `Field`
- Cannot be overridden by setting `IS_DEVELOPMENT=true` in `.env`
- All existing call sites still work

**Verify:**
```powershell
.venv\Scripts\python.exe -m pytest -q
```

---

### Task 1.5 — Remove ModelService compatibility aliases

**Status:** `[ ]`
**Branch:** `fix/remove-model-aliases`
**Files to edit:**
- `web_app/services/model_service.py`

**What to implement:**
In `_build_response()`, remove these two lines at the bottom of the method:
```python
response["class"] = prediction
response["confidence_level"] = confidence_tier
```
And the TODO comment above them.

Before removing, confirm that `triage_use_case.py` reads `raw_result.get("prediction")` and `raw_result.get("confidence_level") or raw_result.get("confidence_tier")` — it already does. The canonical fields `prediction` and `confidence_tier` remain in the response. Only the dead aliases are removed.

**Constraints:**
- Do not rename any canonical fields
- Do not change any response schema
- Do not touch any route handlers

**Acceptance:**
- `_build_response()` no longer sets `response["class"]` or `response["confidence_level"]`
- TODO comment is removed
- All triage tests still pass

**Verify:**
```powershell
.venv\Scripts\python.exe -m pytest -q
```

---

### Task 1.6 — Create frontend/next.config.ts

**Status:** `[ ]`
**Branch:** `fix/next-config-security`
**Files to create:**
- `frontend/next.config.ts`

**What to implement:**
Create `next.config.ts` with:
- `poweredByHeader: false` — removes `X-Powered-By: Next.js` from all responses
- Security headers via `headers()` async function applied to all routes (`source: '/(.*)'`)
- Headers to add:
  ```
  X-Frame-Options: DENY
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
  Permissions-Policy: camera=(), microphone=(), geolocation=(), payment=()
  Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-eval' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; frame-ancestors 'none'
  ```
- Use `unsafe-eval` and `unsafe-inline` in CSP for now — nonce-based CSP forces full SSR which breaks performance. This is intentional and acceptable for the demo.

**Constraints:**
- Do not use nonce-based CSP
- Do not add `Strict-Transport-Security` (HTTP local)
- Export must be `export default nextConfig` as `NextConfig` type
- File must be TypeScript (.ts not .js)

**Acceptance:**
- `frontend/next.config.ts` exists
- `npm run dev` still starts without error
- Browser DevTools shows `X-Frame-Options: DENY` on dashboard responses

**Verify:**
```powershell
cd frontend
npm run typecheck
npx vitest run
```
Both must pass.

---

### Task 1.7 — Add security headers to Next.js middleware.ts

**Status:** `[ ]`
**Branch:** `fix/nextjs-middleware-headers`
**Files to edit:**
- `frontend/middleware.ts`

**What to implement:**
The current `middleware.ts` just exports the NextAuth middleware directly. Wrap it to also stamp security headers on every response. The pattern:
1. Call the NextAuth auth middleware to get the response
2. Before returning, set the security headers on the response object
3. Return the modified response

Headers to add on top of what next.config.ts already sets (middleware runs before config headers in some cases, belt-and-suspenders approach):
```
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
```

**Constraints:**
- Do not break the existing NextAuth session redirect logic
- Keep the `config.matcher` exactly as-is
- Do not add `AUTH_SECRET` or any session logic here

**Acceptance:**
- Middleware still redirects unauthenticated users to `/login`
- Authenticated users still reach dashboard
- Security headers present on both auth and non-auth responses

**Verify:**
```powershell
cd frontend
npm run typecheck
npx vitest run app/api/bff-routes.test.ts
```

---

### Task 1.8 — Set session maxAge in auth.ts

**Status:** `[ ]`
**Branch:** `fix/session-max-age`
**Files to edit:**
- `frontend/auth.ts`

**What to implement:**
Add `maxAge` to the session config. The current config is:
```ts
session: { strategy: 'jwt' }
```
Change to:
```ts
session: {
  strategy: 'jwt',
  maxAge: 8 * 60 * 60, // 8 hours — appropriate for SOC analyst shift
}
```
This replaces the 30-day NextAuth default with 8 hours.

**Constraints:**
- Do not change the strategy from 'jwt'
- Do not add `updateAge` — maxAge alone is sufficient
- Do not change any callbacks
- Do not touch auth.config.ts

**Acceptance:**
- `session.maxAge` is set to 28800 (8 * 60 * 60)
- Login still works with correct password
- Login still fails with wrong password

**Verify:**
```powershell
cd frontend
npm run typecheck
npx vitest run
```

---

### Task 1.9 — Validate timezone param in bff-client.ts

**Status:** `[ ]`
**Branch:** `fix/timezone-validation`
**Files to edit:**
- `frontend/lib/bff-client.ts`

**What to implement:**
In the `getStats()` function, before forwarding the `timezone` param to FastAPI, validate it against a safe pattern. A valid IANA timezone looks like `Asia/Manila` or `America/New_York` — two segments separated by `/`, letters and underscores only.

Add this check before `query.set('timezone', timezone)`:
- If timezone is provided but does not match the pattern, ignore it (do not forward it, do not throw an error)
- If timezone matches the pattern, forward it as before
- Pattern: `^[A-Za-z]+\/[A-Za-z_]+$`

**Constraints:**
- Do not add a new npm package for this
- Do not change the function signature
- Do not change any other param forwarding logic

**Acceptance:**
- Valid timezone (`Asia/Manila`) still forwarded correctly
- Invalid timezone (`../etc/passwd`) silently dropped, not forwarded
- No TypeScript errors

**Verify:**
```powershell
cd frontend
npm run typecheck
npx vitest run lib/bff-client.test.ts
```

---

### Task 1.10 — Fix stale Supabase description in AGENTS.md

**Status:** `[ ]`
**Branch:** `fix/agents-md-accuracy`
**Files to edit:**
- `AGENTS.md` (root)

**What to implement:**
Change the intro paragraph from:
```
It is not yet the full Docker/ModSecurity/Redis/Supabase deployment target.
```
To:
```
Supabase PostgreSQL is the live production database (84+ rows in traffic_logs,
connected via PgBouncer pooler). Docker Compose, ModSecurity, and Redis are
not yet implemented in this repo.
```

Also update the Stack section Data line from:
```
Data: SQLite for tests/local work, PostgreSQL as the async runtime target,
Supabase as the planned production boundary
```
To:
```
Data: SQLite for tests/local work, Supabase PostgreSQL as the live production
database (pooler port 6543, asyncpg with statement_cache_size=0)
```

**Constraints:**
- Do not change any Hard Rules
- Do not change any commands
- Do not change Architecture Boundaries section

**Acceptance:**
- AGENTS.md accurately describes Supabase as live, not planned
- Docker/ModSecurity/Redis correctly listed as not yet implemented

**Verify:**
Read the file and confirm changes are correct. No automated verify needed.

---

## Phase 2 — Database Fixes

---

### Task 2.1 — Write Alembic migration for labeled_at timezone

**Status:** `[ ]`
**Branch:** `fix/labeled-at-timezone`
**Files to create:**
- `migrations/versions/20260323_000006_fix_labeled_at_timezone.py`

**What to implement:**
Write a manual Alembic migration (do NOT use autogenerate — it cannot detect TIMESTAMP → TIMESTAMPTZ changes). The migration must:

`upgrade()`:
```sql
ALTER TABLE traffic_logs
ALTER COLUMN labeled_at TYPE TIMESTAMPTZ
USING labeled_at AT TIME ZONE 'UTC';
```

`downgrade()`:
```sql
ALTER TABLE traffic_logs
ALTER COLUMN labeled_at TYPE TIMESTAMP
USING labeled_at AT TIME ZONE 'UTC';
```

Follow the existing migration file structure in `migrations/versions/` exactly. Copy the header block format from `20260322_000005_add_performance_indexes.py`.

**Constraints:**
- Do not use autogenerate
- Do not touch any other column
- Do not modify the ORM model in database.py in this task — only the migration
- After migration runs, separately update `database.py` labeled_at column to `DateTime(timezone=True)`

**Acceptance:**
- Migration file exists with correct naming convention
- `alembic upgrade head` runs without error against Supabase
- `labeled_at` column shows as `timestamp with time zone` in Supabase dashboard
- `database.py` TrafficLog.labeled_at updated to `DateTime(timezone=True)`

**Verify:**
```powershell
.venv\Scripts\python.exe -m pytest -q
```

---

### Task 2.2 — Enable RLS on Supabase (manual step)

**Status:** `[ ]`
**Branch:** N/A — Supabase dashboard action, no code change

**What to do (manual — no code):**
1. Go to Supabase dashboard → your project
2. Table Editor → `traffic_logs`
3. Click "RLS disabled" toggle → Enable RLS
4. Go to Authentication → Policies
5. Add new policy on `traffic_logs`:
   - Policy name: `service_role_full_access`
   - Allowed operation: ALL
   - Target roles: `service_role`
   - USING expression: `true`
   - WITH CHECK expression: `true`
6. Verify the app still works after enabling RLS

**Acceptance:**
- RLS is shown as "enabled" in Supabase dashboard on traffic_logs
- Service role bypass policy exists
- Running the app and seeding still writes rows successfully
- `curl http://localhost:8000/api/alerts` (with bearer token) still returns data

**Verify:**
```powershell
.venv\Scripts\python.exe -c "
import asyncio
from web_app.infrastructure.database import engine
import sqlalchemy
async def test():
    async with engine.begin() as conn:
        result = await conn.execute(sqlalchemy.text('SELECT COUNT(*) FROM traffic_logs'))
        print('Row count:', result.scalar())
asyncio.run(test())
"
```
Must print a number, not throw an error.

---

### Task 2.3 — Verify injection_alerts.db is gitignored

**Status:** `[ ]`
**Branch:** `fix/gitignore-sqlite`
**Files to edit:**
- `.gitignore` (only if needed)

**What to implement:**
Check if `injection_alerts.db` is in `.gitignore`. Run:
```powershell
git check-ignore -v injection_alerts.db
```
If it outputs a match, the file is already ignored — mark this task [x] with no changes needed.
If it outputs nothing, add `*.db` and `injection_alerts.db` to `.gitignore`.

Also check if `dev.db` and `test.db` are covered.

**Acceptance:**
- `git check-ignore -v injection_alerts.db` returns a match
- `git check-ignore -v dev.db` returns a match
- SQLite files are not tracked in git

**Verify:**
```powershell
git check-ignore -v injection_alerts.db
git check-ignore -v dev.db
```

---

## Phase 3 — Dependency Audit

---

### Task 3.1 — Run npm audit and fix high/critical vulnerabilities

**Status:** `[ ]`
**Branch:** `fix/npm-audit`
**Files potentially edited:** `frontend/package.json`, `frontend/package-lock.json`

**What to implement:**
```powershell
cd frontend
npm audit --audit-level=high
```
If any high or critical CVEs are reported, run:
```powershell
npm audit fix
```
If `npm audit fix` cannot resolve automatically, manually update the specific package to the patched version using `npm install package@latest`.

Do NOT run `npm audit fix --force` — it can introduce breaking major version changes.

**Constraints:**
- Only fix high and critical severity issues
- Do not upgrade packages to major versions unless the CVE cannot be fixed otherwise
- After any package change, run full test suite

**Acceptance:**
- `npm audit --audit-level=high` exits with code 0
- No high or critical CVEs reported

**Verify:**
```powershell
cd frontend
npm audit --audit-level=high
npm run typecheck
npx vitest run
```

---

### Task 3.2 — Run pip-audit and fix vulnerabilities

**Status:** `[ ]`
**Branch:** `fix/pip-audit`
**Files potentially edited:** `requirements.txt`

**What to implement:**
Install and run pip-audit:
```powershell
.venv\Scripts\pip.exe install pip-audit
.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```
For each vulnerability reported, update the affected package to the patched version in `requirements.txt` and reinstall.

**Constraints:**
- Do not upgrade packages to versions incompatible with Python 3.10
- Do not upgrade FastAPI to 1.x — the version constraint is `>=0.104,<1`
- Do not upgrade Pydantic to v3 if it exists
- Run pytest after each package update

**Acceptance:**
- `pip-audit -r requirements.txt` exits with code 0
- No vulnerabilities reported

**Verify:**
```powershell
.venv\Scripts\python.exe -m pip_audit -r requirements.txt
.venv\Scripts\python.exe -m pytest -q
```

---

### Task 3.3 — Add audit steps to CI pipeline

**Status:** `[ ]`
**Branch:** `fix/ci-dependency-audit`
**Files to edit:**
- `.github/workflows/ci.yml`

**What to implement:**
Add to the `frontend` job after the typecheck step:
```yaml
- run: npm audit --audit-level=high
  working-directory: frontend
```

Add to the `backend` job after the pytest step:
```yaml
- run: pip install pip-audit
- run: pip-audit -r requirements.txt
```

**Constraints:**
- Do not change Python version in CI (keep 3.10)
- Do not change Node version in CI (keep 20)
- Do not add new CI jobs — add steps to existing jobs

**Acceptance:**
- CI runs `npm audit` on frontend pushes
- CI runs `pip-audit` on backend pushes
- Both steps pass on current codebase

**Verify:**
Push to a branch and confirm CI passes. Or run locally:
```powershell
cd frontend && npm audit --audit-level=high
.venv\Scripts\python.exe -m pip_audit -r requirements.txt
```

---

## Phase 4 — Docker

---

### Task 4.1 — Write FastAPI Dockerfile

**Status:** `[ ]`
**Branch:** `feat/docker-backend`
**Files to create:**
- `Dockerfile` (root level, for FastAPI backend)

**What to implement:**
Multi-stage is optional — single stage is fine for demo. Requirements:
- Base: `python:3.10-slim`
- Working dir: `/app`
- Copy `requirements.txt` first (layer caching)
- Run `pip install --no-cache-dir -r requirements.txt`
- Copy rest of project
- Copy model artifacts: `COPY ml_model/model_registry/ ml_model/model_registry/`
- Expose port 8000
- CMD: `uvicorn web_app.presentation.app:create_app --host 0.0.0.0 --port 8000`
- Do NOT use `--reload` in the container CMD
- Do NOT copy `.env` into the image — env vars come from compose

**Constraints:**
- Python 3.10-slim base only
- No `--reload` flag
- Model artifacts must be in the image (not mounted)
- `.env` must not be copied

**Acceptance:**
- `docker build -t injection-backend .` succeeds
- Container starts without errors when given required env vars

**Verify:**
```powershell
docker build -t injection-backend .
```
Must exit 0.

---

### Task 4.2 — Write Next.js Dockerfile

**Status:** `[ ]`
**Branch:** `feat/docker-frontend`
**Files to create:**
- `frontend/Dockerfile`

**What to implement:**
Single stage, Node 20 alpine base:
- Base: `node:20-alpine`
- Working dir: `/app`
- Copy `package.json` and `package-lock.json` first
- Run `npm ci` (not `npm install`)
- Copy rest of frontend source
- Run `npm run build`
- Expose port 3000
- CMD: `node .next/standalone/server.js` or `npm start`
- Do NOT copy `.env.local` into the image

**Constraints:**
- Node 20 alpine only
- Use `npm ci` not `npm install`
- Build must run at image build time, not container start time
- `.env.local` must not be copied

**Acceptance:**
- `docker build -t injection-frontend ./frontend` succeeds
- Container starts and serves the Next.js app

**Verify:**
```powershell
docker build -t injection-frontend ./frontend
```
Must exit 0.

---

### Task 4.3 — Write docker-compose.yml

**Status:** `[ ]`
**Branch:** `feat/docker-compose`
**Files to create:**
- `docker-compose.yml` (root level)

**What to implement:**
Three services:

```
modsecurity:
  image: owasp/modsecurity-crs:nginx-alpine
  ports: ["80:80"]
  environment:
    BACKEND: http://backend:8000
    PARANOIA: 1
    ALLOWED_METHODS: GET POST PATCH
  depends_on: [backend]

backend:
  build: . (uses root Dockerfile)
  expose: [8000]          ← internal only, NOT ports
  env_file: .env
  depends_on: []

frontend:
  build: ./frontend
  ports: ["3000:3000"]
  env_file: frontend/.env.local
  environment:
    FASTAPI_BASE_URL: http://backend:8000
  depends_on: [backend]
```

**Critical:** `backend` must use `expose` not `ports` — it should NOT be reachable from the host directly. Only ModSecurity proxies to it on the internal network.

**Constraints:**
- Backend must not be exposed to host
- FASTAPI_BASE_URL in frontend must use the container service name `backend`
- PARANOIA must be 1
- Do not add Redis, volumes, or health checks in this task

**Acceptance:**
- `docker compose up --build` completes without error
- `curl http://localhost:80/health` returns healthy response
- `curl http://localhost:3000` returns the Next.js app
- `curl http://localhost:8000` fails — backend not directly accessible

**Verify:**
```powershell
docker compose up --build -d
curl http://localhost:80/health
curl http://localhost:3000
```

---

### Task 4.4 — Test full stack via Docker

**Status:** `[ ]`
**Branch:** `feat/docker-integration-test`

**What to implement:**
Run seed_demo.py against the Docker stack to verify the full triage pipeline works end-to-end:

```powershell
$env:API_SECRET_KEY = "your-key-here"
.venv\Scripts\python.exe seed_demo.py
```

Then verify alerts appear in Supabase.

**Acceptance:**
- seed_demo.py exits 0 with no errors
- New rows appear in Supabase `traffic_logs`
- Dashboard shows the new alerts
- ModSecurity logs show requests were processed
- A basic SQLi payload gets classified and blocked

**Verify:**
```powershell
.venv\Scripts\python.exe seed_demo.py
.venv\Scripts\python.exe -c "
import asyncio
from web_app.infrastructure.database import engine
import sqlalchemy
async def test():
    async with engine.begin() as conn:
        result = await conn.execute(sqlalchemy.text('SELECT COUNT(*) FROM traffic_logs'))
        print('Row count:', result.scalar())
asyncio.run(test())
"
```

---

## Phase 5 — Demo Prep

---

### Task 5.1 — Write smoke test runbook

**Status:** `[ ]`
**Branch:** `feat/smoke-test-runbook`
**Files to create:**
- `docs/project-ops/SMOKE_TEST_RUNBOOK.md`

**What to implement:**
A step-by-step runbook that verifies the system is working before a demo. Must cover:
- Starting the Docker stack
- Confirming all 3 containers are running
- Running seed_demo.py
- Verifying dashboard loads
- Verifying alerts page shows data
- Verifying ML health page shows model version and status
- Verifying triage status update works (change one alert to in_review)
- Confirming the change persists in Supabase

**Acceptance:**
- Runbook exists at the correct path
- A teammate with no context can follow it without asking questions
- All commands are copy-pasteable PowerShell

**Verify:**
Follow the runbook yourself once end-to-end and confirm it works.

---

### Task 5.2 — Write demo runbook

**Status:** `[ ]`
**Branch:** `feat/demo-runbook`
**Files to create:**
- `docs/project-ops/DEMO_RUNBOOK.md`

**What to implement:**
The panel-facing demo script. Must cover:
- Pre-demo checklist (stack running, data seeded, tunnel live)
- Opening the dashboard and what to say
- Walking through the alerts page and explaining confidence tiers
- Demonstrating a triage status update
- Showing the ML health page and explaining F1 score and calibration
- Panel Q&A answers for: Redis (deferred), ModSecurity (show compose file), RLS (enabled), false positive rate (point to dashboard metric)
- Cloudflare Tunnel command for remote panel access

**Acceptance:**
- Runbook exists at the correct path
- Demo can be delivered in under 10 minutes following the script
- Every likely panel question has a written answer

**Verify:**
Rehearse the demo once end-to-end.

---

## Completion Criteria — All Phases Done

```
[ ] All 18 tasks above are marked [x]
[ ] pytest -q passes (256+ tests)
[ ] npm run typecheck passes
[ ] npx vitest run passes (102+ tests)
[ ] docker compose up --build succeeds
[ ] seed_demo.py runs against Docker stack successfully
[ ] SECURITY_AUDIT.md findings are all resolved or documented as deferred
[ ] STATUS.md reflects final state
[ ] AGENTS.md intro accurately describes current infra state
```
