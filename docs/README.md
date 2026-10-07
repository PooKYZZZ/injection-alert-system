# Documentation Index

This page routes readers to the right document. It is an index, not a guarantee
that every dated proof or status note is still current. Check the date and scope
inside operational documents, and verify the live repository/runtime before
using them to make deployment decisions.

## Start here

- [Project overview](../README.md) — what CyberTrace is, its boundaries, and
  how to begin.
- [Local setup](SETUP.md) — direct development and isolated Docker Compose
  workflows. Hosted-style commands are operator-only.
- [Architecture](architecture.md) — application boundaries, data flow, and
  implementation limitations.
- [Contributing](../CONTRIBUTING.md) — change workflow, repository guardrails,
  and validation commands.

## Current source and date-sensitive records

- [Project Ops index](project-ops/README.md) — routes to runbooks and evidence.
- [Project Ops status](project-ops/STATUS.md) — the latest bounded operator
  verification is at the top; later sections preserve older dated records.
- [Implementation gap register](project-ops/IMPLEMENTATION_GAP_REGISTER.md) —
  cumulative gaps last reviewed on 2026-07-30. Reconcile it with current code
  before treating it as the active backlog.
- [Project context](CONTEXT.md) — dated implementation and history notes,
  editorially reconciled on 2026-10-08; use architecture and operator status
  for current source and deployment evidence.
- [Client requirements](client-requirements.md) — requirements stated by the
  client; this document is not proof that every requirement is implemented.

## Evidence and operational guidance

- [Smoke-test runbook](project-ops/SMOKE_TEST_RUNBOOK.md) — local smoke
  procedures and their evidence boundaries.
- [ModSecurity audit-log policy](project-ops/MODSECURITY_AUDIT_LOG_POLICY.md) —
  local WAF audit data handling and retention guidance.
- [Migration rollback runbook](project-ops/MIGRATION_ROLLBACK_RUNBOOK.md) —
  migration and rollback safeguards.
- [Local ModSecurity/OWASP CRS proof](../reports/modsecurity-live-proof/e2e-proof.md)
  — dated evidence for the local audit-log bridge path; not hosted or production
  proof.
- [Implementation-gap details](project-ops/IMPLEMENTATION_GAP_REGISTER.md) —
  date-stamped cumulative planning/evidence.

## Documentation ownership

| Subject | Main document |
|---|---|
| Project overview | [README](../README.md) |
| Local setup | [SETUP](SETUP.md) |
| Architecture | [Architecture](architecture.md) |
| Contributor workflow | [CONTRIBUTING](../CONTRIBUTING.md) |
| Operator procedures | [Project Ops](project-ops/README.md) |
| Dated operator verification | [STATUS](project-ops/STATUS.md) |
| Academic/history snapshots | [Archive](archive/) and dated reports |

## Documentation rules

- Describe behavior verified in code and tests; label proposals as planned.
- Keep the overview, setup, architecture, and operational evidence in their
  respective documents rather than copying long detail into the project README.
- Keep repository-relative links so they work in GitHub and local clones.
- Do not treat an old test count, migration revision, screenshot, or local
  demonstration as proof of current hosted behavior.
