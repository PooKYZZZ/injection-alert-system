# Project Ops

This folder contains operator-focused working documents. Use the canonical map
below before following older execution logs or broad policy background.

## Canonical routes

| Purpose | Canonical document | Boundary |
|---|---|---|
| Development setup | [`../SETUP.md`](../SETUP.md) | Supported local prerequisites, environment, startup, and developer commands. |
| Tests | [`../SETUP.md`](../SETUP.md) | Canonical local commands and current validation routing. |
| Migrations | [`MIGRATION_ROLLBACK_RUNBOOK.md`](MIGRATION_ROLLBACK_RUNBOOK.md) | Current V6.1 head, backup requirement, downgrade testing, and rollback. |
| Feature enablement | [`../SETUP.md`](../SETUP.md) | Auth, worker, provider, runtime flags, and container recreation. |
| Notifications | [`../architecture.md`](../architecture.md) | Outbox, protected payloads, worker, and Resend boundary. |
| Recovery | [`../architecture.md`](../architecture.md) | Recovery assurance and password/MFA boundaries. |
| Break glass | [`MIGRATION_ROLLBACK_RUNBOOK.md`](MIGRATION_ROLLBACK_RUNBOOK.md) | Restricted-role and compatibility safeguards. |
| Thesis demo | [`SMOKE_TEST_RUNBOOK.md`](SMOKE_TEST_RUNBOOK.md) | WAF proof commands and the verified Admin authentication journey. |
| Cumulative unresolved implementation work | [`IMPLEMENTATION_GAP_REGISTER.md`](IMPLEMENTATION_GAP_REGISTER.md) | Stable-ID register; distinguishes implementation, local/CI/manual, and hosted evidence. |

[`STATUS.md`](STATUS.md) is the current operator snapshot;
[`IMPLEMENTATION_GAP_REGISTER.md`](IMPLEMENTATION_GAP_REGISTER.md) owns
cumulative unresolved implementation work; and
[`LIVING_CHECKLIST.md`](LIVING_CHECKLIST.md) remains the operational execution
checklist and handoff material.

## Files

- `STATUS.md`
  - current implementation status and known repo gaps
- `IMPLEMENTATION_GAP_REGISTER.md`
  - canonical cumulative stable-ID register for unresolved implementation work
- `LIVING_CHECKLIST.md`
  - operational execution checklist and handoff material
- `DEMO_TARGET_WAF_PROOF.md`
  - verified local PD2 proof for the realistic `localhost:8089 -> demo-target-modsecurity -> demo-target-app` WAF path and `demo-target-bridge` ingest
- `SMOKE_TEST_RUNBOOK.md`
  - canonical smoke commands for normal Docker checks, the `8088` technical WAF proof path, and the `8089` final realistic demo-target path
- `../../reports/modsecurity-live-proof/e2e-proof.md`
  - checked-in local ModSecurity/OWASP CRS -> bridge -> FastAPI WAF ingest proof
- `MODSECURITY_AUDIT_LOG_POLICY.md`
  - local PD2 policy for ModSecurity JSONL audit logs, evidence fields, sensitive-data handling, retention, and rotation target
- `../client-requirements.md`
  - client-stated PD2 requirements that affect security, alerting, and confidence-tier planning
- `README.md`
  - explains the operator-doc subset itself

## Historical and background documents

- `AUTH_V6_EXECUTION_LOG.md` is append-only implementation history. Its old
  counts, intermediate migration heads, and earlier limitations are not current
  operating instructions.
- `MIGRATION_ROLLBACK_RUNBOOK.md`, `BACKUP_RESTORE_RUNBOOK.md`,
  `RETENTION_POLICY.md`, and `SUPABASE_RLS_HARDENING.md` remain general
  policy/checklist background. Current V6.1 migration and runtime guidance is
  in `../SETUP.md`, `../architecture.md`, `STATUS.md`, and
  `SMOKE_TEST_RUNBOOK.md`.

These files are operational notes, not the main user-facing documentation surface.
