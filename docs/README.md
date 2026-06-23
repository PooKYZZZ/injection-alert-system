# Documentation

Last updated: 2026-06-23

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

- Backend tests currently pass: **336 passed** (pytest)
- Frontend lint currently passes: `cd frontend && npm run lint`
- Frontend typecheck currently passes: `cd frontend && npm run typecheck`
- Frontend tests currently pass: **122 passed** (vitest)
- Frontend production build currently passes: `cd frontend && npm run build`
- Current backend API surface includes:
  - protected: `POST /api/predict`, `POST /api/triage`, `GET /api/alerts`, `GET /api/alerts/{id}`, `PATCH /api/alerts/{id}/triage`, `GET /api/stats`, `GET /api/ml-health`, `POST /api/feedback`
  - public: `GET /health`, `GET /api/health`
- The Next.js dashboard BFF is wired for alerts, alert detail, triage, stats, and ML health through `frontend/lib/bff-client.ts`
- USE_MOCK_API=false (hitting real FastAPI)
- Supabase is the active hosted PostgreSQL boundary for the app runtime
- Dockerfiles and `docker-compose.yml` are present for local smoke testing
- The local Compose stack currently publishes the frontend on `localhost:3000`
- The WAF proof path is published on `localhost:8088`
- The backend stays internal to the Compose network and is shown as `8000/tcp`; do not use `localhost:8000` unless backend port 8000 is explicitly published
- Verified local WAF proof: `/healthz` and `/api/health` returned HTTP 200 through `localhost:8088`; SQLi probe `/api/health?id=17%27%20OR%2017%3D17--` returned HTTP 403; bridge posted to FastAPI; Docker-internal lookup returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `crs_score=5`, rules `942100` and `949110`, with `source_ip`, `request_path`, and URL-encoded `query_string` present
- Targeted WAF checks passed: bridge tests `34 passed`, WAF ingest route tests `8 passed`, WAF ingest use-case tests `4 passed`, and `docker compose config --quiet` passed
- Client-required real user access management/RBAC, 2FA, email notifications after detection, and the `CRITICAL >=90%` confidence tier are planned requirements tracked in `client-requirements.md`, not completed runtime behavior.

## Documentation Rules For This Repo

- Keep implementation docs tied to code and tests, not intention.
- If something is planned but not shipped, label it as planned.
- Keep setup, architecture, and status separate so each file has one job.
- Preserve academic documents, but mark them clearly when they are design artifacts instead of runtime truth.
- Keep operator docs separate from user-facing implementation docs.
