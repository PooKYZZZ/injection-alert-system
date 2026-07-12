# CyberTrace V6.1 Deployment Runbook

This runbook records the implemented boundary and the remaining human/deployment gates. The repository is still a thesis-sized local Compose and hosted-Supabase runtime; it is not a Kubernetes or production-SIEM deployment.

The current additive migration head is `20260711_000019`. PR #83 keeps all
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
NOTIFICATION_PAYLOAD_ENCRYPTION_KEY=<dedicated base64 or hex 32-byte AES-GCM key>
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
worker also performs a startup database probe. Pending setup, reset,
verification, and email-recovery values are stored as versioned AES-256-GCM
envelopes. Next.js encrypts before the atomic producer RPC, and the Python
worker decrypts only immediately before template rendering. The same dedicated
key must be present in both server runtimes; it must not be reused for TOTP or
OTP hashing. An enabled worker fails configuration validation when the key is
missing or malformed. Terminal outbox rows remain scrubbed. No live Resend
smoke was performed in this remediation.

## Migration gate

1. Prove a disposable PostgreSQL target and set `DATABASE_URL` only in that shell.
2. Run `.venv\Scripts\python.exe -m alembic upgrade head`.
3. Run the migration source tests and PostgreSQL integration suites.
4. Run `.venv\Scripts\python.exe -m alembic downgrade 20260710_000014` followed by `upgrade head` to verify clean rollback/re-upgrade of the PR #83 revisions.
5. A hosted Supabase migration requires a separate reviewed deployment approval; this agent has not applied migrations to production.

Migration `20260711_000019` intentionally stops when an active
credential-equivalent outbox row still contains plaintext. Before a hosted
upgrade, inventory only `pending`, `leased`, and `retry_wait` rows for
`password_setup`, `password_reset`, `email_verification`, and
`email_recovery_otp`. Do not copy their payloads into tickets or logs. A
reviewed operator must either let the old worker finish them, terminalize them,
or reissue them through the protected producer before rerunning the migration.
The migration does not silently encrypt legacy rows because deployment may not
possess the original application key and nonce context.

## Hosted readiness checklist (approval required)

This checklist is preparation only. Completing it requires an authorized human
deployment window and is not evidence that this repository changed a hosted
project.

- [ ] Record the intended Supabase project reference without credentials and
  independently confirm both Next.js `SUPABASE_URL` and FastAPI `DATABASE_URL`
  resolve to that same project.
- [ ] Confirm the migration identity is the approved database owner and that
  `anon`, `authenticated`, and `service_role` are the intended target roles.
- [ ] Inventory active legacy secret-bearing outbox rows using counts and IDs
  only; complete the reviewed remediation gate above before `000019`.
- [ ] Generate a dedicated notification payload key in the approved secret
  manager, deploy the identical value to Next.js and the worker, and record key
  version `1` without recording the key itself.
- [ ] Apply migrations through `20260711_000019`, then verify the single
  Alembic head, protected RPC execute grants, plaintext rejection, and terminal
  scrub behavior.
- [ ] Confirm Auth.js callback/origin values, HTTPS, secure cookies, provider
  sender/domain verification, and the explicitly approved smoke recipient.
- [ ] Keep auth feature switches and both worker switches disabled while
  running readiness, health-detail, and database-role checks.
- [ ] With separate approval, enable one bounded staging producer path and the
  worker, send one controlled email, verify delivery plus durable completion,
  then confirm the terminal payload is `{}` and logs contain no URL, OTP,
  token, recipient, envelope, or key material.
- [ ] Review ambiguous-delivery events by outbox ID and provider message ID;
  never issue an unkeyed resend.
- [ ] Record rollback ownership: disable producers and worker first, then
  prefer a forward fix after any protected row exists. Downgrade `000019` only
  when its active-row gate passes and key/version compatibility is understood.

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
downgrade. A clean downgrade from `20260711_000019` to `20260710_000014` is
validated only before new terminal outbox states or live auth challenges are
written; after rollout, prefer a forward migration. Do not restore
`AUTH_USERS_JSON` or another weaker authentication path. Rotate/revoke any
exposed provider or service credentials immediately.
