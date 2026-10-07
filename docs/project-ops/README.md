# Project Ops

This folder contains operator-focused working documents. Use the canonical map
below before following older execution logs or broad policy background.

## Canonical routes

| Purpose | Canonical document | Boundary |
|---|---|---|
| Development setup | [`../SETUP.md`](../SETUP.md) | Supported local prerequisites, environment, startup, and developer commands. |
| Tests | [`../SETUP.md`](../SETUP.md) | Canonical local commands and current validation routing. |
| Migrations | [`MIGRATION_ROLLBACK_RUNBOOK.md`](MIGRATION_ROLLBACK_RUNBOOK.md) | Backup requirement, downgrade testing, and rollback; the last checked revision is dated in STATUS. |
| Feature enablement | [`STATUS.md`](STATUS.md) and [`SMOKE_TEST_RUNBOOK.md`](SMOKE_TEST_RUNBOOK.md) | Status lists dated evidence; the smoke runbook owns controlled-local procedures. |
| Notifications | [`STATUS.md`](STATUS.md) | Dated provider/worker evidence and remaining validation; not a live delivery guarantee. |
| Recovery | [`STATUS.md`](STATUS.md) | Dated account-recovery and MFA evidence; not a live service check. |
| Break glass | [`MIGRATION_ROLLBACK_RUNBOOK.md`](MIGRATION_ROLLBACK_RUNBOOK.md) | Restricted-role and compatibility safeguards. |
| Thesis demo | [`SMOKE_TEST_RUNBOOK.md`](SMOKE_TEST_RUNBOOK.md) | Local WAF/demo procedures and clearly scoped operator checks; consult dated status before relying on prior evidence. |
| Cumulative unresolved implementation work | [`IMPLEMENTATION_GAP_REGISTER.md`](IMPLEMENTATION_GAP_REGISTER.md) | Stable-ID register; distinguishes implementation, local/CI/manual, and hosted evidence. |

[`STATUS.md`](STATUS.md) starts with the latest dated operator snapshot
(2026-10-07 in this checkout; it is not a live health feed);
[`IMPLEMENTATION_GAP_REGISTER.md`](IMPLEMENTATION_GAP_REGISTER.md) preserves
cumulative unresolved-work findings last reviewed on 2026-07-30 and must be
reconciled with current source before planning work; and
[`LIVING_CHECKLIST.md`](LIVING_CHECKLIST.md) is a historical working checklist
last substantively reviewed on 2026-07-30; revalidate its items before using it
for execution or handoff.

## Files

- `STATUS.md`
  - dated operator verification and earlier implementation/evidence records
- `IMPLEMENTATION_GAP_REGISTER.md`
  - canonical cumulative stable-ID register for unresolved implementation work
- `PR7_IMPLEMENTATION_SPEC.md`, `PR7_DESIGN_RATIONALE.md`, and
  `PR7_BLOCK_2_EVIDENCE.md`
  - current controlled-local CRITICAL/WAF contract, rationale, and evidence
- `LIVING_CHECKLIST.md`
  - historical working checklist last substantively reviewed on 2026-07-30;
    revalidate items before execution or handoff
- `DEMO_TARGET_WAF_PROOF.md`
  - verified local PD2 proof for the realistic `localhost:8089 -> demo-target-modsecurity -> demo-portal` WAF path and `demo-target-bridge` ingest
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
  policy/checklist background. Use `../SETUP.md` for local development,
  `../architecture.md` for current implementation and configuration boundaries,
  `STATUS.md` for dated runtime evidence, and the relevant runbook for an
  operational procedure.
- The superseded `IMPLEMENTATION_PLAN.md` was archived as
  `../archive/historical-plans/IMPLEMENTATION_PLAN_20260323.md`; use the
  current setup, architecture, status, and gap-register documents instead.
- `PR7_T0_EVIDENCE.md`, `SOURCE_CORRELATION_PROOF.md`, and
  `CLOUDFLARE_TARGET_INGRESS_ISOLATION_RUNBOOK.md` preserve historical T0 or
  external-ingress evidence. They do not authorize hosted or production
  enforcement; use the PR7 Block 2 evidence and contract for current local
  runtime behavior.

These files are operational notes, not the main user-facing documentation surface.
