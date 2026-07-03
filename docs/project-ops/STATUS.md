# Project Ops Status

**Scope:** operator-only session status
**Defense:** May 2026
**Last updated:** 2026-07-03

---

## Current Verified Repo State

- Active branch baseline: `master`
- Python runtime target: `3.14+`
- Local venv currently recreated and verified on: `Python 3.14.3`
- Frontend runtime: Next.js `16.2.9`, React `19.2.4`, TypeScript `5.9.3`, Zod `4.3.6`
- Backend runtime: FastAPI `0.138.0`, Pydantic `2.12.5`, SQLAlchemy `2.0.48` (async)
- Model/runtime artifacts boundary: `ml_model/model_registry/`
- Data/runtime boundary: Supabase-backed PostgreSQL for app runtime, SQLite for tests
- DistilBERT promotion workflow CLI: `ml_model/export/promote_final_training_run.py`
- Active staged path remains stable: `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755`
- Client requirements are now tracked in `docs/client-requirements.md`: secure login, RBAC, 2FA, timely alerts, email notifications after detection, and `CRITICAL >=90%`.

### Latest local verification results

- Backend dependency integrity: `.venv\Scripts\python.exe -m pip check` → **pass**
- Backend tests: `.venv\Scripts\python.exe -m pytest -q` → **489 passed**
- Final-demo script tests: `.venv\Scripts\python.exe -m pytest -q tests/scripts/test_run_final_demo_smoke.py` → **9 passed**
- API abuse smoke tests: `.venv\Scripts\python.exe -m pytest -q tests/integration/test_api_abuse_smoke.py` → **4 passed**
- WAF ingest and inference queue tests: `.venv\Scripts\python.exe -m pytest -q tests/integration/test_waf_ingest_route.py tests/unit/test_inference_queue.py` → **24 passed**
- Request-context regression tests: `.venv\Scripts\python.exe -m pytest -q tests/unit/test_request_context_middleware.py` → **9 passed**
- App startup sanity: `.venv\Scripts\python.exe -c "from web_app.presentation.app import create_app; print(bool(create_app()))"` → **True**
- Frontend lint: `cd frontend && npm run lint` → **pass**
- Frontend typecheck: `cd frontend && npm run typecheck` → **pass**
- Frontend BFF-focused tests:
  - `cd frontend && npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts lib/searchParams.test.ts` → **89 passed**
- Frontend full suite: `cd frontend && npx vitest run --pool=threads` → **206 passed**
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
- Targeted WAF checks: bridge tests `37 passed`, WAF ingest route tests `11 passed`, WAF ingest use-case tests `4 passed`; the latest combined run passed `52` tests, and the previously verified `docker compose config --quiet` result remains recorded in the proof evidence.
- ModSecurity audit-log policy is documented; automatic rotation and production retention remain TODO.
- Bridge follow-mode transient `readline()` `OSError` resilience is implemented and unit-tested in `tests/scripts/test_waf_audit_bridge.py`; the follow loop preserves the last safe file position, warns, sleeps briefly, reopens, and continues processing later lines.

### Observability and traceability

- FastAPI responses include `X-Request-ID`; safe incoming IDs are preserved and missing or invalid IDs are replaced. Generic unhandled `500` responses also return the request ID without exposing raw exception details.
- Valid W3C version-00 `traceparent` headers supply the request `trace_id` and `span_id`; otherwise the backend generates a local `trace_id` without inventing a span.
- Request completion/failure, WAF ingest outcomes, and direct prediction outcomes use single-line JSON logs through `web_app/observability/structured_logging.py`.
- The WAF bridge emits single-line JSON events for startup, configuration failures, follow mode, retry, post success/failure, duplicate skip, read errors, and summary counts; configuration failures use JSON stderr while normal operations remain on stdout.
- `transaction_id` correlates bridge and backend WAF events. Within FastAPI, `request_id` and `trace_id` correlate route and ingest/prediction events for one request.
- New structured-log fields are redacted recursively and case-insensitively for Authorization, cookies, API keys, tokens, passwords, secrets, sessions, credentials, and database connection values. Raw request bodies and query strings are not logged by the new request/route instrumentation.
- Minimal metrics remain the existing `/api/stats`, `/api/ml-health` queue health, and bridge summary log counts. No new metrics endpoint, Prometheus, tracing backend, or SIEM was added.
- Ops runbooks added as documentation-only artifacts:
  - `docs/project-ops/PRODUCTION_EDGE_CHECKLIST.md`
  - `docs/project-ops/BACKUP_RESTORE_RUNBOOK.md`
  - `docs/project-ops/MIGRATION_ROLLBACK_RUNBOOK.md`
  - `docs/project-ops/RETENTION_POLICY.md`
  - `docs/project-ops/SUPABASE_RLS_HARDENING.md`
  - `docs/project-ops/TASKS_RECONCILIATION.md`
- These docs do not implement production deployment, backup automation, restore automation, database migrations, retention/archive jobs, Supabase dashboard changes, RLS policies, Wazuh export, or SIEM deployment.

### Automated final demo and abuse smoke proof

- `scripts/run_final_demo_smoke.py` provides explicit `backend`, `waf-8088`,
  and `demo-target-8089` modes with bounded HTTP timeouts, concise
  PASS/FAIL/SKIP output, parseable `--json` output, and nonzero exit on required
  check failure.
- Script tests cover parseable JSON output, controlled timeout/unavailable
  failures, and redaction of secret-like values and Authorization headers.
- The script does not read or emit the backend API secret, Authorization
  headers, database URLs, or raw request payloads. Connection failures use
  fixed safe messages without tracebacks.
- `tests/scripts/test_run_final_demo_smoke.py` is deterministic and requires no
  Docker, live network, Supabase, or sibling portal checkout.
- `tests/integration/test_api_abuse_smoke.py` adds malformed JSON, auth
  correlation/token non-leakage, and invalid triage input proof. Existing tests
  remain the source for body limits, invalid alert IDs, duplicate/unknown WAF
  transactions, model unavailable behavior, and queue overflow.
- Queue-full WAF proof now explicitly asserts `X-Request-ID`,
  `waf_ingest.queue_full`, `transaction_id`, `queue_depth`, `Retry-After`, and
  API-secret non-leakage.
- The `8088` and `8089` CLI modes remain opt-in local checks. Missing audit
  JSONL files and Docker-internal transaction lookup are reported as `SKIP`;
  the manual lookup commands remain in
  `docs/project-ops/SMOKE_TEST_RUNBOOK.md`.
- Starlette `TestClient` now uses pinned `httpx2==2.5.0` without the deprecated plain-`httpx` warning path; `httpx==0.28.1` remains for current consumers such as `huggingface_hub`.

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
  - Persisted-alert dashboard counts and confidence styling use backend-emitted `confidence_level`, not raw-score reclassification.
  - Confidence distributions include all predictions; enforcement-policy counts exclude `Normal`, which remains `ALLOWED` for every valid tier.
  - Confidence-tier badges display the canonical tier and do not replace it with `Benign`.

---

## Important Notes For Operators

- CI may show four checks on branch updates because both `push` and `pull_request` workflows run for frontend and backend.
- `requirements.train.txt` is laptop/training-only and should not be treated as required for CI/backend runtime verification.
- Supabase is now part of the current runtime truth. Do not document it as merely planned.
- ModSecurity audit log policy is documented in `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`.
- Current ModSecurity audit log path is JSONL at `logs/modsecurity/modsec_audit.jsonl`.
- Bridge and selected backend boundary logs are structured JSON; legacy startup and unrelated application logs are not claimed to be converted repo-wide.
- Local WAF proof evidence remains under `reports/modsecurity-live-proof/`.
- Dashboard screenshot evidence remains under `reports/modsecurity-live-proof/dashboard-evidence.md` and `reports/modsecurity-live-proof/screenshots/`.
- Demo-target proof is separate from the default `localhost:8088` WAF proof path and requires `demo-target-bridge` when `8089` events must appear in CyberTrace.
- Automatic audit log rotation is not implemented.
- Production retention and full Wazuh/SIEM deployment are not implemented.

---

## Open Gaps (Current, Not Historical)

- Docker Compose WAF ingest proof is verified locally through `localhost:8088`, but this is not a production-grade ModSecurity-fronted deployment.
- Portal-target WAF proof through `localhost:8089` is runtime-verified locally. The profile is optional for normal startup, but required for the final realistic WAF demonstration.
- Bridge follow-mode transient `readline()` `OSError` resilience is implemented and unit-tested; automatic log rotation and production retention remain TODO.
- Bounded in-process inference queue and queue health visibility are implemented for synchronous WAF ingest.
- Redis-backed enforcement state is not implemented and should stay conditional on shared runtime state.
- Some Supabase policy and operational hardening steps remain outside automated repo verification/export.
- Client-required real user access management with RBAC and secure login is not yet implemented beyond the current demo credentials flow.
- Client-required 2FA is not yet implemented.
- Client-required email notification after detection is not yet implemented.
- Real-time SSE/EventSource dashboard alerting is not yet implemented.
- Automated final-demo HTTP/audit checks are implemented, but Docker-internal
  backend transaction lookup and full dashboard interaction remain explicit
  manual runbook steps rather than always-on CI.
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
