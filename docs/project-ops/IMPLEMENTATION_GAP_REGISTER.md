# Cumulative Implementation Gap Register

**Reviewed:** 2026-07-22

**Repository baseline:** `master` merge `62fc168` / merged PR #90

This is the canonical cumulative register for unresolved implementation work. Only
code, configuration, tests, and current runtime wiring outrank documentation.
Entries are cumulative: IDs never renumber, and local, CI, manual, and hosted
evidence are distinct evidence classes.

## Immediate priority queue

| ID | Priority | Status | Area | Target |
|---|---|---|---|---|
| BLOCK-001 | HIGH | BLOCKED | Production rollout | Deployment gate |
| BLOCK-002 | HIGH | BLOCKED | Trusted source proof | Deployment gate |
| GAP-001 | HIGH | NOT_STARTED | HIGH enforcement | PR6 |
| GAP-002 | HIGH | NOT_STARTED | CRITICAL/WAF enforcement | PR7 |
| BUG-001 | HIGH | KNOWN_BUG | Enforcement | Maintenance |
| BUG-002 | MEDIUM | KNOWN_BUG | Migration | Maintenance |

Detailed entries below remain grouped by stable ID and are the source of truth.

ID prefixes are permanent historical identifiers. The `Status` field is
authoritative and may change over time; do not infer current status from an ID
prefix.

### BLOCK-001 — Hosted PR5 topology and production rollout gate

Status: BLOCKED

Priority:
HIGH

Area:
Active enforcement deployment

Current implementation: Controlled local LOW/MEDIUM enforcement exists; production mode is off.

Missing: Direct Cloudflare source/topology, Pseudo IPv4, origin-isolation, and production Turnstile proof.

Evidence:

- `docs/project-ops/STATUS.md`
- `reports/active-enforcement/PR5_CONTROLLED_E2E_PROOF.md`
- `web_app/config.py`

Requirement: Production rollout requires direct topology and source-trust proof.

Impact: Production ENFORCE cannot be evidenced or enabled.

Dependencies / blockers: Cloudflare/operator network proof and separately approved rollout.

Recommended next step: Run operator proof, then seek separate rollout approval.

Introduced / identified: PR5 review.

Last reviewed: 2026-07-22

### LIMIT-001 — Exact PR5 threshold screenshot pairs were not retained

Status: KNOWN_LIMITATION

Priority:
LOW

Area:
PR5 evidence

Current implementation: Functional threshold transitions were observed.

Missing: Clean LOW 5→6 and MEDIUM 10→11 screenshot pairs.

Evidence:

- `docs/project-ops/STATUS.md`
- `reports/active-enforcement/PR5_CONTROLLED_E2E_PROOF.md`

Requirement: None beyond stronger thesis evidence if requested.

Impact: Exact-boundary visual evidence is incomplete.

Dependencies / blockers: Disposable local E2E environment.

Recommended next step: Rerun only if stronger thesis evidence is needed.

Introduced / identified: PR5 controlled E2E.

Last reviewed: 2026-07-22

### GAP-001 — PR6 HIGH application blocking

Status: NOT_STARTED

Priority:
HIGH

Area:
Active enforcement

Current implementation: HIGH recommendations exist, but the active query excludes them.

Missing: HIGH application-blocking behavior.

Evidence:

- `docs/project-ops/STATUS.md`
- `docs/architecture.md`
- `web_app/infrastructure/repositories/enforcement_recommendation_repository.py`

Requirement: Separately scoped PR6.

Impact: HIGH remains non-disruptive.

Dependencies / blockers: PR6 scope and deployment topology.

Recommended next step: Create a separately scoped PR6.

Introduced / identified: PR5 acceptance state.

Last reviewed: 2026-07-22

### GAP-002 — PR7 CRITICAL/WAF enforcement

Status: NOT_STARTED

Priority:
HIGH

Area:
WAF enforcement

Current implementation: No WAF mutation or CRITICAL active path exists.

Missing: CRITICAL/WAF enforcement.

Evidence:

- `docs/project-ops/STATUS.md`
- `reports/active-enforcement/README.md`

Requirement: Separately scoped PR7 after PR6 and topology work.

Impact: CRITICAL remains non-disruptive.

Dependencies / blockers: PR6 and trusted deployment topology.

Recommended next step: Scope PR7 only after those prerequisites.

Introduced / identified: PR5 acceptance state.

Last reviewed: 2026-07-22

### DEFER-001 — Alternative high-throughput enforcement state backend

Status: DEFERRED

Priority:
MEDIUM

Area:
Enforcement scalability

Current implementation: PostgreSQL counters exist.

Current: PostgreSQL provides durable shared counters and grants.

Deferred: An additional Redis-style state layer.

Evidence:

- `docs/project-ops/STATUS.md`
- `migrations/versions/20260721_000024_add_active_enforcement_state.py`

Requirement: Reassess only if a demonstrated scale requirement justifies another state system.

Impact: No additional low-latency or specialized distributed cache layer is provided or currently required.

Dependencies / blockers: Demonstrated multi-instance requirement.

Recommended next step: Reassess only if that need is demonstrated.

Introduced / identified: PR5 scope.

Last reviewed: 2026-07-22

### GAP-003 — PR8 model packaging

Status: NOT_STARTED

Priority:
HIGH

Area:
ML packaging

Current implementation: Promotion tooling exists.

Missing: Complete PR8 packaging work.

Evidence:

- `docs/project-ops/STATUS.md`
- `ml_model/export/promote_final_training_run.py`

Requirement: Separately scoped PR8.

Impact: PR8 packaging is not complete.

Dependencies / blockers: PR8 design and validation scope.

Recommended next step: Create a separately scoped PR8.

Introduced / identified: PR5 acceptance state.

Last reviewed: 2026-07-22

### GAP-004 — PR9 candidate retraining pipeline

Status: NOT_STARTED

Priority:
MEDIUM

Area:
ML retraining

Current implementation: Retraining package is design-only.

Missing: Scheduler and runnable entrypoint.

Evidence:

- `docs/project-ops/STATUS.md`
- `ml_model/retraining/README.md`

Requirement: Separately scoped PR9.

Impact: No candidate retraining pipeline is claimed.

Dependencies / blockers: PR9 design, data, and evaluation criteria.

Recommended next step: Create a separately scoped PR9.

Introduced / identified: PR5 acceptance state.

Last reviewed: 2026-07-22

### GAP-005 — Model integrity and promotion gates

Status: PARTIAL

Priority:
MEDIUM

Area:
ML promotion

Current implementation: Archive/rollback tooling exists.

Missing: Manifest checksum validation and closed challenger/quality gate.

Evidence:

- `docs/architecture.md` (current feature-state matrix)
- `ml_model/export/promote_final_training_run.py`

Requirement: No auto-promotion.

Impact: Promotion readiness remains incomplete.

Dependencies / blockers: Approved evaluation thresholds and manifest design.

Recommended next step: Add checksum and approved gate without auto-promotion.

Introduced / identified: PD2 tracker.

Last reviewed: 2026-07-22

### GAP-006 — Wazuh export-only compatibility

Status: DEFERRED

Priority:
LOW

Area:
Observability export

Current implementation: No Wazuh export exists.

Missing: JSON/JSONL export-only compatibility.

Evidence:

- `docs/project-ops/STATUS.md`
- `docs/architecture.md`

Requirement: Full SIEM remains deferred.

Impact: No Wazuh export is available.

Dependencies / blockers: PD2 time and scope approval.

Recommended next step: Consider only if JSON/JSONL export is approved.

Introduced / identified: Current architecture gap.

Last reviewed: 2026-07-22

### GAP-007 — Automated WAF log rotation and production retention

Status: PARTIAL

Priority:
MEDIUM

Area:
WAF operations

Current implementation: JSONL policy and format exist.

Missing: Automated rotation and production retention.

Evidence:

- `docs/project-ops/STATUS.md`
- `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`

Requirement: No physical DELETE.

Impact: Manual/local handling is the only documented path.

Dependencies / blockers: Operator-safe archive/rotation design.

Recommended next step: Design archive/rotation without physical delete.

Introduced / identified: WAF policy review.

Last reviewed: 2026-07-22

### GAP-008 — ModSecurity operator-path decision

Status: NOT_STARTED

Priority:
MEDIUM

Area:
Deployment architecture

Current implementation: Local Compose proofs exist.

Missing: Decision whether it is a supported browser-facing operator path.

Evidence:

- `docs/CONTEXT.md`

Requirement: Explicit architecture decision.

Impact: Operator support boundary is undecided.

Dependencies / blockers: Maintainer/product decision.

Recommended next step: Record an explicit architecture decision.

Introduced / identified: Living checklist.

Last reviewed: 2026-07-22

### GAP-009 — Additional attack-class demo evidence

Status: PARTIAL

Priority:
MEDIUM

Area:
Demonstration evidence

Current implementation: SQLi is proven.

Missing: Code/server injection-like and other attack-like probe evidence.

Evidence:

- `reports/modsecurity-live-proof/demo-target-crs-proof.md`

Requirement: Safe, correlated demonstration probes.

Impact: Demo evidence covers fewer attack classes.

Dependencies / blockers: Defined safe probes and capture procedure.

Recommended next step: Define probes and capture correlated proof.

Introduced / identified: PD2 demo checklist.

Last reviewed: 2026-07-22

### LIMIT-002 — Minimal metrics boundary

Status: DEFERRED

Priority:
LOW

Area:
Observability

Current implementation: Stats, ML health, and bridge summaries exist.

Missing: Separate bridge/email metrics endpoint.

Evidence:

- `docs/project-ops/STATUS.md`
- `docs/architecture.md` (current feature-state matrix)

Requirement: Expand only for demonstrated operator need.

Impact: Metrics remain intentionally minimal.

Dependencies / blockers: Demonstrated operator need.

Recommended next step: Expand only if needed.

Introduced / identified: PD2 tracker.

Last reviewed: 2026-07-22

### GAP-010 — Notification worker operational validation

Status: PARTIAL

Priority:
MEDIUM

Area:
Notifications

Current implementation: Outbox/worker/Resend and live delivery exist.

Missing: Tested retry, duplicate prevention, provider failure, and required-worker health deployment behavior.

Evidence:

- `docs/project-ops/STATUS.md`
- `docs/architecture.md` (current feature-state matrix)

Requirement: Controlled operational validation.

Impact: Deployment failure behavior is not fully evidenced.

Dependencies / blockers: Controlled provider-failure environment.

Recommended next step: Run provider-failure/retry/health test.

Introduced / identified: PR83 follow-up.

Last reviewed: 2026-07-22

### DEFER-002 — Distributed login throttling and persistent audit storage

Status: DEFERRED

Priority:
MEDIUM

Area:
Authentication operations

Current implementation: Local/process protections are implemented.

Missing: Distributed throttling and persistent audit storage.

Evidence:

- `docs/project-ops/STATUS.md`
- `docs/architecture.md` (current feature-state matrix)

Requirement: Shared runtime approval.

Impact: Protections remain local/process-bound.

Dependencies / blockers: Approved shared runtime.

Recommended next step: Reassess only with that approval.

Introduced / identified: Login-hardening follow-up.

Last reviewed: 2026-07-22

### DEFER-003 — MFA enrollment UI redesign

Status: DEFERRED

Priority:
LOW

Area:
MFA usability

Current implementation: Functional verified UI exists.

Missing: Usability redesign.

Evidence:

- `docs/project-ops/STATUS.md`

Requirement: Usability-only work.

Impact: No security behavior is missing.

Dependencies / blockers: Separate UI scope.

Recommended next step: Create a usability-only PR.

Introduced / identified: PR83 follow-up.

Last reviewed: 2026-07-22

### DEFER-004 — Backup-code UI redesign

Status: DEFERRED

Priority:
LOW

Area:
Recovery usability

Current implementation: Functional recovery exists.

Missing: Backup-code UI redesign.

Evidence:

- `docs/project-ops/STATUS.md`

Requirement: Usability-only work.

Impact: No recovery behavior is missing.

Dependencies / blockers: Separate UI scope.

Recommended next step: Create a usability-only PR.

Introduced / identified: PR83 follow-up.

Last reviewed: 2026-07-22

### GAP-011 — Disabled MFA feature-flag semantics audit

Status: PARTIAL

Priority:
MEDIUM

Area:
MFA controls

Current implementation: Flags fail closed.

Missing: Explicit enrollment-disabled behavior audit.

Evidence:

- `docs/project-ops/STATUS.md`

Requirement: Preserve 404 and authorization behavior.

Impact: Disabled-mode assurance is incomplete.

Dependencies / blockers: Focused behavior audit/tests.

Recommended next step: Audit without weakening 404/auth behavior.

Introduced / identified: PR83 follow-up.

Last reviewed: 2026-07-22

### DEFER-005 — Conditional local Playwright null-session investigation

Status: DEFERRED

Priority:
LOW

Area:
Authentication E2E

Current implementation: Remote auth E2E passes.

Missing: Reproduction, if the local issue recurs.

Evidence:

- `docs/project-ops/STATUS.md`

Requirement: Investigate only on recurrence.

Impact: No current failing remote path is claimed.

Dependencies / blockers: Reproducible local failure.

Recommended next step: Capture reproduction if it recurs.

Introduced / identified: PR83 follow-up.

Last reviewed: 2026-07-22

### DEFER-006 — Auth.js beta upgrade

Status: DEFERRED

Priority:
MEDIUM

Area:
Frontend dependencies

Current implementation: `next-auth 5.0.0-beta.30` is current.

Missing: Separate compatibility upgrade.

Evidence:

- `frontend/package.json`
- `docs/project-ops/STATUS.md`

Requirement: Full authentication suite before upgrading.

Impact: Beta dependency remains in use.

Dependencies / blockers: Separate compatibility scope.

Recommended next step: Use a dedicated PR and full auth suite.

Introduced / identified: PR83 follow-up.

Last reviewed: 2026-07-22

### DEFER-007 — Passkeys/WebAuthn

Status: DEFERRED

Priority:
LOW

Area:
Authentication roadmap

Current implementation: Later enhancement only.

Missing: Product approval and design.

Evidence:

- `docs/project-ops/STATUS.md`

Requirement: Product approval before design.

Impact: No passkey support is claimed.

Dependencies / blockers: Product approval.

Recommended next step: Obtain approval before design.

Introduced / identified: PR83 follow-up.

Last reviewed: 2026-07-22

### GAP-012 — Backup, restore, and retention automation

Status: DEFERRED

Priority:
LOW

Area:
Data operations

Current implementation: Runbooks and policies exist.

Missing: Automation; acceptance remains broad.

Evidence:

- `docs/project-ops/BACKUP_RESTORE_RUNBOOK.md`
- `docs/project-ops/RETENTION_POLICY.md`

Requirement: Narrow operator requirement first.

Impact: Procedures remain manual.

Dependencies / blockers: Defined automation target and acceptance criteria.

Recommended next step: Narrow operator requirement before implementation.

Introduced / identified: Operations checklist.

Last reviewed: 2026-07-22

### GAP-013 — Repo-managed Supabase policy/RLS evidence export

Status: PARTIAL

Priority:
MEDIUM

Area:
Database assurance

Current implementation: RLS/revocations/no policies are documented.

Missing: Repo-managed hosted/export evidence.

Evidence:

- `docs/project-ops/SUPABASE_RLS_HARDENING.md`

Requirement: Safe read-only export/verification design.

Impact: Hosted policy evidence is incomplete.

Dependencies / blockers: Read-only export design and reviewed target.

Recommended next step: Design safe read-only export/verification.

Introduced / identified: Operations checklist.

Last reviewed: 2026-07-22

### GAP-014 — Dashboard mitigation/security polish and chart-warning follow-up

Status: PARTIAL

Priority:
LOW

Area:
Dashboard UX

Current implementation: Dashboard exists.

Missing: Narrow mitigation/security pages and reproducible chart warning.

Evidence:

- `docs/architecture.md` (current feature-state matrix)

Requirement: Stable reproduction before scope.

Impact: Follow-up is broad and not reproducible yet.

Dependencies / blockers: Stable warning reproduction.

Recommended next step: Reproduce and scope separately.

Introduced / identified: Tracker follow-up.

Last reviewed: 2026-07-22

### DEFER-008 — Hosted PR4 shadow enablement and latency

Status: DEFERRED

Priority:
MEDIUM

Area:
Shadow enforcement deployment

Current implementation: Local proof exists.

Missing: Hosted topology measurement and timeout selection.

Evidence:

- `docs/project-ops/STATUS.md`
- `reports/shadow-enforcement/e2e-proof.md`

Requirement: Topology evidence before enablement.

Impact: Hosted shadow remains disabled.

Dependencies / blockers: Hosted topology/latency evidence.

Recommended next step: Revisit only after topology proof.

Introduced / identified: PR4 post-merge validation.

Last reviewed: 2026-07-22

### BLOCK-002 — Trusted-source hosted verification

Status: BLOCKED

Priority:
HIGH

Area:
Source verification

Current implementation: Hosted regression exists, but mode remains unverified.

Missing: Pseudo IPv4, Worker, direct-origin, and immediate-peer facts.

Evidence:

- `docs/project-ops/STATUS.md`
- `docs/project-ops/SOURCE_CORRELATION_PROOF.md`

Requirement: Direct operator/network proof.

Impact: Trusted hosted identity is not claimed.

Dependencies / blockers: Cloudflare and network topology observations.

Recommended next step: Run direct operator/network proof.

Introduced / identified: Trusted-source correlation review.

Last reviewed: 2026-07-22

### LIMIT-003 — SSE single-process and no durable replay

Status: KNOWN_LIMITATION

Priority:
MEDIUM

Area:
Real-time alerts

Current implementation: SSE is implemented and hosted-verified.

Missing: Multi-worker fan-out, durable replay/Last-Event-ID, and latency benchmark.

Evidence:

- `docs/project-ops/STATUS.md`
- `web_app/presentation/api/routes.py`

Requirement: Retain unless scaling is approved.

Impact: Single-process delivery boundary.

Dependencies / blockers: Scaling requirement.

Recommended next step: Retain unless scaling requirement is approved.

Introduced / identified: PR2 scope.

Last reviewed: 2026-07-22

### LIMIT-004 — Telegram provider/hosted delivery guarantees

Status: KNOWN_LIMITATION

Priority:
MEDIUM

Area:
Telegram notifications

Current implementation: Local implementation and tests exist.

Missing: Live hosted proof and external exactly-once guarantee.

Evidence:

- `docs/project-ops/STATUS.md`

Requirement: Do not claim exactly-once delivery.

Impact: Hosted Telegram delivery is unverified.

Dependencies / blockers: Approved hosted provider validation.

Recommended next step: Validate provider if approved, without exactly-once claim.

Introduced / identified: PR3 status.

Last reviewed: 2026-07-22

### BUG-001 — MEDIUM retry interval can outlive recommendation expiry

Status: KNOWN_BUG

Priority:
HIGH

Area:
Active enforcement timing

Current implementation: Retry calculation uses only `window_end`.

Missing: Cap at recommendation expiry.

Evidence:

- `web_app/application/enforcement_use_cases.py`
- Unresolved PR90 review thread

Requirement: Retry interval must not outlive recommendation expiry.

Impact: MEDIUM retry guidance can exceed recommendation lifetime.

Dependencies / blockers: Focused failing test.

Recommended next step: Add test, then cap at `min(window_end, expires_at)`.

Introduced / identified: PR90 review.

Last reviewed: 2026-07-22

### BUG-002 — SQLite PR5 constraint rebuild drops parent server defaults

Status: KNOWN_BUG

Priority:
MEDIUM

Area:
SQLite migration

Current implementation: SQLite `copy_from` rebuild omits parent defaults.

Missing: Preserved `enforcement_mode` and `created_at` defaults.

Evidence:

- `migrations/versions/20260721_000024_add_active_enforcement_state.py`
- `migrations/versions/20260720_000023_add_shadow_enforcement_recommendations.py`
- `tests/migrations/test_active_enforcement_migration.py`

Requirement: Preserve parent defaults during SQLite rebuild.

Impact: Insert/default behavior can diverge after migration.

Dependencies / blockers: Focused migration default test.

Recommended next step: Add failing insert/default test, then preserve defaults.

Introduced / identified: PR90 review.

Last reviewed: 2026-07-22

### LIMIT-005 — Turnstile verification lacks one total deadline

Status: KNOWN_LIMITATION

Priority:
MEDIUM

Area:
Turnstile verification

Current implementation: HTTPX phase timeouts exist.

Missing: Outer end-to-end deadline; runtime impact is unobserved.

Evidence:

- `web_app/infrastructure/turnstile.py`
- PR90 review thread

Requirement: Total deadline only if authorized by focused evidence.

Impact: Combined phase duration is not bounded by one deadline.

Dependencies / blockers: Slow-phase test and authorization.

Recommended next step: Add slow-phase test, then consider a total-deadline wrapper.

Introduced / identified: PR90 review.

Last reviewed: 2026-07-22

### BUG-003 — Enforcement counter window can retain stale duration after configuration change

Status: KNOWN_BUG

Priority:
MEDIUM

Area:
Enforcement counters

Current implementation: Conflict identity omits duration and update does not reset `window_end`.

Missing: Safe duration-change behavior.

Evidence:

- `web_app/infrastructure/repositories/enforcement_recommendation_repository.py`
- PR90 review thread

Requirement: Configuration changes must not retain stale counter duration.

Impact: Existing counter window can outlive new duration settings.

Dependencies / blockers: Focused duration-change test.

Recommended next step: Add test, then reset or separate state safely.

Introduced / identified: PR90 review.

Last reviewed: 2026-07-22
