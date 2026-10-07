# Client Requirements

Last reconciled with current implementation documentation: 2026-10-08

This document records client-stated requirements that must be considered when
planning PD2 work. “Current Repo State” summarizes implementation status; it
does not prove live hosted configuration or deployment behavior. Use
[`architecture.md`](architecture.md) for current code boundaries and
[`project-ops/STATUS.md`](project-ops/STATUS.md) for dated verification.

## Security And Access Control

| Client Requirement | Engineering Consideration | Current Repo State | Tracker Direction |
|---|---|---|---|
| The system should be secure and controlled. | Keep browser access behind authenticated dashboard routes and keep backend access behind server-side BFF/internal API boundaries. | Implemented for the named-account/BFF boundary: hashed accounts, server-side RBAC, per-account `authz_version`, MFA, and backend bearer auth exist. | Production-grade distributed identity/throttling hardening remains separately tracked. |
| Implement user access management using RBAC with secure login. | Use a proven auth layer rather than hand-rolled sessions. Persist roles, include role claims in sessions, and enforce roles in route handlers and UI actions. | Implemented for the current DB-backed foundation: Auth.js accounts, `OWNER`/`ADMIN`/`ANALYST`/`VIEWER` claims, centralized role permissions, guarded BFF routes, and role-aware dashboard affordances. ML Health and ML Deployment are Owner-only at both the BFF and FastAPI boundaries. | Keep server route checks authoritative; managed identity remains future work. |
| The system should ensure strong account security. | Add login hardening and account protection controls. | Partial: generic login errors, Argon2id hashes, dummy verification, bounded per-identifier throttles, shared hash-work limits, database-expiring password-level MFA challenges, recovery, step-up, and safe JSON audit logs are implemented. | Add distributed throttling, persistent audit storage, and reviewed deployment controls. |
| The system shall implement two-factor authentication (2FA). | Prefer a proven provider or TOTP implementation with enrollment, recovery, reset, and factor-change handling. | Implemented behind fail-closed server-side availability flags: factor-aware TOTP enrollment, login MFA, backup/email recovery, mandatory re-enrollment, retry-safe handoff, and recent-TOTP step-up. A hosted Admin journey has a recorded verification in [Project Status](project-ops/STATUS.md); this is not live-state proof. | Redesign the MFA UI and audit disabled-flag semantics as post-merge work. |

## Threat Alerting

| Client Requirement | Engineering Consideration | Current Repo State | Tracker Direction |
|---|---|---|---|
| The system should provide timely alerts for detected threats. | Alerts should flow from WAF/ML detection to dashboard without manual refresh where feasible. | Implemented; a recorded test verified post-commit SSE through the authenticated BFF, no-refresh updates, browser reconnect/catch-up, and delivery on the named hosted domain. See [Project Status](project-ops/STATUS.md); this is not a live availability claim. | Keep single-process fan-out for the thesis runtime; shared fan-out remains future work for multi-instance deployment. |
| The system shall send email notifications after detection. | Use a transactional email provider/API; avoid building mail delivery infrastructure. Add duplicate-send protection and failure visibility. | The email-only outbox/worker boundary, supported templates, idempotency, deadlines, cancellation, lease reconciliation, terminal scrubbing, and protected active payloads are implemented. Resend domain/live delivery have a recorded verification in [Project Status](project-ops/STATUS.md), not a live availability guarantee. | Validate notification-worker retry, duplicate prevention, provider-failure handling, and required-worker health behavior. |

## Confidence Policy

| Client Requirement | Engineering Consideration | Current Repo State | Tracker Direction |
|---|---|---|---|
| Client standard includes a `CRITICAL >=90%` confidence tier. | Keep backend policy, schemas, frontend contracts, filters, mocks, and tests aligned. | Implemented across backend and frontend contracts without changing action values. Persisted-alert UI grouping/styling uses `confidence_level`; non-Normal enforcement-policy displays keep the Normal exception visible; confidence-tier badges always show the canonical tier. | Maintain CRITICAL as an explicit client-driven confidence tier. |

Implementation rule: confidence tier remains separate from attack severity. A request can have an attack class such as `SQL Injection` or `Code Injection`, while `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL` describe model certainty. `CRITICAL >=90%` is implemented without retraining, recalibration, or model artifact changes; historical rows are not retroactively reclassified, and legacy `severity` remains only a query compatibility alias.
