# Client Requirements

Last updated: 2026-06-22

This document records client-stated requirements that must be considered when planning PD2 work. It does not claim that every item is already implemented.

## Security And Access Control

| Client Requirement | Engineering Consideration | Current Repo State | Tracker Direction |
|---|---|---|---|
| The system should be secure and controlled. | Keep browser access behind authenticated dashboard routes and keep backend access behind server-side BFF/internal API boundaries. | Partially implemented: dashboard/BFF session checks and backend bearer auth exist. | Continue hardening around real accounts, RBAC, login controls, and 2FA. |
| Implement user access management using RBAC with secure login. | Use a proven auth layer rather than hand-rolled sessions. Persist roles, include role claims in sessions, and enforce roles in route handlers and UI actions. | Partially implemented: Auth.js credentials login exists, but it is still demo-style and not a real user/RBAC system. | Replace demo login with real user accounts, then implement Admin/Analyst RBAC. |
| The system should ensure strong account security. | Add login hardening and account protection controls. | Partially implemented: route/session boundary exists; strong account controls are not yet complete. | Add login throttling/lockout policy, audit records, secure recovery path, and 2FA. |
| The system shall implement two-factor authentication (2FA). | Prefer a proven provider or TOTP implementation with enrollment, recovery, reset, and factor-change handling. | Not implemented. | Treat 2FA as a client requirement after the real-account/RBAC foundation is in place. |

## Threat Alerting

| Client Requirement | Engineering Consideration | Current Repo State | Tracker Direction |
|---|---|---|---|
| The system should provide timely alerts for detected threats. | Alerts should flow from WAF/ML detection to dashboard without manual refresh where feasible. | Partially implemented: alerts exist in the dashboard, but real-time/push alerting is not complete. | Add real-time dashboard alerts after the WAF-to-backend path is proven. |
| The system shall send email notifications after detection. | Use a transactional email provider/API; avoid building mail delivery infrastructure. Add duplicate-send protection and failure visibility. | Not implemented. | Add email notifications for HIGH/CRITICAL or client-defined alert classes after detection. |

## Confidence Policy

| Client Requirement | Engineering Consideration | Current Repo State | Tracker Direction |
|---|---|---|---|
| Client standard includes a `CRITICAL >=90%` confidence tier. | Keep backend policy, schemas, frontend contracts, filters, mocks, and tests aligned. | Implemented across backend and frontend contracts without changing action values. Persisted-alert UI grouping/styling uses `confidence_level`; non-Normal enforcement-policy displays keep the Normal exception visible; confidence-tier badges always show the canonical tier. | Maintain CRITICAL as an explicit client-driven confidence tier. |

Implementation rule: confidence tier remains separate from attack severity. A request can have an attack class such as `SQL Injection` or `Code Injection`, while `LOW`, `MEDIUM`, `HIGH`, and `CRITICAL` describe model certainty. `CRITICAL >=90%` is implemented without retraining, recalibration, or model artifact changes; historical rows are not retroactively reclassified, and legacy `severity` remains only a query compatibility alias.
