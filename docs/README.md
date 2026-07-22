# Documentation

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
- `../CONTRIBUTING.md`
  - Workflow, guardrails, and validation steps for contributors.

### Operator docs
- `project-ops/STATUS.md`
  - Team and implementation status notes for current operator workflows.
- `project-ops/IMPLEMENTATION_GAP_REGISTER.md`
  - Canonical cumulative stable-ID register for unresolved implementation work;
    local, CI, manual, and hosted evidence remain distinct.
- `project-ops/LIVING_CHECKLIST.md`
  - Ongoing implementation checklist and handoff material.
- `project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`
  - ModSecurity audit-log policy for the verified local WAF proof path.
- `project-ops/DEMO_TARGET_WAF_PROOF.md`
  - Verified local PD2 proof for the realistic `localhost:8089` demo-target WAF path against the separate land-records portal.
- `project-ops/SMOKE_TEST_RUNBOOK.md`
  - Canonical smoke commands for the `8088` technical proof path, the `8089` realistic demo-target path, and the verified Admin authentication journey.
- `project-ops/MIGRATION_ROLLBACK_RUNBOOK.md`
  - Migration-head, backup, downgrade, application rollback, and runtime kill-switch guidance.
- `project-ops/README.md`
  - Canonical routing table for setup, tests, migrations, enablement,
    notifications, recovery, break glass, and thesis demonstrations.
- `../reports/modsecurity-live-proof/e2e-proof.md`
  - Checked-in local proof evidence for ModSecurity/OWASP CRS -> bridge -> FastAPI WAF ingest.

### Dataset and ML baseline
- `DATASET_RELEASE_SR_BH_CLEAN_v3.1.0.md`
  - Release note for the current cleaned dataset snapshot.
- `DATASET_BASELINE_SR_BH_v3.1.0.md`
  - Frozen baseline statistics and training metadata for the current dataset version.

## Current project state

This index intentionally avoids duplicating fast-changing status, route, and
evidence details. Use the canonical documents below:

- [Project context](CONTEXT.md)
- [Architecture](architecture.md)
- [Developer setup](SETUP.md)
- [Operator status](project-ops/STATUS.md)
- [Implementation gap register](project-ops/IMPLEMENTATION_GAP_REGISTER.md)
- [Execution checklist](project-ops/LIVING_CHECKLIST.md)

## Documentation ownership

| Subject | Canonical source |
|---|---|
| Project overview | `README.md` |
| Current implementation | `CONTEXT.md` |
| Runtime architecture | `architecture.md` |
| Developer setup | `SETUP.md` |
| Operator snapshot | `project-ops/STATUS.md` |
| Outstanding work | `project-ops/IMPLEMENTATION_GAP_REGISTER.md` |
| Execution checklist | `project-ops/LIVING_CHECKLIST.md` |
| Historical evidence | `reports/` |

## Documentation Rules For This Repo

- Keep implementation docs tied to code and tests, not intention.
- If something is planned but not shipped, label it as planned.
- Keep setup, architecture, and status separate so each file has one job.
- Preserve academic documents, but mark them clearly when they are design artifacts instead of runtime truth.
- Keep operator docs separate from user-facing implementation docs.
