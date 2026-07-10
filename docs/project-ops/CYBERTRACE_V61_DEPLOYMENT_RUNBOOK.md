# CyberTrace V6.1 Deployment Runbook

This runbook records the implemented boundary and the remaining human/deployment gates. The repository is still a thesis-sized local Compose and hosted-Supabase runtime; it is not a Kubernetes or production-SIEM deployment.

## Required server-only configuration

Set these only in ignored server-side environment stores:

```dotenv
AUTH_SECRET=<random Auth.js secret>
AUTH_APP_ORIGIN=https://<dashboard-host>
SUPABASE_URL=https://<project-ref>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<server-only service-role key>
AUTH_MFA_ENCRYPTION_KEY=<base64 32-byte AES-GCM key>
AUTH_EMAIL_OTP_KEY=<dedicated 32+ byte OTP HMAC key>
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

Unit 1 Resend remains fake-provider/default-off unless the guarded smoke command is explicitly enabled for the approved recipient `froilangayaom@gmail.com`.

## Migration gate

1. Prove a disposable PostgreSQL target and set `DATABASE_URL` only in that shell.
2. Run `.venv\Scripts\python.exe -m alembic upgrade head`.
3. Run the migration source tests and PostgreSQL integration suites.
4. Run `.venv\Scripts\python.exe -m alembic downgrade 20260710_000013` followed by `upgrade head` to verify rollback/re-upgrade.
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

The browser boundary remains `Browser -> Next.js/Auth.js -> server-only Supabase/RPC -> FastAPI BFF`; the browser never calls FastAPI or receives service-role credentials.

## Public edge and smoke checks

- Local WAF proof uses `http://localhost:8088`; backend port 8000 is internal-only in Compose.
- Optional demo-target proof uses `http://localhost:8089`.
- Use the existing bounded final-demo smoke harness for live local proof and require current-marker backend correlation.
- Deployed use requires HTTPS, exact Auth.js origin, secure `__Host-` cookies, verified email/provider configuration, and Turnstile hostname validation.

## Rollback

Disable the feature switches first, preserve account/security-event data, then downgrade only after a reviewed rollback decision. Do not restore `AUTH_USERS_JSON` or another weaker authentication path. Rotate/revoke any exposed provider or service credentials immediately.
