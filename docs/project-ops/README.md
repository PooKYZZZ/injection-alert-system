# Project Ops

This folder contains operator-focused working documents. Use the canonical map
below before following older execution logs or broad policy background.

## Canonical routes

| Purpose | Canonical document | Boundary |
|---|---|---|
| Development setup | [`../SETUP.md`](../SETUP.md) | Supported local prerequisites, environment, startup, and developer commands. |
| Tests | [`../SETUP.md`](../SETUP.md) | Canonical local commands; PR #83 exact security evidence is in [`PR83_THESIS_EVIDENCE.md`](PR83_THESIS_EVIDENCE.md). |
| Migrations | [`CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md`](CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md) | Current V6.1 head, hosted approval gate, payload compatibility, and rollback. |
| Feature enablement | [`CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md`](CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md) | Auth, worker, provider, target identity, and smoke gates. |
| Notifications | [`CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md`](CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md) | Payload key, worker, provider, reconciliation, and terminal scrub operations. |
| Recovery | [`CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md`](CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md) | Backup/email recovery enablement and verification boundary. |
| Break glass | [`CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md`](CYBERTRACE_V61_DEPLOYMENT_RUNBOOK.md) | Restricted role approval, invocation, audit, and access revocation. |
| Thesis demo | [`PR83_THESIS_EVIDENCE.md`](PR83_THESIS_EVIDENCE.md) | Five disposable authentication journeys; WAF demo commands remain in [`SMOKE_TEST_RUNBOOK.md`](SMOKE_TEST_RUNBOOK.md). |

[`STATUS.md`](STATUS.md) is the current operator snapshot and
[`LIVING_CHECKLIST.md`](LIVING_CHECKLIST.md) is the maintained task ledger.
[`PR83_EXECUTION_RECORD.md`](PR83_EXECUTION_RECORD.md) preserves command-level
implementation evidence.

## Files

- `STATUS.md`
  - current implementation status and known repo gaps
- `LIVING_CHECKLIST.md`
  - ongoing task checklist and handoff material
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
  `RETENTION_POLICY.md`, `PRODUCTION_EDGE_CHECKLIST.md`, and
  `SUPABASE_RLS_HARDENING.md` remain general policy/checklist background. For
  the current V6.1 migration and enablement sequence, use the canonical
  deployment runbook above.

These files are operational notes, not the main user-facing documentation surface.
