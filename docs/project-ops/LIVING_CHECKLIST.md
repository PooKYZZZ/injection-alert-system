# Living Checklist
> Location: `docs/project-ops/LIVING_CHECKLIST.md`
> Keep this file updated after every meaningful implementation or verification session.
> This is a working checklist, not the full runtime source of truth.

**Last updated:** 2026-07-05

Status note:
- Current test baseline: pytest 496 passed, vitest 317 passed, typecheck passed, lint passed, build passed
- Current source-of-truth runtime docs are `docs/CONTEXT.md`, `docs/architecture.md`, and `docs/SETUP.md`
- ModSecurity audit-log handling policy is documented in `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`
- Client requirements are tracked in `docs/client-requirements.md`
- Confidence-tier naming is clarified in code/docs: `confidence_tier` is the preferred filter name, legacy `severity` remains a compatibility alias, current tiers remain `LOW`/`MEDIUM`/`HIGH`/`CRITICAL`, and `CRITICAL >=90%` is implemented as the confidence threshold
- Frontend confidence semantics are aligned: persisted-alert grouping/styling uses `confidence_level`; enforcement-policy counts exclude Normal predictions; Normal remains `ALLOWED` for every valid tier; tier badges always display the canonical tier
- Alerts UI role affordances are implemented for dense alert rows and detail views: viewers are read-only, analysts keep triage controls, and admins keep the full control set
- DistilBERT staged promotion now uses `ml_model/export/promote_final_training_run.py` with archive-and-recreate safety
- Real promotion command currently fails closed on strict head-shape mismatch between final-training checkpoint and `package_serving_artifact.py` loader expectations; rollback restoration behavior is verified
- Local WAF ingest proof is verified in `reports/modsecurity-live-proof/e2e-proof.md`: WAF path `localhost:8088`, SQLi HTTP 403, JSON audit log, bridge `status=200`, backend lookup `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `source_ip`, `request_path`, URL-encoded `query_string`, `crs_score=5`, and rules `942100`, `949110`
- Realistic demo-target WAF proof is verified locally through `localhost:8089`: marker `SMOKE002945` returned HTTP 403, `demo-target-bridge` posted transaction `178249138618.813428`, and backend lookup returned `found=true`, `/records/search`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `crs_score=15`
- Dashboard screenshot evidence is verified in `reports/modsecurity-live-proof/dashboard-evidence.md` with PNGs under `reports/modsecurity-live-proof/screenshots/`; the latest set includes `8089` dashboard/table evidence and an ML health overview, while the detail drawer screenshots show the default `8088` path
- Request/trace context, structured JSON logs for request/WAF/prediction boundaries, bridge JSON logs, and recursive log-field redaction are implemented and covered by targeted backend tests
- Final-demo automation is checked in at `scripts/run_final_demo_smoke.py` with
  deterministic Docker-free tests; live `8088`/`8089` modes remain opt-in
  local proof, and Docker-internal lookup remains a manual runbook step
- The smoke suite now explicitly covers `--json` parsing, safe failure output,
  timeout/unavailable handling, and secret redaction, without requiring Docker
  for CI-safe verification

## Ops Runbooks / Operator Truth

- [x] Production edge checklist exists: `docs/project-ops/PRODUCTION_EDGE_CHECKLIST.md`
- [x] Backup/restore runbook exists: `docs/project-ops/BACKUP_RESTORE_RUNBOOK.md`
- [x] Migration rollback runbook exists: `docs/project-ops/MIGRATION_ROLLBACK_RUNBOOK.md`
- [x] Retention policy exists: `docs/project-ops/RETENTION_POLICY.md`
- [x] Supabase/RLS hardening notes exist: `docs/project-ops/SUPABASE_RLS_HARDENING.md`
- [x] Stale task reconciliation exists: `docs/project-ops/TASKS_RECONCILIATION.md`
- [ ] Backup automation implemented
- [ ] Restore automation tested against production-like target
- [ ] Retention/archive job implemented
- [ ] Supabase production settings applied and externally verified
- [ ] RLS policy changes implemented and tested

---

## Current Verified State (2026-07-05)

### Test Baseline
- Backend: `.venv\Scripts\python.exe -m pytest -q` → **496 passed**
- Final-demo script tests → **9 passed**
- API abuse smoke tests → **4 passed**
- WAF ingest and inference queue tests → **24 passed**
- Request-context regression tests → **9 passed**
- Frontend lint: `cd frontend && npm run lint` → **PASSED**
- Frontend typecheck: `cd frontend && npm run typecheck` → **PASSED**
- Frontend BFF: `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **95 passed**
- Frontend full suite: `cd frontend && npx vitest run` → **317 passed**
- Frontend build: `cd frontend && npm run build` → **PASSED**

### Backend Routes
- `POST /api/predict` ✓
- `POST /api/triage` ✓
- `GET /api/alerts` ✓
- `GET /api/alerts/{id}` ✓
- `PATCH /api/alerts/{id}/triage` ✓
- `GET /api/stats` ✓
- `GET /api/ml-health` ✓
- `POST /api/feedback` ✓
- `GET /health` ✓
- `GET /api/health` ✓

### Frontend/BFF Truths
- `USE_MOCK_API` is the single centralized server-only mock toggle ✓
- All BFF handlers require Auth.js session ✓
- `frontend/proxy.ts` is the active edge entrypoint ✓
- Local `next start` validation requires `AUTH_TRUST_HOST=true` ✓
- Transport contract values remain `BLOCKED`, `THROTTLED`, `ALLOWED` ✓

### Data Boundary
- App runtime uses Supabase-backed PostgreSQL ✓
- Tests use SQLite ✓
- Async SQLAlchemy remains the only DB access path ✓

---

## Open Backlog

- [x] Build/verify external demo target website (`G:\AI\land-records-portal`)
- [x] Verify local WAF path through `localhost:8088` with ModSecurity/OWASP CRS block, audit log, bridge post, backend ingest, and transaction lookup proof
- [x] Verify WAF JSONL bridge and internal FastAPI ingest route with live ModSecurity audit-log evidence
- [~] ModSecurity audit-log policy is documented, but automatic rotation and production retention are not implemented
- [~] Decide whether ModSecurity becomes a production browser-facing path or remains a local proof/demo path; current dashboard path remains `Browser -> Next.js -> FastAPI`
- [ ] Decide ModSecurity audit-log format, captured fields, transaction ID strategy, log rotation, and retention
- [x] Create CRS-only baseline report for normal and attack traffic; report exists at `reports/modsecurity-live-proof/crs-baseline.md`
- [x] Demo-target WAF config exists for `localhost:8089 -> demo-target-modsecurity -> demo-portal`; the profile is optional for normal startup and required for the final realistic WAF demonstration; `demo-portal` builds from the separate land-records portal repo path, runs internally on Compose port `3010`, and is not host-published by default; `demo-target-bridge` watches `logs/modsecurity/demo-target/modsec_audit.jsonl` for CyberTrace ingest
- [x] Final observed demo-target report exists at `reports/modsecurity-live-proof/demo-target-crs-proof.md`
- [x] Add bounded `asyncio.Queue(maxsize=N)` inference queue and queue health visibility
- [x] Add structured JSON logs with backend request/trace IDs and bridge-to-backend `transaction_id` correlation; scope is request/WAF/prediction boundaries and bridge operational events, not every application log
- [x] Return a safe `X-Request-ID` on generic unhandled `500` responses while preserving sanitized `request.failed` logs
- [x] Emit bridge configuration failures as JSON stderr and normalize unsupported backend structured-log levels to `INFO`
- [x] Migrate Starlette `TestClient` to pinned `httpx2==2.5.0` while retaining legacy `httpx` for current consumers
- [x] Add a standalone final-demo smoke script with explicit backend, `8088`,
  and `8089` modes, JSON output, timeouts, safe failures, and deterministic
  script tests
- [x] Add current-backend API abuse/resource proof for malformed input, auth
  correlation and token non-leakage, body limits, duplicate/unknown WAF
  transactions, model unavailable behavior, and queue overflow
- [~] Minimal metrics use existing `/api/stats`, `/api/ml-health` queue health, and JSON bridge summary counts; no separate bridge/email metrics endpoint is implemented
- [x] Add client-standard `CRITICAL >=90%` confidence tier across backend/frontend contracts and tests
- [ ] Add real-time dashboard alerting for timely threat visibility
- [ ] Add email notifications after detection using a transactional email provider/API
- [x] Replace demo password login with Supabase `auth_accounts` and Argon2id password hashes; no env fallback remains
- [x] Implement server-side Admin/Analyst/Viewer RBAC with per-account `authz_version`
- [~] Login hardening includes Argon2id-only verification, generic errors, local identifier/global throttles, a two-slot password-hash cap, eight-hour sessions, and safe JSON login and route-guard audit logs; MFA, reset/recovery, distributed throttling, and persistent audit storage remain unimplemented
- [x] Auth/security schema and runtime account boundary implemented: additive migration, nine public-schema tables, RLS enabled, public-role revocations, no policies, server-only login/freshness queries, and no `AUTH_USERS_JSON` fallback. Live Supabase migration application remains a reviewed manual operation
- [x] Add safe Supabase account provisioning scripts for create/list/disable/set-password using Argon2id; username normalization matches runtime login
- [x] Cut Auth.js Credentials login and all six BFF freshness checks over to `auth_accounts`; missing, disabled, role-changed, stale, and DB-unavailable accounts fail closed
- [x] Stabilize PR #79 frontend CI native-addon loading: PR #81 uses pure mocks in non-hashing auth/provisioning tests, keeps real Argon2id coverage in `password-hash.test.ts`, and passed the full frontend CI job twice without changing the threaded Vitest pool or production auth code
- [ ] Implement 2FA/MFA
- [ ] Decide whether local Docker Compose is experimental smoke support or a fully supported operator path
- [ ] Redis-backed enforcement or review-queue state
- [ ] Repo-managed export and verification of Supabase policy / RLS state
- [ ] Re-assess any remaining chart container sizing warnings only after stable UI reproduction

---

## PD2 Demo Checklist

- [x] normal request reaches the demo target
- [x] SQLi request reaches the ModSecurity/CRS path
- [ ] code/server-side injection-like request reaches the ModSecurity/CRS path
- [ ] other attack-like request reaches the ModSecurity/CRS path
- [x] CRS detection evidence is captured
- [x] WAF event is ingested by FastAPI
- [x] ML triage runs
- [x] confidence tier is recorded
- [x] dashboard alert is visible; replacement screenshot evidence exists in `reports/modsecurity-live-proof/dashboard-evidence.md` and `reports/modsecurity-live-proof/screenshots/`, including `/records/search`, `SQL Injection`, `Blocked`, and `crs_score=15` in the `8089` alerts table
- [x] action is recorded; real enforcement only if separately implemented
- [ ] email/SSE evidence is captured only after those features exist

## Abuse Smoke Expectations

- [x] missing auth
- [x] invalid token
- [x] malformed JSON
- [x] oversized payload
- [x] duplicate transaction ID
- [x] repeated transaction request/idempotency
- [x] queue overflow after queue implementation
- [x] failed/model-unavailable inference
- [x] invalid triage update
- [x] dashboard API access without session (existing BFF route tests)
- [ ] email/SSE/RBAC/2FA abuse cases only after those features exist

---

## Quick Reference Commands

```powershell
# Backend tests
.venv\Scripts\python.exe -m pytest -q

# Frontend lint + typecheck
cd frontend && npm run lint && npm run typecheck

# BFF-focused tests
cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts

# Full frontend tests
cd frontend && npx vitest run

# Frontend build
cd frontend && npm run build

# Start backend
.venv\Scripts\python.exe -m uvicorn web_app.presentation.app:create_app --reload

# Start frontend
cd frontend && npm run dev

# DistilBERT promotion dry-run
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run --source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" --active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" --archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" --archive-suffix "pre_20260420" --dry-run

# DistilBERT promotion
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run --source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" --active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" --archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" --archive-suffix "pre_20260420"
```
