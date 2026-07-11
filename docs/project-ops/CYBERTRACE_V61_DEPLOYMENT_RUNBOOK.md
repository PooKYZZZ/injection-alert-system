# CyberTrace V6.1 Deployment Runbook

This runbook records the implemented boundary and the remaining human/deployment gates. The repository is still a thesis-sized local Compose and hosted-Supabase runtime; it is not a Kubernetes or production-SIEM deployment.

The current additive migration head is `20260711_000018`. PR #83 keeps all
V6.1 feature switches disabled until the target migration, provider,
payload-protection, and browser gates are reviewed.

## Required server-only configuration

Set these only in ignored server-side environment stores:

```dotenv
AUTH_SECRET=<random Auth.js secret>
AUTH_APP_ORIGIN=https://<dashboard-host>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only service-role key>
AUTH_MFA_ENCRYPTION_KEY=<base64 32-byte AES-GCM key>
AUTH_EMAIL_OTP_KEY=<dedicated 32+ byte OTP HMAC key>
NOTIFICATION_WORKER_ENABLED=false
NOTIFICATION_WORKER_REQUIRED=false
NOTIFICATION_WORKER_BATCH_SIZE=1
EMAIL_PROVIDER=fake
RESEND_API_KEY=<server-only provider key when approved>
RESEND_FROM_EMAIL=<verified sender when approved>
```

Never use `NEXT_PUBLIC_SUPABASE_SERVICE_ROLE_KEY`. Do not print, paste, or commit any value above.

Keep these rollout switches disabled until the corresponding external checks are complete:

```dotenv
AUTH_ACCOUNT_MANAGEMENT_ENABLED=false
AUTH_MFA_ENROLLMENT_ENABLED=false
AUTH_EMAIL_RECOVERY_ENABLED=false
AUTH_PASSWORD_RESET_ENABLED=false
AUTH_TURNSTILE_ENABLED=false
```

The worker is email-only and claims one job per poll by default. Staging and
production reject `EMAIL_PROVIDER=fake` when the worker is enabled; a required
worker also performs a startup database probe. Terminal outbox rows are
scrubbed, but pending credential payload encryption still requires a separate
security approval before security-email enablement. No live Resend smoke was
performed in this remediation.

## Migration gate

1. Prove a disposable PostgreSQL target and set `DATABASE_URL` only in that shell.
2. Run `.venv\Scripts\python.exe -m alembic upgrade head`.
3. Run the migration source tests and PostgreSQL integration suites.
4. Run `.venv\Scripts\python.exe -m alembic downgrade 20260710_000014` followed by `upgrade head` to verify clean rollback/re-upgrade of the PR #83 revisions.
5. A hosted Supabase migration requires a separate reviewed deployment approval; this agent has not applied migrations to production.

## Frontend validation

Use the pinned Node 24 runtime and run:

```powershell
cd frontend
npm run lint
npm run typecheck
npx vitest run --pool=threads
npm run build
```

The browser boundary remains `Browser -> Next.js/Auth.js -> server-only Supabase/RPC -> FastAPI BFF`; the browser never calls FastAPI or receives service-role credentials. The five required journeys are defined in `frontend/e2e/auth-journeys.spec.ts`; execute them only with installed Playwright browsers and a disposable seeded Supabase-backed app environment.

## Security boundaries and remaining limitations

- MFA completion, recovery, enrollment, and recent step-up purposes are
  isolated by database functions; Auth.js does not infer assurance from a
  client-controlled field.
- Backup-code recovery requires a password-bearing privileged account and an
  unused backup code, then forces TOTP enrollment. Live email verification is
  not required for that path.
- The operator reset function is a high-privilege service-role helper with
  exact confirmation and audit logging. It is not an isolated database role;
  provision a separate operational role before calling it a production
  break-glass control.
- Next.js and FastAPI must be checked against the same intended PostgreSQL
  target at deployment time; this repository does not apply hosted migrations
  automatically.

## Public edge and smoke checks

- Local WAF proof uses `http://localhost:8088`; backend port 8000 is internal-only in Compose.
- Optional demo-target proof uses `http://localhost:8089`.
- Use the existing bounded final-demo smoke harness for live local proof and require current-marker backend correlation.
- Deployed use requires HTTPS, exact Auth.js origin, secure `__Host-` cookies, verified email/provider configuration, and Turnstile hostname validation.

## Rollback

Disable the feature switches and worker first, preserve account/security-event
and outbox history, then roll back application code before any reviewed schema
downgrade. A clean downgrade from `20260711_000018` to `20260710_000014` is
validated only before new terminal outbox states or live auth challenges are
written; after rollout, prefer a forward migration. Do not restore
`AUTH_USERS_JSON` or another weaker authentication path. Rotate/revoke any
exposed provider or service credentials immediately.
