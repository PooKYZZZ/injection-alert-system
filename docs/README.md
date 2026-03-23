# Documentation

Last updated: 2026-03-23

This folder is the maintained documentation surface for the repository. It is intentionally trimmed to the documents that still map to the current codebase, test suite, and academic deliverables.

## Use This Folder By Purpose

### Current implementation
- `CONTEXT.md`
  - Short status snapshot for the repo as it exists today.
- `architecture.md`
  - Current system structure, request flow, active boundaries, and known gaps.
- `SETUP.md`
  - Honest local setup instructions for the repo in its current state.
- `CONTRIBUTING.md`
  - Workflow, guardrails, and validation steps for contributors.

### Operator docs
- `project-ops/STATUS.md`
  - Team and implementation status notes for current operator workflows.
- `project-ops/CONTEXT_BLOCK.md`
  - Compact context block for AI-assisted development sessions.
- `project-ops/LIVING_CHECKLIST.md`
  - Ongoing backend checklist and session handoff material.
- `PR_CHECKLIST_python314-upgrade.md`
  - Summary and verification checklist for the Python 3.14 / latest-compatible upgrade branch.
- `project-ops/DATA_AUDIT.md`
  - Full database-to-frontend audit findings (2026-03-20).

### Dataset and ML baseline
- `DATASET_RELEASE_SR_BH_CLEAN_v3.1.0.md`
  - Release note for the current cleaned dataset snapshot.
- `DATASET_BASELINE_SR_BH_v3.1.0.md`
  - Frozen baseline statistics and training metadata for the current dataset version.

### Academic documents
- `feasibility_report.md`
  - Feasibility and design report. Treat it as an academic design document, not the live implementation status page.
- `model_architecture_subsection.md`
  - Thesis subsection describing model selection rationale and citations.

## Verified Repo State (2026-03-22)

- Backend tests currently pass: **259 passed** (pytest)
- Frontend typecheck currently passes: `npm run typecheck`
- Frontend lint currently passes: `cd frontend && npm run lint`
- Frontend tests currently pass: **107 passed** (vitest)
- Current backend API surface includes:
  - protected: `POST /api/predict`, `POST /api/triage`, `GET /api/alerts`, `GET /api/alerts/{id}`, `PATCH /api/alerts/{id}/triage`, `GET /api/stats`, `GET /api/ml-health`
  - public: `POST /api/feedback`, `GET /health`, `GET /api/health`
- The Next.js dashboard BFF is wired for alerts, alert detail, triage, stats, and ML health through `frontend/lib/bff-client.ts`
- USE_MOCK_API=false (hitting real FastAPI)
- Hardcoded values audit completed: derived claims removed from dashboard, calibration claim fixed in ML health
- Docker Compose, Dockerfiles, and runnable ModSecurity wiring are not in the repo yet

## Documentation Rules For This Repo

- Keep implementation docs tied to code and tests, not intention.
- If something is planned but not shipped, label it as planned.
- Keep setup, architecture, and status separate so each file has one job.
- Preserve academic documents, but mark them clearly when they are design artifacts instead of runtime truth.
- Keep operator docs separate from user-facing implementation docs.
- `docs/checklists/` is intentionally left out of this refresh and should be treated separately.
