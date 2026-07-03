# Documentation

Last updated: 2026-07-03

This folder is the maintained documentation surface for the repository. It is intentionally trimmed to the documents that still map to the current codebase, test suite, runtime boundaries, and academic deliverables.

## Use This Folder By Purpose

### Current implementation
- `CONTEXT.md`
  - Short status snapshot for the repo as it exists today.
- `architecture.md`
  - Current system structure, request flow, active boundaries, and known gaps.
- `SETUP.md`
  - Honest local setup instructions for the repo in its current state.
- `client-requirements.md`
  - Client-stated PD2 requirements for secure login, RBAC, 2FA, timely alerts, email notifications, and confidence-tier expectations.
- `CURRENT_SYSTEM_STATE.md`
  - Detailed snapshot of pages, contracts, and runtime behavior.
- `DESIGN_SYSTEM.md`
  - Frontend token, pattern, and styling guidance.
- `agent-tooling.md`
  - Repo-maintained MCP and CLI routing guidance.
- `../CONTRIBUTING.md`
  - Workflow, guardrails, and validation steps for contributors.

### Operator docs
- `project-ops/STATUS.md`
  - Team and implementation status notes for current operator workflows.
- `project-ops/LIVING_CHECKLIST.md`
  - Ongoing implementation checklist and handoff material.
- `project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`
  - ModSecurity audit-log policy for the verified local WAF proof path.
- `project-ops/DEMO_TARGET_WAF_PROOF.md`
  - Verified local PD2 proof for the realistic `localhost:8089` demo-target WAF path against the separate land-records portal.
- `project-ops/SMOKE_TEST_RUNBOOK.md`
  - Canonical smoke commands for the `8088` technical proof path and the `8089` realistic demo-target path.
- `project-ops/README.md`
  - Entry point for the operator-doc subset.
- `../reports/modsecurity-live-proof/e2e-proof.md`
  - Checked-in local proof evidence for ModSecurity/OWASP CRS -> bridge -> FastAPI WAF ingest.

### Dataset and ML baseline
- `DATASET_RELEASE_SR_BH_CLEAN_v3.1.0.md`
  - Release note for the current cleaned dataset snapshot.
- `DATASET_BASELINE_SR_BH_v3.1.0.md`
  - Frozen baseline statistics and training metadata for the current dataset version.

## Verified Repo State

- Backend tests currently pass: `.venv\Scripts\python.exe -m pytest -q`
- Frontend lint currently passes: `cd frontend && npm run lint`
- Frontend typecheck currently passes: `cd frontend && npm run typecheck`
- Frontend tests currently pass: `cd frontend && npx vitest run`
- Frontend production build currently passes: `cd frontend && npm run build`
- Latest verification counts are recorded in `project-ops/STATUS.md`.
- Current backend API surface includes:
  - protected: `POST /api/predict`, `POST /api/triage`, `GET /api/alerts`, `GET /api/alerts/{id}`, `PATCH /api/alerts/{id}/triage`, `GET /api/stats`, `GET /api/ml-health`, `POST /api/feedback`
  - public: `GET /health`, `GET /api/health`
- The Next.js dashboard BFF is wired for alerts, alert detail, triage, stats, and ML health through `frontend/lib/bff-client.ts`
- USE_MOCK_API=false (hitting real FastAPI)
- Supabase is the active hosted PostgreSQL boundary for the app runtime
- Dockerfiles and `docker-compose.yml` are present for local smoke testing
- The local Compose stack currently publishes the frontend on `localhost:3000`
- The technical CyberTrace WAF proof path is published on `localhost:8088`
- The realistic protected demo website WAF path is published on `localhost:8089` when the `demo-target` profile is enabled; Compose builds the separate land-records portal as internal service `demo-portal:3010`, so no manual portal dev server is required
- The backend stays internal to the Compose network and is shown as `8000/tcp`; do not use `localhost:8000` unless backend port 8000 is explicitly published
- Verified local WAF proof: `/healthz` and `/api/health` returned HTTP 200 through `localhost:8088`; SQLi probe `/api/health?id=17%27%20OR%2017%3D17--` returned HTTP 403; bridge posted to FastAPI; Docker-internal lookup returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `crs_score=5`, rules `942100` and `949110`, with `source_ip`, `request_path`, and URL-encoded `query_string` present
- Verified demo-target WAF proof: `localhost:8089` home returned HTTP 200; SQLi marker `SMOKE002945` returned HTTP 403; `demo-target-bridge` posted transaction `178249138618.813428`; backend lookup returned `found=true`, `/records/search`, `prediction=SQL Injection`, `action_taken=BLOCKED`, and `crs_score=15`
- Targeted WAF checks passed: bridge tests `37 passed`, WAF ingest route tests `11 passed`, WAF ingest use-case tests `4 passed`; the latest combined targeted run passed `52` tests, and the previously verified `docker compose config --quiet` result remains recorded in the WAF proof evidence
- Backend request/WAF/prediction boundaries and bridge operations emit structured JSON logs with request/trace/transaction correlation; bridge configuration failures are JSON on stderr
- Starlette `TestClient` uses pinned `httpx2==2.5.0`; legacy `httpx==0.28.1` remains installed for existing consumers
- Real user access management/RBAC is implemented for the named-account foundation; 2FA and email notifications after detection remain planned requirements tracked in `client-requirements.md`.
- The `CRITICAL >=90%` model-confidence tier is implemented without retraining, recalibration, model artifact changes, or retroactive historical-row reclassification.
- Frontend confidence distributions and styling use persisted `confidence_level`; enforcement-policy counts are non-Normal-only, and confidence-tier badges never replace the canonical tier with prediction labels.

## Documentation Rules For This Repo

- Keep implementation docs tied to code and tests, not intention.
- If something is planned but not shipped, label it as planned.
- Keep setup, architecture, and status separate so each file has one job.
- Preserve academic documents, but mark them clearly when they are design artifacts instead of runtime truth.
- Keep operator docs separate from user-facing implementation docs.
