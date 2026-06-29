# Project Ops Status

**Scope:** operator-only session status
**Defense:** May 2026
**Last updated:** 2026-06-29

---

## Current Verified Repo State

- Active branch baseline: `master`
- Python runtime target: `3.14+`
- Local venv currently recreated and verified on: `Python 3.14.3`
- Frontend runtime: Next.js `16.2.1`, React `19.2.4`, TypeScript `5.9`, Zod `4.3.6`
- Backend runtime: FastAPI `0.135.1`, Pydantic `2.12.5`, SQLAlchemy `2.0.48` (async)
- Model/runtime artifacts boundary: `ml_model/model_registry/`
- Data/runtime boundary: Supabase-backed PostgreSQL for app runtime, SQLite for tests
- DistilBERT promotion workflow CLI: `ml_model/export/promote_final_training_run.py`
- Active staged path remains stable: `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755`
- Client requirements are now tracked in `docs/client-requirements.md`: secure login, RBAC, 2FA, timely alerts, email notifications after detection, and `CRITICAL >=90%`.

### Latest local verification results

- Backend dependency integrity: `.venv\Scripts\python.exe -m pip check` → **pass**
- Backend tests: `.venv\Scripts\python.exe -m pytest -q` → **444 passed**
- App startup sanity: `.venv\Scripts\python.exe -c "from web_app.presentation.app import create_app; print(bool(create_app()))"` → **True**
- Frontend lint: `cd frontend && npm run lint` → **pass**
- Frontend typecheck: `cd frontend && npm run typecheck` → **pass**
- Frontend BFF-focused tests:
  - `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **81 passed**
- Frontend full suite: `cd frontend && npx vitest run` → **191 passed**
- Frontend production build: `cd frontend && npm run build` → **pass**
- Promotion pipeline unit tests: `.venv\Scripts\python.exe -m pytest -q tests/unit/test_promote_final_training_run.py` → **18 passed**
- Promotion dry-run command (April DistilBERT source path) → **pass** (planned actions printed, no writes)
- Promotion real-run command (April DistilBERT source path) → **failed closed** with strict checkpoint architecture incompatibility:
  - `package_serving_artifact.py` strict load expects DistilBERT classification head shapes (`768`) but final-training checkpoint head uses `256`-dim layers
  - rollback behavior verified: active staged run restored; archive target not left behind

### Verified WAF ingest proof

Evidence file: `reports/modsecurity-live-proof/e2e-proof.md`
Audit-log policy file: `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`

- WAF proof path uses `localhost:8088`.
- Backend is internal-only in Docker Compose and shows `8000/tcp`; do not use `localhost:8000` unless backend port 8000 is explicitly published.
- Backend transaction lookup proof uses Docker-internal `docker compose exec -e TXID=$txid backend ...`.
- `/healthz` through `localhost:8088` returned HTTP 200.
- `/api/health` through `localhost:8088` returned HTTP 200 and `{"status":"healthy","database":"connected"}`.
- SQLi probe `/api/health?id=17%27%20OR%2017%3D17--` through WAF returned HTTP 403.
- ModSecurity audit log contained transaction `17821639659.909603`, source IP `172.21.0.1`, and request URI `/api/health?id=17%27%20OR%2017%3D17--`.
- Bridge posted `status=200 transaction_id=17821639659.909603 rule_ids=['942100', '949110']`.
- Docker-internal lookup returned `found=true`, `prediction=SQL Injection`, `confidence_level=HIGH`, `action_taken=BLOCKED`, `source_ip=172.21.0.1`, `request_path=/api/health`, URL-encoded `query_string`, `crs_score=5`, and CRS rules `942100`, `949110`.
- Targeted WAF checks: bridge tests `34 passed`, WAF ingest route tests `8 passed`, WAF ingest use-case tests `4 passed`, and `docker compose config --quiet` passed.
- ModSecurity audit-log policy is documented; automatic rotation and production retention remain TODO.
- Remaining TODO: bridge follow mode once logged transient `OSError: [Errno 5] Input/output error` at `readline()`; bridge restarted and posted successfully afterward.

### CRS baseline and demo-target proof

- CRS-only baseline is documented in `reports/modsecurity-live-proof/crs-baseline.md`.
- Demo-target WAF proof exists at `reports/modsecurity-live-proof/demo-target-crs-proof.md`; the demo-target service uses the official CRS image `BACKEND` reverse-proxy behavior without mounting a custom Nginx template.
- The demo-target Compose profile is optional for normal developer startup and required for the final realistic WAF demonstration.
- Demo-target WAF path is `localhost:8089 -> demo-target-modsecurity -> demo-portal`.
- Demo-target CyberTrace ingest uses `demo-target-bridge`, which watches `logs/modsecurity/demo-target/modsec_audit.jsonl` separately from the default `8088` audit log.
- `demo-portal` is built from the separate land-records portal repo path by the demo-target Compose profile; the portal source remains outside this repo, runs internally on Compose port `3010`, and is not host-published by default.
- Observed demo-target evidence was captured through `localhost:8089`, including normal portal traffic and controlled SQLi/XSS checks with CRS transaction IDs, rule IDs, and matched messages where available.
- Verified demo-target bridge evidence: SQLi marker `SMOKE002945` returned HTTP 403, audit transaction `178249138618.813428` had host `localhost:8089` and path `/records/search`, `demo-target-bridge` posted `status=200`, backend lookup returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, and `crs_score=15`.

### Dashboard screenshot evidence

- Dashboard evidence is documented in `reports/modsecurity-live-proof/dashboard-evidence.md`.
- Reviewed replacement screenshots exist under `reports/modsecurity-live-proof/screenshots/`: dashboard overview variants, `8089` `/records/search` alerts table with WAF/ML rows, default `8088` WAF alert detail drawer, and ML health overview.
- The latest ML health screenshot is an overview capture; queue-health fields are available through `/api/ml-health`, but a queue-specific UI screenshot is not claimed.
- Capture target was `http://localhost:3000` only; no auth state, cookies, session headers, or secrets were written.

### Promotion Workflow Commands

- Dry-run (no writes):
  - `.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run --source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" --active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" --archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" --archive-suffix "pre_20260420" --dry-run`
- Real promotion:
  - `.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run --source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" --active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" --archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" --archive-suffix "pre_20260420"`
- Rollback behavior:
  - If failure occurs after archive, the promotion script restores the archived active run automatically.

### Current API/BFF state

- Implemented backend routes:
  - `POST /api/predict`
  - `POST /api/triage`
  - `GET /api/alerts`
  - `GET /api/alerts/{id}`
  - `PATCH /api/alerts/{id}/triage`
  - `GET /api/stats`
  - `GET /api/ml-health`
  - `POST /api/feedback`
  - `GET /health`
  - `GET /api/health`
- Reservation-first triage flow is active (`PROCESSING` placeholders, lease reclaim support, winner/loser behavior).
- `PROCESSING` rows are excluded from normal alerts and stats reads.
- Frontend boundary remains:
  - `Browser -> Next.js route handlers/BFF -> FastAPI`
- Route protection and proxy entrypoint:
  - Auth checks are enforced in BFF handlers.
  - Next.js edge entrypoint uses `frontend/proxy.ts`.
  - Local `next start` validation requires `AUTH_TRUST_HOST=true` in `frontend/.env.local`.
- Alert confidence-tier naming:
  - Current tiers remain `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL`.
  - Preferred query/filter naming is `confidence_tier`.
  - Legacy `severity` query compatibility is retained for existing URLs and callers.
  - Persisted backend field remains `confidence_level`.
  - `CRITICAL >=90%` is implemented as the high-confidence threshold.
  - Historical rows are not retroactively reclassified.

---

## Important Notes For Operators

- CI may show four checks on branch updates because both `push` and `pull_request` workflows run for frontend and backend.
- `requirements.train.txt` is laptop/training-only and should not be treated as required for CI/backend runtime verification.
- Supabase is now part of the current runtime truth. Do not document it as merely planned.
- ModSecurity audit log policy is documented in `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`.
- Current ModSecurity audit log path is JSONL at `logs/modsecurity/modsec_audit.jsonl`.
- Local WAF proof evidence remains under `reports/modsecurity-live-proof/`.
- Dashboard screenshot evidence remains under `reports/modsecurity-live-proof/dashboard-evidence.md` and `reports/modsecurity-live-proof/screenshots/`.
- Demo-target proof is separate from the default `localhost:8088` WAF proof path and requires `demo-target-bridge` when `8089` events must appear in CyberTrace.
- Automatic audit log rotation is not implemented.
- Production retention and full Wazuh/SIEM deployment are not implemented.

---

## Open Gaps (Current, Not Historical)

- Docker Compose WAF ingest proof is verified locally through `localhost:8088`, but this is not a production-grade ModSecurity-fronted deployment.
- Portal-target WAF proof through `localhost:8089` is runtime-verified locally. The profile is optional for normal startup, but required for the final realistic WAF demonstration.
- Bridge follow-mode resilience for transient `readline()` `OSError` remains a TODO.
- Bounded in-process inference queue and queue health visibility are implemented for synchronous WAF ingest.
- Redis-backed enforcement state is not implemented and should stay conditional on shared runtime state.
- Some Supabase policy and operational hardening steps remain outside automated repo verification/export.
- Client-required real user access management with RBAC and secure login is not yet implemented beyond the current demo credentials flow.
- Client-required 2FA is not yet implemented.
- Client-required email notification after detection is not yet implemented.
- Real-time SSE/EventSource dashboard alerting is not yet implemented.
- Wazuh export-only integration is not yet implemented; full Wazuh/SIEM deployment is deferred.
- Retraining remains design-level in `ml_model/retraining/`; promotion/rollback tooling exists separately under `ml_model/export/`.

---

## Source-of-Truth Docs

- Implementation snapshot: `docs/CONTEXT.md`
- Architecture boundaries: `docs/architecture.md`
- Local setup: `docs/SETUP.md`
- Client requirements: `docs/client-requirements.md`
- Detailed current-state snapshot: `docs/CURRENT_SYSTEM_STATE.md`
- Operator checklist: `docs/project-ops/LIVING_CHECKLIST.md`
- ModSecurity audit log policy: `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`
