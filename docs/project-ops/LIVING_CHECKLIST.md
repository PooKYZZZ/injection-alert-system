# Living Checklist
> Location: `docs/project-ops/LIVING_CHECKLIST.md`
> Keep this file updated after every meaningful implementation or verification session.
> This is a working checklist, not the full runtime source of truth.

**Last updated:** 2026-07-30

Status note:
- Current repository status is maintained in `docs/project-ops/STATUS.md`;
  PR #90 is merged into `master`; the current review branch is `feat/pr7-waf-runtime`.
- PR7 Block 1 and Block 2 controlled-local WAF runtime evidence is complete in
  `PR7_BLOCK_2_EVIDENCE.md`; hosted/staging/production enforcement remains off
  and Block 3 evidence is still open.
- Hosted Supabase is migrated through `20260712_000020`; disposable PostgreSQL downgrade/re-upgrade through the same head passed
- Current frontend validation: lint, typecheck, build, and full Vitest pass; remote authentication E2E is passing. Local-only browser session behavior remains a follow-up if it reappears.
- Current source-of-truth runtime docs are `docs/CONTEXT.md`, `docs/architecture.md`, and `docs/SETUP.md`
- PR #84 source-correlation implementation is locally complete at Alembic head
  `20260715_000021`; hosted Supabase is only confirmed through
  `20260712_000020` and must not be described as migrated to the new head.
- PR #84 implementation is historical and frozen at baseline
  `6cfe67bd331e55d4309c201c8c254668bc2ea688`; that maintenance pass was
  documentation-only. PR2 SSE and PR3 Telegram are completed historical slices;
  their evidence remains in `docs/project-ops/STATUS.md`.
- PR #85 automated validation is green for backend, frontend, postgres,
  auth-e2e, and secret-scan. Manual WAF repetition, no-refresh dashboard
  updates, hosted SSE delivery, browser reconnect, and source-correlation
  regression evidence are recorded in `docs/project-ops/STATUS.md`.
- [x] Add Telegram as a database-backed outbox channel restricted to
  `threat_detected`, with versioned V6.2 claiming and channel-specific dedupe.
- [x] Enqueue Telegram only for persisted in-scope (`SQL Injection` or `Code
  Injection`) HIGH/CRITICAL alerts while preserving email and isolating each
  channel's enqueue failure.
- [x] Add plain-text HTTPX `sendMessage` delivery, explicit timeouts, bounded
  429/5xx retry classification, ambiguous-delivery handling, and secret-safe logs.
- [x] Add mocked provider/worker/WAF failure-isolation tests and an explicitly
  guarded provider smoke. Live/hosted Telegram proof remains unverified.
- [x] PR3 local verification: focused matrix **165 passed**, full backend
  **754 passed, 34 skipped**, disposable PostgreSQL notification tests
  **10 passed**, and V6.2 downgrade/re-upgrade ended at the single expected head.
- WAF submission uses a distinct `WAF_INGEST_API_KEY`; lookup/BFF traffic keeps
  `API_SECRET_KEY`. Production/staging reject missing, short, or equal WAF keys.
- Current PR validation: backend **703 passed, 32 skipped**; focused
  source/integrity suite **189 passed**; migration-focused run **2 passed, 1
  PostgreSQL-only skip**;
  executable SQLite migration cycle passed; disposable PostgreSQL CI
  integration **114 passed** and migrations **39 passed**; clean-checkout
  Compose **8 passed**; frontend lint,
  typecheck, **84 files / 480 Vitest tests**, and production build passed.
- [x] Required PR #84 GitHub jobs passed for implementation head `6cfe67b`:
  backend, postgres, frontend, auth-e2e, and secret-scan. Earlier
  Compose/secret-scan failures and the intermediate dependency-audit failure
  remain summarized in
  `docs/project-ops/STATUS.md` rather than hidden.
- [ ] Dependency exception owner: backend dependency-maintenance; review by
  2026-09-30. Remove `PYSEC-2026-3447` when active PyTorch permits
  `setuptools>=83`, or earlier if macOS packaging/source-distribution jobs are
  introduced. The current Linux wheel-only CI still ignores this one advisory.
- Canonical source/provenance/status and factual fingerprint duplicate handling
  are implemented. The fingerprint is internal and omitted from lookup/UI.
- [x] Compose profile/service/port/network configuration is automatically
  verified for technical, demo, hosted, and controlled topologies.
- [x] Complete the controlled packet-path proof (two client sources, forged
  direct header, correlated rows, SQLi 403) locally on 2026-07-17. This is
  Docker evidence only; it does not prove hosted Cloudflare trust.
- [x] Complete the hosted home Wi-Fi and mobile-data source-correlation proof:
  distinct public sources matched ModSecurity, bridge, FastAPI, PostgreSQL,
  and dashboard records; forged-header resistance, fresh-audit leakage review,
  and restart/recreate proof also passed.
- [ ] Complete the final hosted trust gate: review Cloudflare Pseudo IPv4,
  confirm no Worker rewrites `CF-Connecting-IP`, prove direct-origin isolation,
  and independently confirm the immediate tunnel-side peer before enabling
  `cloudflare_tunnel`; current mode remains `unverified`.
- Hosted recreate configuration is now persistent through the ignored root
  `.env` and `scripts/start_hosted_target.ps1`; the launcher refuses missing or
  broad peers and any mode other than `unverified`.
- ModSecurity audit-log handling policy is documented in `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`
- Client requirements are tracked in `docs/client-requirements.md`
- Confidence-tier naming is clarified in code/docs: `confidence_tier` is the preferred filter name, legacy `severity` remains a compatibility alias, current tiers remain `LOW`/`MEDIUM`/`HIGH`/`CRITICAL`, and `CRITICAL >=90%` is implemented as the confidence threshold
- Frontend confidence semantics are aligned: persisted-alert grouping/styling uses `confidence_level`; enforcement-policy counts exclude Normal predictions; Normal remains `ALLOWED` for every valid tier; tier badges always display the canonical tier
- Alerts UI role affordances are implemented for dense alert rows and detail views: viewers are read-only, analysts keep triage controls, and admins keep the full control set
- DistilBERT staged promotion now uses `ml_model/export/promote_final_training_run.py` with archive-and-recreate safety, `weights_only=True` checkpoint loading, and separate packaging/quality readiness fields
- Real promotion command currently fails closed on strict head-shape mismatch between final-training checkpoint and `package_serving_artifact.py` loader expectations; rollback restoration behavior is verified
- Local WAF ingest proof is verified in `reports/modsecurity-live-proof/e2e-proof.md`: WAF path `localhost:8088`, SQLi HTTP 403, JSON audit log, bridge `status=200`, backend lookup `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `source_ip`, `request_path`, URL-encoded `query_string`, `crs_score=5`, and rules `942100`, `949110`
- Realistic demo-target WAF proof is verified locally through `localhost:8089`: marker `SMOKE002945` returned HTTP 403, `demo-target-bridge` posted transaction `178249138618.813428`, and backend lookup returned `found=true`, `/records/search`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `crs_score=15`
- Dashboard screenshot evidence is verified in `reports/modsecurity-live-proof/dashboard-evidence.md` with PNGs under `reports/modsecurity-live-proof/screenshots/`; the latest set includes `8089` dashboard/table evidence and an ML health overview, while the detail drawer screenshots show the default `8088` path
- Request/trace context, structured JSON logs for request/WAF/prediction boundaries, bridge JSON logs, and recursive log-field redaction are implemented and covered by targeted backend tests
- Final-demo automation is checked in at `scripts/run_final_demo_smoke.py` with
  deterministic Docker-free tests; live `8088`/`8089` modes remain opt-in
  local proof, and `--require-backend-lookup` enforces current-marker backend
  correlation after bounded audit-flush and bridge-persistence waits
- The smoke suite now explicitly covers `--json` parsing, safe failure output,
  stale-audit rejection, timestamp/marker correlation, timeout/unavailable
  handling, and secret redaction, without requiring Docker for CI-safe verification

## Ops Runbooks / Operator Truth

- [x] Production edge limitations are recorded in `docs/project-ops/STATUS.md` and `docs/project-ops/MIGRATION_ROLLBACK_RUNBOOK.md`
- [x] Backup/restore runbook exists: `docs/project-ops/BACKUP_RESTORE_RUNBOOK.md`
- [x] Migration rollback runbook exists: `docs/project-ops/MIGRATION_ROLLBACK_RUNBOOK.md`
- [x] Retention policy exists: `docs/project-ops/RETENTION_POLICY.md`
- [x] Supabase/RLS hardening notes exist: `docs/project-ops/SUPABASE_RLS_HARDENING.md`
- [x] Stale task reconciliation was archived; current work is tracked in the gap register.
- [x] CyberTrace V6.1 deployment and feature-gate guidance exists in `docs/SETUP.md`, `docs/architecture.md`, and `docs/project-ops/SMOKE_TEST_RUNBOOK.md`
- [ ] Backup automation implemented
- [ ] Restore automation tested against production-like target
- [ ] Retention/archive job implemented
- [ ] Supabase production settings applied and externally verified
- [ ] RLS policy changes implemented and tested

---

## Current Verified State (historical baseline: 2026-07-05)

### Test Baseline
- Backend: `.venv\Scripts\python.exe -m pytest -q` → **528 passed**
- Final-demo script tests → **16 passed**
- API abuse smoke tests → **4 passed**
- WAF ingest and inference queue tests → **25 passed**
- Request-context regression tests → **9 passed**
- Frontend lint: `cd frontend && npm run lint` → **PASSED**
- Frontend typecheck: `cd frontend && npm run typecheck` → **PASSED**
- Frontend BFF: `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **96 passed**
- Frontend full suite: `cd frontend && npx vitest run` → **333 passed**
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

## Implementation Gap Routing

All prior unresolved items were normalized into the canonical
[`IMPLEMENTATION_GAP_REGISTER.md`](IMPLEMENTATION_GAP_REGISTER.md); do not
duplicate their full entries here. [`STATUS.md`](STATUS.md) remains the current
operator snapshot.

- PR5 LOW/MEDIUM is locally complete and controlled-local E2E-evidenced;
  `LIMIT-001` preserves the exact screenshot-sequence limitation.
- PR6 HIGH application blocking is implemented, automated-tested, and
  controlled-local E2E-evidenced; the portal blocks before record filtering.
  Exact distinct-source local E2E remains topology-limited, and the stable page
  response uses generic HTTP 200 block content rather than experimental 403.
- `BLOCK-001` and `BLOCK-002` gate hosted/production rollout.
- `LIMIT-006` tracks shared-IP collateral risk for HIGH source-key blocking;
  `LIMIT-007` tracks the stable HTTP 200 block-page limitation.
- `GAP-001` is complete for PR6; `GAP-002` is partially resolved by the
  controlled-local PR7 Block 1/Block 2 runtime. Its Block 3 evidence remains
  open in the gap register.

---

## PD2 Demo Checklist

- [x] normal request reaches the demo target
- [x] SQLi request reaches the ModSecurity/CRS path
- [ ] code/server-side injection-like request reaches the ModSecurity/CRS path
- [ ] other attack-like request reaches the ModSecurity/CRS path
- [x] CRS detection evidence is captured
- [x] WAF event is ingested by FastAPI
- [x] ML triage runs
- [x] controlled-local PR7 PostgreSQL -> backend -> WAF activation and
  revocation proof passes
- [ ] complete attack -> audit bridge -> ML -> recommendation -> WAF proof
- [x] confidence tier is recorded
- [x] dashboard alert is visible; replacement screenshot evidence exists in `reports/modsecurity-live-proof/dashboard-evidence.md` and `reports/modsecurity-live-proof/screenshots/`, including `/records/search`, `SQL Injection`, `Blocked`, and `crs_score=15` in the `8089` alerts table
- [x] action is recorded; PR4 shadow recommendations are separately persisted and checked for later `/records/search` requests; `actual_decision=ALLOW` and no real control is applied
- [x] SSE edge automation, disposable real-stack Chromium no-refresh proof,
  browser-native reconnect, and named-domain hosted SSE evidence passed. Email
  evidence remains separate and pending.

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
- [x] SSE backend bearer denial and BFF fail-closed permission behavior are
  covered; disposable cleanup, no-reload behavior, and live disconnect/reconnect
  recovery proof passed. Email follow-up remains separate.

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
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run --source-run-dir "ml_model\results\benchmarks\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" --active-run-dir "ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" --archive-root "ml_model\model_registry\archive" --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" --archive-suffix "pre_20260420" --dry-run

# DistilBERT promotion
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run --source-run-dir "ml_model\results\benchmarks\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" --active-run-dir "ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" --archive-root "ml_model\model_registry\archive" --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" --archive-suffix "pre_20260420"
```
