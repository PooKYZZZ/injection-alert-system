# Local Setup

Last updated: 2026-07-22

This guide reflects the repo as it exists now. It supports direct local development, a Docker-based CyberTrace smoke path, and a final realistic WAF demo path. Docker Compose and ModSecurity now exist in the repo. The dashboard browser boundary remains `Browser -> Next.js -> FastAPI`; the technical CyberTrace WAF proof path uses `localhost:8088`, and the realistic protected demo website path uses `localhost:8089` with the separate land-records portal built as the `demo-portal` service. PR2 SSE no-refresh and browser reconnect behavior are manually verified through the named hosted deployment; see `docs/project-ops/STATUS.md` for evidence and limitations.

PR #84 is frozen at trusted source correlation. Its code, migrations, CI,
controlled proof, hosted source-correlation proof, and restart/recreate proof
are complete. The separate PR2 SSE slice is implemented with automated and
manual no-refresh, browser-reconnect, and named-domain hosted proof. PR5 adds
local/test-only LOW/MEDIUM active enforcement for the protected portal route;
hosted/production enforcement remains off and HIGH/CRITICAL remain
non-disruptive. Current Telegram provider/hosted verification is recorded in
`docs/project-ops/STATUS.md`. Hosted source verification remains
`WAF_SOURCE_VERIFICATION_MODE=unverified` until the final Cloudflare/origin
trust checks are completed. See
`docs/project-ops/IMPLEMENTATION_GAP_REGISTER.md` for remaining PR5 and hosted
work.

Client-stated PD2 requirements are recorded in `docs/client-requirements.md`. The `CRITICAL >=90%` confidence tier, named-account/RBAC, TOTP MFA, recovery, password-reset, recent-step-up, protected notification outbox, and restricted break-glass boundaries are implemented behind explicit rollout switches and database roles. The hosted V6.1 migration, public Cloudflare deployment, Resend delivery, and live Admin authentication journey are verified; Turnstile hostname verification and the approved post-merge follow-ups remain separate work.

## Prerequisites

- Windows PowerShell
- Python 3.14+
- Node.js 24.x (the frontend and GitHub CI use the same major version)
- npm

## 1. Clone And Enter The Repo

```powershell
git clone <your-remote-url>
cd injection-alert-system
```

## 2. Backend Setup

### Create a virtual environment

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, either adjust execution policy for the current user or call the venv executables directly.

### Install Python dependencies

```powershell
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### Create `.env`

The backend currently reads settings from `.env`. For ordinary local development,
use a local or disposable PostgreSQL database (or SQLite where supported); do
not point `DATABASE_URL` at hosted Supabase. Hosted Supabase is for explicitly
authorized operator work documented in the runbooks. A minimal local development file looks like this:

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:<password>@<project-ref>.supabase.co:6543/postgres
APP_ENV=development
LOG_LEVEL=INFO
MODEL_PATH=ml_model/models/mock_model.py
MODEL_REGISTRY_PATH=
API_SECRET_KEY=local-dev-secret
WAF_INGEST_API_KEY=<different-generated-secret>
WAF_SOURCE_VERIFICATION_MODE=unverified
WAF_SOURCE_PROVENANCE_MODE=direct_remote_addr
ENFORCEMENT_MODE=off
ENFORCEMENT_CHECK_API_KEY=<different-generated-secret>
ENFORCEMENT_RECOMMENDATION_TTL_SECONDS=900
GROQ_API_KEY=
ALLOWED_ORIGINS=["http://localhost:3000"]
CONFIDENCE_LOW_THRESHOLD=0.50
CONFIDENCE_HIGH_THRESHOLD=0.80
STALE_PROCESSING_TIMEOUT_SECONDS=30
MAX_SEQ_LEN=128
TEMPERATURE=0.596868
```

Generate the two bearer keys independently; never copy one into the other:

```powershell
.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(32))"
```

Run that command twice and place each result only in `.env`. In production and
staging both keys are required, `WAF_INGEST_API_KEY` must be at least 32
characters, and it must differ from `API_SECRET_KEY`. The bridge uses the WAF
key only for `POST /api/internal/waf-events`; BFF calls and WAF transaction
lookup continue to use `API_SECRET_KEY`. If either key is exposed, replace it
manually and recreate the backend plus every affected bridge; no automatic key
rotation exists.

PR4 shadow enforcement is opt-in. Set `ENFORCEMENT_MODE=shadow` and provide a
third, independently generated `ENFORCEMENT_CHECK_API_KEY` (at least 32
characters and different from both existing backend keys). The backend records
only expiring recommendations for `/records/search`; the dedicated
`POST /api/internal/enforcement/check` endpoint and the separate portal
server-side client always fails open locally. A healthy backend evaluation
returns `{"decision":"ALLOW"}`; a backend lookup failure returns `503`, which
the portal treats as local `ALLOW`. This does not block, throttle, challenge,
or otherwise change a request.

PR5 active enforcement is a controlled local/test path only. The completed
controlled full-stack evidence is recorded in
`reports/active-enforcement/PR5_CONTROLLED_E2E_PROOF.md`. Keep the default
`ENFORCEMENT_MODE=off` for hosted and production environments. For a disposable
local environment, set `ENFORCEMENT_MODE=enforce`, provide the dedicated check
key, set `ENFORCEMENT_ALLOW_UNVERIFIED_SOURCE_FOR_TESTS=true` in both CyberTrace
and the portal, and configure Cloudflare's published test Turnstile credentials
with `ENFORCEMENT_TURNSTILE_TEST_MODE=true`. Set the portal check timeout to at
least 1000 ms and its challenge timeout above the backend Siteverify budget
(5000 ms for the current controlled defaults). Test mode and the source bypass
are rejected in staging/production. Real deployed ENFORCE additionally requires
`ENFORCEMENT_SOURCE_TRUST_MODE=cloudflare_verified`, which records completion of
the separate origin-isolation and proxy-header topology gate. LOW defaults to five
unchallenged requests per 60-second window; MEDIUM challenges immediately and
allows ten verified requests per 60-second window before returning
`THROTTLE` with `retry_after_seconds`. The portal applies these decisions only
to `/records/search`. Enforcement evaluation failures fail open; an invalid or
unavailable challenge remains unsatisfied and never creates a grant.

Active enforcement uses additive migration
`20260721_000024_add_active_enforcement_state.py`. It preserves PR4 SHADOW rows,
adds `enforcement_request_windows` and `enforcement_challenge_grants`, and does
not delete traffic logs on downgrade. Local/test proof belongs in
`reports/active-enforcement/`; it is not hosted readiness evidence.

The auth/security schema foundation also includes a frontend server-only
Supabase client. Put these values in `frontend/.env.local`:

```dotenv
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only-key>
```

Never use `NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY`. The service-role credential
bypasses RLS and must not enter browser code, bundles, logs, or committed files.
RLS on the new public-schema auth/security tables is defense-in-depth only.
Auth.js Credentials login and BFF session freshness checks now read
`auth_accounts` through the server-only client. `AUTH_USERS_JSON` is not a
runtime source or outage fallback.
The hosted migration has been completed through `20260712_000020` using a
reviewed deployment step. Do not rerun or downgrade the hosted database
casually; use `docs/project-ops/MIGRATION_ROLLBACK_RUNBOOK.md`.

The V6.1 account/MFA/recovery feature switches are documented in
`frontend/.env.example`; they fail closed when absent. Runtime values are read
at request time by the server-only frontend helper. The maintained operator
boundaries are `docs/SETUP.md`, `docs/architecture.md`, and
`docs/project-ops/SMOKE_TEST_RUNBOOK.md`.

Notes:

- `MODEL_PATH` still exists in config for compatibility.
- `MODEL_REGISTRY_PATH` controls the real runtime model service.
- If `MODEL_REGISTRY_PATH` is empty or missing in development, startup falls back to the mock model service with a warning.
- `CONFIDENCE_LOW_THRESHOLD`, `CONFIDENCE_HIGH_THRESHOLD`, and `STALE_PROCESSING_TIMEOUT_SECONDS` are supported env overrides with locked current defaults.
- `MAX_SEQ_LEN`, `TEMPERATURE`, `LABEL_NAMES`, and `MODEL_VERSION` are also accepted by settings, but the repo currently relies on their defaults unless you are doing targeted backend or artifact validation work.
- SQLite is still fine for isolated local testing, but it is no longer the primary runtime path documented for the app.
- If you want the real staged model, use an explicit run directory such as:

```dotenv
MODEL_REGISTRY_PATH=ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755
```

### Promote the staged DistilBERT artifact safely

Use the promotion CLI to replace the active staged artifact via archive-and-recreate while preserving the active path name.

Dry-run first:

```powershell
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run ^
  --source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" ^
  --active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" ^
  --archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" ^
  --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" ^
  --archive-suffix "pre_20260420" ^
  --dry-run
```

Real promotion (remove `--dry-run`):

```powershell
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run ^
  --source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" ^
  --active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" ^
  --archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" ^
  --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" ^
  --archive-suffix "pre_20260420"
```

This workflow reads checkpoint payloads with `torch.load(..., weights_only=True)`,
writes sidecar provenance files (`provenance.json`, `MODEL_CARD.md`), and does
not rename the active staged run directory. Packaging plus local reload sets
`artifact_packaging_ready`; it does not set `ready_for_promotion=true` unless a
separate configured quality gate also passes. No such quality threshold gate is
currently configured, so operators must not treat packaging success as model
quality approval.

### Run tests

```powershell
.venv\Scripts\python.exe -m pytest -q
```

Do not copy historical test counts from this setup guide; rerun the repository
commands for current totals. Current release evidence is summarized in
`docs/project-ops/STATUS.md`.

### Start the backend

```powershell
.venv\Scripts\python.exe -m uvicorn web_app.presentation.app:create_app --reload
```

Backend entrypoint:

- `http://localhost:8000/health`
- `http://localhost:8000/api/health`

Current API surface:

- Protected by backend bearer auth:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `PATCH /api/alerts/{id}/triage`
  - `GET /api/stats`
  - `GET /api/ml-health`
- Internal bearer-token protected backend endpoints:
  - `POST /api/feedback`
- Public backend endpoints:
  - `GET /health`
  - `GET /api/health`

## 3. Frontend Setup

### Install dependencies

```powershell
node --version
npm --version
cd frontend
npm install
```

The repository pins Node 24 in `.nvmrc`, `.node-version`, and
`frontend/package.json`. Activate Node 24 before installing frontend
dependencies, especially the native `argon2` package.

### Create `frontend/.env.local`

Use a local file with the variables the current frontend actually reads:

```dotenv
AUTH_SECRET=replace-me
AUTH_TRUST_HOST=true
AUTH_APP_ORIGIN=https://<public-app-domain>
AUTH_ACCOUNT_MANAGEMENT_ENABLED=false
AUTH_MFA_ENROLLMENT_ENABLED=false
AUTH_EMAIL_RECOVERY_ENABLED=false
AUTH_PASSWORD_RESET_ENABLED=false
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only-key>
FASTAPI_BASE_URL=http://localhost:8000
INTERNAL_API_KEY=local-dev-secret
USE_MOCK_API=false
NEXT_PUBLIC_APP_ENV=development
NEXT_PUBLIC_APP_VERSION=0.0.0-LOCAL
```

Notes:

- `AUTH_SECRET` is the Auth.js signing secret. Keep `NEXTAUTH_SECRET` unset to avoid split secret sources.
- `AUTH_APP_ORIGIN` must match the public application origin used by Auth.js redirects.
- `AUTH_TRUST_HOST=true` is required for local `next start` validation so Auth.js trusts the local host.
- `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` are required for login and protected BFF access. Missing configuration or a Supabase outage fails closed; there is no `AUTH_USERS_JSON` fallback.
- At least one `auth_accounts` row with an approved Argon2id `password_hash` must exist before login can succeed. Runtime verification requires PHC version `v=19` with at least `m=19456,t=2,p=1`; weak, null, old scrypt/bcrypt, malformed, and unsupported hashes are rejected before native verification.
- The login form accepts account id, normalized email, or normalized username plus password. There is no demo-password fallback.
- Disablement, `mfa_required`, role changes, and `authz_version` changes are checked against the current DB row on every protected BFF request. Existing JWTs are denied when the account is missing, disabled, newly MFA-required, downgraded, or stale.
- Assured MFA sessions retain an eight-hour Auth.js maximum. Password-level MFA sessions are additionally bounded by the database challenge expiry and cannot reach the dashboard. This is not an AAL2 compliance claim.
- Local login hardening uses per-identifier failure throttles with bounded expiry/size pruning plus a default two-operation password-hash concurrency cap. There is no process-wide denial counter. Defaults can be overridden with the `AUTH_LOGIN_*` and `AUTH_PASSWORD_HASH_CONCURRENCY_LIMIT` variables.
- Operational account provisioning uses `frontend/lib/server/db/script-client.mjs`; app runtime access remains protected separately by the `server-only` TypeScript client. Scripts load `frontend/.env.local` when run from `frontend/`, with explicitly supplied shell variables taking precedence, and errors name missing variables without printing values. The scripts create, list, disable, and set passwords without exposing secret-bearing fields.
- Throttle state is process memory only: it resets on restart and is not shared across serverless instances, Node processes, or horizontally scaled containers. It does not use IP or `X-Forwarded-For`.
- Login audit events are single-line JSON logs with hashed identifiers and fixed reason codes. They are operational logs, not a persistent or tamper-resistant audit store.
- `INTERNAL_API_KEY` must match backend `API_SECRET_KEY` for BFF-to-FastAPI requests.
- `USE_MOCK_API` is the only server-side mock toggle for alerts, alert detail, triage, stats, and ML health.
- Keep backend-only values unprefixed. Do not add `NEXT_PUBLIC_` to server-only secrets.
- Runtime feature flags are server-only availability controls. They are injected when the frontend container starts, are not Docker build arguments, and are evaluated per request. Recreate or restart the container after changing them.
- TOTP MFA enrollment/login, backup/email recovery, password reset, and recent-TOTP step-up are implemented behind `AUTH_MFA_ENROLLMENT_ENABLED`, `AUTH_EMAIL_RECOVERY_ENABLED`, and `AUTH_PASSWORD_RESET_ENABLED`. Missing values fail closed; runtime changes require container recreation or restart. Turnstile has a server-side verification boundary but no enabled production widget/hostname configuration.
- Accounts with `mfa_required=true` enter the password-level pre-auth flow and cannot reach the dashboard until final TOTP completion; recovery-level sessions are routed to mandatory enrollment.
- The repository migration head is `20260728_000025`. The latest hosted Supabase
  revision with recorded evidence is `20260712_000020`. Hosted and repository
  revisions are separate facts.
- Hosted migration state is only confirmed through `20260712_000020`; the
  source-verification migration is not claimed as hosted until a reviewed
  deployment proves it. Application
  functions remain purpose-bound and server-only; the restricted break-glass
  function is executable only through `cybertrace_break_glass`, not
  `service_role`.
- The notification worker is channel-aware for email and Telegram, claims one
  job per poll by default, reconciles expired leases/deadlines, cancels
  superseded jobs, decrypts protected credential payloads only at email
  delivery, and scrubs terminal payloads. Telegram is restricted by the
  database to `threat_detected` jobs and cannot carry password, MFA, or account
  notifications.

### Telegram threat notifications

Telegram is a secondary notification channel for persisted non-Normal `HIGH`
and `CRITICAL` confidence-tier alerts. Configure server-only values:

Notification links use the dashboard-neutral alert review contract
`/alerts?alert_id=<id>`. The existing Alerts workspace validates the identifier,
fetches detail through the authenticated Next.js BFF, and opens the existing
drawer without implicitly changing triage state. Closing the drawer removes
only `alert_id` while preserving other alert filters.

```dotenv
THREAT_TELEGRAM_ENABLED=false
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=
TELEGRAM_LIVE_TEST_ENABLED=false
```

Disabled or incomplete configuration does not stop the backend and does not
affect alert persistence, SSE, dashboard visibility, or existing email. The
worker uses Telegram Bot API `sendMessage` through HTTPX with bounded retries;
429 responses honor a bounded `retry_after`. Ambiguous delivery is not blindly
retried because Telegram provides no general idempotency key. The database
prevents duplicate jobs, but the project does not claim exactly-once external
delivery. Telegram messages intentionally omit source IP, query/body content,
headers, cookies, and credentials.

### Manual PR 3 auth cutover and rollback

Do not mutate live Supabase as part of normal app startup or automated tests.
For each target environment:

1. Apply migration `20260704_000008` through a reviewed deployment step.
2. Create at least one account with `frontend/scripts/create_auth_account.mjs`.
   For the temporary pre-MFA demo path, pass `--mfa-required false`.
3. Verify login locally or in staging, then verify set-password and disable
   behavior on a non-primary test account.
4. Keep a secure pre-cutover `AUTH_USERS_JSON` export only as rollback
   material. Rollback requires reverting the cutover code before restoring that
   env value; the PR 3 runtime never reads it. Keep the auth tables intact
   unless separately reviewed data recovery requires otherwise.

Example from `frontend/`:

```powershell
node scripts/create_auth_account.mjs --email admin@example.test --name "SOC Admin" --role ADMIN --password "<temporary-password>" --mfa-required false
node scripts/set_auth_account_password.mjs --email admin@example.test --password "<replacement-password>"
node scripts/disable_auth_account.mjs --email disposable-check@example.test
```

Password CLI arguments can enter shell history. Use only an appropriate local
operator shell and never commit or paste credentials into logs or reports.

### Validate migrations without touching live Supabase

Use a disposable PostgreSQL database, then exercise the normal migration chain:

```powershell
$env:DATABASE_URL = "postgresql+psycopg://<user>:<password>@127.0.0.1:<port>/<disposable-db>"
$env:CYBERTRACE_POSTGRES_TEST_URL = $env:DATABASE_URL
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m pytest -q tests/integration
.venv\Scripts\python.exe -m pytest -q tests/migrations
.venv\Scripts\python.exe -m alembic downgrade 20260715_000021
.venv\Scripts\python.exe -m alembic upgrade head
.venv\Scripts\python.exe -m alembic heads
.venv\Scripts\python.exe -m alembic current
```

The repository has exactly one current head, `20260728_000025`. Use
`alembic heads`, `alembic current`, and `alembic history` before any migration
downgrade or upgrade; the exact rollback decision belongs in
[`MIGRATION_ROLLBACK_RUNBOOK.md`](project-ops/MIGRATION_ROLLBACK_RUNBOOK.md).
Do not choose a downgrade target from this setup guide. Follow
[`MIGRATION_ROLLBACK_RUNBOOK.md`](project-ops/MIGRATION_ROLLBACK_RUNBOOK.md) for
reviewed downgrade/re-upgrade testing. Hosted Supabase is confirmed only through
`20260712_000020`; do not infer that the repository head has been deployed
there. Revision `20260704_000008` is intentionally part of normal `upgrade head`.
It creates nine auth/security tables, enables RLS, revokes public-role access,
and creates no browser-facing policies. Revision `20260324_000007` now fails
clearly if its required `traffic_logs` table is missing instead of silently
reporting success. Use a reviewed deployment step for live Supabase.

For current feature enablement, notification-key, recovery, and restricted
break-glass operations, follow this guide together with
[`project-ops/MIGRATION_ROLLBACK_RUNBOOK.md`](project-ops/MIGRATION_ROLLBACK_RUNBOOK.md)
and [`project-ops/SMOKE_TEST_RUNBOOK.md`](project-ops/SMOKE_TEST_RUNBOOK.md).

### Run the disposable authentication browser project

```powershell
cd frontend
npm run test:e2e:auth
```

The managed command creates and migrates unique PostgreSQL/PostgREST resources,
runs only the five critical Chromium journeys, and always removes them. It does
not require static E2E credentials or a hosted project. CI runs the same command.

### Dashboard role matrix

| Role | Read alerts/stats/ML health | Triage alerts | Update `action_taken` |
|---|---:|---:|---:|
| `VIEWER` | Yes | No | No |
| `ANALYST` | Yes | Yes | No |
| `ADMIN` | Yes | Yes | Yes |

The BFF route guards are the authorization authority. This SOC-team console does not implement per-alert ownership or tenant scoping.

### Start the frontend

```powershell
cd frontend
npm run dev
```

### Validate types and lint

```powershell
cd frontend
npm run lint
npm run typecheck
```

As of 2026-07-03, both pass cleanly.

### Run focused frontend BFF tests

```powershell
cd frontend
npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts
```

### Run full frontend test suite

```powershell
cd frontend
npx vitest run
```

The current verified counts are recorded in `docs/project-ops/STATUS.md` and
`docs/project-ops/LIVING_CHECKLIST.md`; run the commands above to verify the
current checkout rather than relying on a stale embedded count.

### Validate production build

```powershell
cd frontend
npm run build
```

## 4. Current Frontend Data Reality

Be explicit about the current BFF status:

- `/api/stats`
  - Wired through `frontend/lib/bff-client.ts`
  - Calls real FastAPI in non-mock mode
- `/api/alerts`
  - Wired through `frontend/lib/bff-client.ts`
  - Calls real FastAPI in non-mock mode
- `/api/alerts/[id]`
  - Wired through `frontend/lib/bff-client.ts`
  - Calls real FastAPI in non-mock mode
- `/api/alerts/[id]/triage` (PATCH)
  - Wired through `frontend/app/api/alerts/[id]/triage/route.ts`
  - Calls real FastAPI in non-mock mode
- `/api/ml-health`
  - Wired through `frontend/lib/bff-client.ts`
  - Calls real FastAPI in non-mock mode

So the current local dashboard can run fully against the backend, with optional centralized mock mode via `USE_MOCK_API=true`.

**Current state:** `USE_MOCK_API=false` - the dashboard is hitting the real FastAPI backend.

### Current frontend protection split

- `/login` is the public sign-in page.
- `/` redirects to `/login` or `/dashboard` based on session state.
- `frontend/app/(dashboard)/layout.tsx` protects the dashboard route group with a session check plus the central DB-backed freshness guard.
- `frontend/proxy.ts` additionally matches `/dashboard`, `/alerts`, and `/ml-health`.
- All seven BFF handlers validate the session, current DB account, disablement, role, and per-account `authz_version`; they return generic `401`/`403` responses before calling FastAPI when denied.

## 5. What This Setup Does Not Cover

The following are not yet available as runnable repo-level setup paths:

- Production-grade ModSecurity-fronted deployment
- Redis-backed review queue or enforcement state
- Richer backend-native dashboard stats and ML-health payloads beyond the current BFF normalization layer
- Automatic repo-managed export of Supabase policies and operational guardrails
- Production-grade ModSecurity-fronted deployment, Turnstile widget/hostname rollout, managed identity, and distributed login throttling
- Notification failure/retry operational testing, MFA flag-semantics audit, and Auth.js/passkey follow-ups

## 5A. Docker Smoke Setup

### Required files

- Root `.env`
- `frontend/.env.local`

Those files are mounted into the containers via `docker-compose.yml`.

### Start the stack

```powershell
docker compose --profile technical-waf up --build -d
docker compose ps
```

Expected services:

- `frontend`
- `backend`
- `modsecurity`
- `bridge`

Without `--profile technical-waf`, normal Compose starts only `frontend` and
`backend`; the historical `8088` WAF pair is now explicitly opt-in.

### Current Docker network truth

- `frontend` is published on `http://localhost:3000`
- `modsecurity` publishes the WAF proof path on `http://localhost:8088`
- `backend` is internal only and should show `8000/tcp`
- `frontend` talks to `backend` using `FASTAPI_BASE_URL=http://backend:8000`
- `modsecurity` proxies to `backend` using `BACKEND=http://backend:8000`

This means:

- Browser path today: `Browser -> frontend -> backend`
- WAF proof path today: `localhost:8088 -> modsecurity -> backend`
- Backend transaction lookup proof: `docker compose exec backend ...`

Do not use `localhost:8000` for Docker proof unless backend port 8000 is explicitly published.

### Final realistic demo-target stack

For normal developer startup, the demo-target profile is not required. For the final realistic WAF demonstration, start this repo with the demo-target profile:

```powershell
docker compose -f docker-compose.yml -f docker-compose.demo-target.yml --profile demo-target up -d --build
```

By default, the profile builds the protected demo website from the sibling path `../../land-records-portal`, which resolves to `G:\AI\land-records-portal` from this repo layout. If your portal checkout is elsewhere, set `DEMO_PORTAL_CONTEXT` before running Compose.

Expected path:

```text
localhost:8089
-> demo-target-modsecurity
-> demo-portal on the Compose network port 3010
-> logs/modsecurity/demo-target/modsec_audit.jsonl
-> demo-target-bridge
-> FastAPI internal WAF ingest
-> ML triage
-> dashboard/backend lookup
```

The land-records-portal source stays separate from this repository. This repo's Compose override references it as a build context; it does not merge the portal source into CyberTrace. The portal runs as a production Next.js standalone container with `HOSTNAME=0.0.0.0` and `PORT=3010`, and port `3010` is internal to the Compose network unless explicitly changed for debugging. `demo-target-bridge` is required when `8089` events must appear in CyberTrace.

Latest verified local proof: `/records/search` SQLi marker `SMOKE002945` returned HTTP 403 through `localhost:8089`; `demo-target-bridge` posted transaction `178249138618.813428`; backend lookup returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, and `crs_score=15`.

For hosted rendering, first observe the actual narrow tunnel peer or subnet;
do not guess it. Store the observed value in the ignored root `.env`, not only
in a temporary PowerShell session:

```dotenv
HOSTED_WAF_TRUSTED_PEER=<observed-narrow-peer-or-subnet>
WAF_SOURCE_VERIFICATION_MODE=unverified
```

Use the hosted launcher so the persistent file is loaded and validated on every
recreate:

```powershell
pwsh -NoProfile -File scripts/start_hosted_target.ps1 -ValidateOnly
pwsh -NoProfile -File scripts/start_hosted_target.ps1 -Build
```

The launcher fails if the peer is missing, malformed, broad, or if hosted mode
is anything other than `unverified`. The resolved topology must contain one
realistic WAF/bridge pair, no `8088`, and exactly one loopback
`127.0.0.1:8089:8080` binding. Source correlation and restart/recreate proof
are complete. Do not switch to `cloudflare_tunnel` until Workers, Pseudo IPv4,
direct-origin isolation, and the immediate tunnel-side peer are independently
proved. Current hosted identity verification status is Partial; mode remains
`unverified`.

### Backend health checks in Docker

The backend image does not include `curl`, so use Python from inside the container:

```powershell
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/health').status)"
docker compose exec backend python -c "import urllib.request; print(urllib.request.urlopen('http://localhost:8000/api/health').status)"
```

### Verified WAF proof flow

Use these commands for the ModSecurity/OWASP CRS proof path:

```powershell
Invoke-WebRequest -UseBasicParsing "http://localhost:8088/healthz"
Invoke-WebRequest -UseBasicParsing "http://localhost:8088/api/health"
Invoke-WebRequest -UseBasicParsing -SkipHttpErrorCheck "http://localhost:8088/api/health?id=17%27%20OR%2017%3D17--"
```

Expected proof result:

- `/healthz` through `localhost:8088` returns HTTP 200.
- `/api/health` through `localhost:8088` returns HTTP 200.
- SQLi probe through `localhost:8088` returns HTTP 403.
- ModSecurity writes JSON audit evidence to `logs/modsecurity/modsec_audit.jsonl`.
- The bridge posts to `http://backend:8000/api/internal/waf-events`.

Backend transaction lookup is Docker-internal:

```powershell
$txid = "<paste transaction.unique_id>"
if ([string]::IsNullOrWhiteSpace($txid)) { throw "txid missing" }
docker compose exec -e TXID=$txid backend python -c "import os, urllib.request; txid=os.environ['TXID']; secret=os.environ['API_SECRET_KEY']; req=urllib.request.Request(f'http://127.0.0.1:8000/api/internal/waf-events/{txid}', headers={'Authorization': 'Bearer ' + secret}); print(urllib.request.urlopen(req).read().decode())"
```

Verified result for transaction `17821639659.909603`: `found=true`, `prediction=SQL Injection`, `confidence_level=HIGH`, `action_taken=BLOCKED`, `source_ip=172.21.0.1`, `request_path=/api/health`, URL-encoded `query_string`, `crs_score=5`, and rules `942100`, `949110`.

### Frontend smoke check

```powershell
Invoke-WebRequest -UseBasicParsing http://localhost:3000 | Select-Object -ExpandProperty StatusCode
```

Expected result: `200`

### Public Cloudflare Tunnel verification

The verified public deployment uses a Cloudflare Tunnel in the deployment
environment. Start the tunnel using the operator-managed tunnel configuration;
do not commit the tunnel token or credentials:

```powershell
cloudflared tunnel run <tunnel-name>
```

Verify the public application and protected target separately:

```powershell
Invoke-WebRequest -UseBasicParsing https://app.cybertracesystems.com | Select-Object -ExpandProperty StatusCode
Invoke-WebRequest -UseBasicParsing https://target.cybertracesystems.com | Select-Object -ExpandProperty StatusCode
```

Expected result: the application domain is publicly reachable and the target
domain is challenged by Cloudflare Access for identities without access. The
frontend runtime flags are injected at container start, not at image build
time. After changing them, run `docker compose up -d --force-recreate frontend`
and verify the value inside the recreated container.

### Demo data

No maintained `seed_demo.py` exists in this repository. Use the WAF smoke
commands and account provisioning scripts documented above; do not rely on
stale seeder commands.

### Stop the stack

```powershell
docker compose down
```

## 6. Troubleshooting

### Backend starts with a mock model unexpectedly

- Check `MODEL_REGISTRY_PATH`
- In development, a missing path falls back to mock mode
- In production mode, a missing path raises at startup

### Frontend cannot reach backend

- Check `FASTAPI_BASE_URL`
- Check that `INTERNAL_API_KEY` matches backend `API_SECRET_KEY`
- If you intentionally want UI-only local work, set `USE_MOCK_API=true`
- Make sure the backend is running before starting full-stack local work

### Typecheck or test results differ from this doc

Re-run:

```powershell
.venv\Scripts\python.exe -m pytest -q
cd frontend
npm run lint
npm run typecheck
npx vitest run
npm run build
```

If those outputs change, update this file and `docs/CONTEXT.md` in the same change.
