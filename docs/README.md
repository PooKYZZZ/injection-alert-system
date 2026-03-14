# Documentation

Last updated: 2026-03-14

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

## Verified Repo State

- Backend tests currently pass: `44 passed`
- Frontend typecheck currently passes: `npm run typecheck`
- Current backend routes are limited to:
  - `POST /api/predict`
  - `GET /api/alerts`
  - `POST /api/feedback`
  - `/health` and `/api/health`
- The Next.js dashboard exists, but the BFF is still mixed:
  - `stats` can proxy to FastAPI
  - `alerts`, `alert detail`, and `ml-health` are still mock-first or stubbed
- Docker Compose, Dockerfiles, and runnable ModSecurity wiring are not in the repo yet

## Documentation Rules For This Repo

- Keep implementation docs tied to code and tests, not intention.
- If something is planned but not shipped, label it as planned.
- Keep setup, architecture, and status separate so each file has one job.
- Preserve academic documents, but mark them clearly when they are design artifacts instead of runtime truth.
- Keep operator docs separate from user-facing implementation docs.
- `docs/checklists/` is intentionally left out of this refresh and should be treated separately.
