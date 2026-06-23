# PD2 Priority Tracker

Purpose: track what still needs to be implemented for PD2 without claiming that planned features already exist.

Legend:

* **Urgency**: how soon this matters for the PD2 demo/defense.
* **Difficulty**: how hard it is to implement correctly in the current codebase.
* **Status**:
  * `[x] Done`
  * `[~] Partial`
  * `[ ] Not started`
  * `[!] Blocked`

## Evidence Basis

This tracker is based on:

* Current repo inspection:

  * `web_app/application/triage_use_case.py` currently maps confidence to `ALLOWED`, `THROTTLED`, and `BLOCKED`.
  * `frontend/auth.ts` currently uses a credentials login with a demo-style SOC user.
  * `ml_model/retraining/README.md` says the retraining pipeline is still design-level only.
  * `reports/modsecurity-live-proof/e2e-proof.md` proves the local ModSecurity/OWASP CRS -> bridge -> FastAPI WAF ingest path through `localhost:8088`.
  * `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md` documents the local ModSecurity audit-log policy.
  * `docs/architecture.md` says Redis-backed enforcement is planned, not implemented.

* Client requirements:

  * The system should be secure and controlled.
  * The system should implement user access management using RBAC with secure login.
  * The system should provide timely alerts for detected threats.
  * The system shall send email notifications after detection.
  * The system should ensure strong account security.
  * The system shall implement two-factor authentication (2FA).
  * The client standard includes a `CRITICAL >=90%` confidence tier.
  * Canonical requirement notes live in `docs/client-requirements.md`.

* External implementation references:

  * OWASP CRS: https://owasp.org/www-project-modsecurity-core-rule-set/
  * ModSecurity reference manual: https://github.com/owasp-modsecurity/ModSecurity/wiki/Reference-Manual-%28v2.x%29
  * Python `asyncio.Queue`: https://docs.python.org/3/library/asyncio-queue.html
  * FastAPI background tasks: https://fastapi.tiangolo.com/tutorial/background-tasks/
  * MDN Server-Sent Events: https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events
  * Auth.js RBAC: https://authjs.dev/guides/role-based-access-control
  * OWASP Authentication Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html
  * OWASP MFA Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html
  * Redis rate limiting: https://redis.io/docs/latest/develop/use-cases/rate-limiter/
  * Cloudflare Turnstile server validation: https://developers.cloudflare.com/turnstile/get-started/server-side-validation/
  * PostgreSQL backup/restore: https://www.postgresql.org/docs/current/app-pgdump.html
  * Alembic migrations: https://alembic.sqlalchemy.org/
  * Wazuh documentation: https://documentation.wazuh.com/
  * Google MLOps continuous training: https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning
  * AWS retraining guidance: https://docs.aws.amazon.com/machine-learning/latest/dg/retraining-models-on-new-data.html

## Priority List

| Status | Task                                                             | Urgency     | Difficulty    | Why This Is Ranked Here                                                                                                                                                                                                   |
| ---- | ---------------------------------------------------------------- | ----------- | ------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [x]  | Build a small demo target website                                | Critical    | Medium        | External target exists at `G:\AI\land-records-portal` with WAF route inventory and live Playwright PASS evidence. Integration with this repo remains separate.                                                           |
| [x]  | Put ModSecurity in the actual test request path                  | Critical    | High          | Done for local proof: `localhost:8088` reached ModSecurity/OWASP CRS, `/healthz` and `/api/health` returned 200, and SQLi probe `/api/health?id=17%27%20OR%2017%3D17--` returned 403. This is not a production deployment claim. |
| [~]  | Decide ModSecurity audit log format and retention                | Critical    | Low           | Partial: Compose writes JSON audit logs to `logs/modsecurity/modsec_audit.jsonl` and bridge consumes them; log rotation and retention policy remain TODO.                                                               |
| [x]  | Build ModSecurity JSON audit-log watcher/bridge                  | Critical    | High          | Done for local proof: bridge followed the live JSON audit log and posted `status=200 transaction_id=17821639659.909603 rule_ids=['942100', '949110']`; follow-mode transient `OSError` resilience remains TODO.        |
| [x]  | Connect ModSecurity detections to FastAPI ingest reliably        | Critical    | High          | Done for local proof: lookup for transaction `17821639659.909603` returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, source/request metadata, `crs_score=5`, and rules `942100`, `949110`.       |
| [~]  | Create CRS-only baseline test report                             | Critical    | Medium        | Partial: SQLi CRS block proof exists in `reports/modsecurity-live-proof/e2e-proof.md`, but no broader normal/attack CRS-only baseline report is checked in.                                                            |
| [~]  | Verify end-to-end attack flow                                    | Critical    | Medium-High   | Partial: request -> WAF -> audit log -> bridge -> FastAPI -> ML -> persisted lookup is proven; dashboard was observed manually, but a screenshot path is not captured in repo evidence.                                  |
| [ ]  | Add bounded async inference queue                                | Critical    | Medium        | Not started: no `asyncio.Queue(maxsize=N)` runtime ingestion queue found. ML inference is offloaded with `run_in_threadpool`, not queued.                                                                                 |
| [ ]  | Add queue health visibility                                      | Critical    | Low           | Not started: `/api/ml-health` exists, but no queue depth, worker state, overflow, or last queue error fields exist.                                                                                                       |
| [~]  | Add minimal metrics endpoint                                     | High        | Low           | Partial: `/api/stats` and `/api/ml-health` expose app/model stats, but no queue/email/bridge metrics exist.                                                                                                               |
| [ ]  | Add structured JSON logs with transaction/request IDs            | High        | Medium        | Not started: standard Python/Next logging exists; no repo-wide structured JSON logging contract found.                                                                                                                    |
| [ ]  | Add `CRITICAL >=90%` confidence tier                             | Critical    | Medium        | Not started: code contracts still expose `LOW`, `MEDIUM`, `HIGH` only in `ml_model/inference/predict_attack.py` and `frontend/features/alerts/contract.ts`.                                                              |
| [ ]  | Add real-time dashboard alerts                                   | High        | Medium        | Not started: no SSE/EventSource route or client stream found.                                                                                                                                                            |
| [ ]  | Add email notifications after detection                          | High        | Medium        | Not started: no transactional email integration found.                                                                                                                                                                   |
| [~]  | Add end-to-end demo/test script                                  | High        | Medium        | Partial: `reports/modsecurity-live-proof/e2e-proof.md` contains copy-paste proof commands and results; no standalone automated final demo script is checked in.                                                          |
| [~]  | Add API abuse/resource smoke tests                               | High        | Medium        | Partial: tests cover auth, duplicate transaction IDs, model-not-ready, and body limits in places; queue overflow, email, SSE, and full dashboard access abuse tests are not present.                                     |
| [~]  | Add analyst override/audit trail for model mistakes              | High        | Medium        | Partial: `POST /api/feedback` stores analyst label/email/timestamp, but no full old/new action, reason, or model-version override audit trail exists.                                                                     |
| [ ]  | Replace demo login with real user accounts                       | High        | High          | Not started: `frontend/auth.ts` still uses demo credentials and static SOC user identity.                                                                                                                                 |
| [ ]  | Implement RBAC for Admin, Analyst, and Viewer roles              | High        | High          | Not started: no persisted roles, session role claims, or route/action role checks found.                                                                                                                                  |
| [ ]  | Add 2FA/MFA                                                      | High        | High          | Not started: no TOTP/email OTP enrollment, challenge, recovery, or factor reset flow found.                                                                                                                              |
| [~]  | Add login hardening                                              | High        | Medium-High   | Partial: `AUTH_SECRET` is required and JWT max age is set; failed-login throttling, account lockout, reset/recovery, and login audit policy are missing.                                                                  |
| [~]  | Implement real enforcement state for block/throttle/challenge    | High        | High-Critical | Partial: `action_taken` is persisted as metadata; no request-path block/throttle/challenge state is enforced at runtime.                                                                                                  |
| [ ]  | Implement LOW light rate limiting                                | High        | High          | Not started: no LOW runtime rate-limit enforcement found.                                                                                                                                                                |
| [ ]  | Implement MEDIUM aggressive throttling                           | High        | High          | Not started: no MEDIUM runtime throttle enforcement found.                                                                                                                                                               |
| [ ]  | Implement CAPTCHA/Turnstile challenge flow                       | High        | High          | Not started: no CAPTCHA/Turnstile server-side verification or challenge state found.                                                                                                                                      |
| [ ]  | Implement HIGH/CRITICAL temporary IP blocking or firewall action | High        | High-Critical | Not started: no temporary IP blocklist/firewall handoff with expiry and rollback found.                                                                                                                                   |
| [ ]  | Implement automated retraining pipeline skeleton                 | High        | Critical      | Not started: `ml_model/retraining/README.md` says the package is design-level only and has no committed retraining entrypoint or scheduler.                                                                               |
| [ ]  | Add dataset validation before retraining                         | High        | High          | Not started for analyst-labeled retraining exports; no retraining dataset validation entrypoint found.                                                                                                                    |
| [ ]  | Add challenger evaluation gate before promotion                  | High        | High          | Not started for retrained candidates; promotion safety exists separately but no closed retraining challenger gate is present.                                                                                              |
| [~]  | Add model artifact checksum/manifest validation                  | Medium-High | Medium        | Partial: `ModelService` reads manifest/eval metadata, but checksum validation is not implemented.                                                                                                                         |
| [~]  | Add model promotion/rollback integration                         | Medium-High | Critical      | Partial: `ml_model/export/promote_final_training_run.py` implements archive/rollback safety, but real promotion currently fails closed on checkpoint shape mismatch per ops docs.                                        |
| [ ]  | Add production edge checklist                                    | Medium      | Low           | Not started as a dedicated checklist; related setup notes exist in `docs/SETUP.md`.                                                                                                                                       |
| [ ]  | Add backup/restore and migration rollback runbook                | Medium      | Medium        | Not started: no PostgreSQL/Supabase backup-restore or Alembic rollback runbook found.                                                                                                                                     |
| [ ]  | Add retention policy for alerts and audit logs                   | Medium      | Low-Medium    | Not started: no `archived_at`/`hidden_at` behavior or retention runbook found.                                                                                                                                            |
| [ ]  | Implement full DistilBERT retraining automation                  | Medium      | Critical      | Not started: final-training artifacts exist, but no production retraining automation flow is checked in.                                                                                                                  |
| [ ]  | Decide daily vs 20-day retraining window                         | Medium      | Low-Medium    | Not started: docs still reference 20-day design while newer tracker requirements mention daily-vs-20-day decision.                                                                                                        |
| [~]  | Align operator docs after implementation                         | Medium      | Low           | Partial: docs exist and are being corrected; some historical/planning docs still contain target-state language.                                                                                                           |
| [ ]  | Add Wazuh export-only integration                                | Low-Medium  | Medium        | Not started: no Wazuh JSON/JSONL export implementation found.                                                                                                                                                            |
| [ ]  | Supabase/RLS operational hardening export                        | Low-Medium  | Medium        | Not started: ops docs say some Supabase policy and hardening steps remain outside repo automation.                                                                                                                        |
| [~]  | Dashboard polish for mitigation/security pages                   | Low         | Low-Medium    | Partial: dashboard/alerts/ML-health UI exists; mitigation/security-specific pages remain planned.                                                                                                                         |
| [x]  | Defer Wazuh full SIEM deployment                                 | Defer       | Critical      | Done as a scope decision: tracker keeps Wazuh as export-only and marks full SIEM as deferred.                                                                                                                             |
| [x]  | Defer Kubernetes/Helm/Terraform                                  | Defer       | Critical      | Done as a scope decision: tracker keeps Docker Compose/runbooks/checklists as the PD2 path.                                                                                                                               |
| [x]  | Defer Kafka/Celery/Elasticsearch                                 | Defer       | Critical      | Done as a scope decision: tracker prefers `asyncio.Queue`, PostgreSQL, and structured logs first.                                                                                                                         |

## Current Recommended Focus

Based on priority and implementation hardness, focus on the highest-value work that proves the system before starting the hardest platform pieces.

| Focus Order | Task                                                       | Why Now                                                                                                                                |
| ----------: | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
|           1 | Harden bridge transient read-error behavior                | A live proof passed, but follow mode once logged transient `OSError: [Errno 5] Input/output error` before restart recovery.            |
|           2 | Decide ModSecurity audit log retention and rotation        | JSON audit format and live path are proven; rotation and retention remain unresolved.                                                   |
|           3 | Create CRS-only baseline test report                       | Shows what CRS detects before ML triage and gives evidence for false positives/detection gaps.                                         |
|           4 | Capture final dashboard screenshot evidence                | Dashboard was observed manually, but a screenshot path is not recorded in checked-in proof.                                             |
|           5 | Add bounded async inference queue and queue health         | Protects FastAPI from log bursts and mass attack tests while giving operators visibility.                                              |
|           6 | Add metrics and structured JSON logs                       | Gives traceability and measurable evidence for defense/client testing.                                                                 |
|           7 | Add `CRITICAL >=90%` confidence tier                       | Client standard requires it and it touches backend/frontend contracts.                                                                 |
|           8 | Add real-time dashboard alerts and email notification path | Client requires timely alerts and email notification after detection.                                                                  |
|           9 | Add API abuse/resource smoke tests                         | Gives production-readiness evidence without enterprise test platforms.                                                                 |
|          10 | Implement secure login, RBAC, 2FA, and login hardening     | Client requires secure login, RBAC, strong account security, and 2FA.                                                                  |
|          11 | Implement lightweight enforcement and challenge flow       | Required for confidence-based response, but should follow stable WAF-to-dashboard proof.                                               |
|          12 | Implement analyst override and retraining skeleton         | Supports HITL feedback and retraining objective without unsafe auto-promotion.                                                         |

Do not start with Kubernetes, Helm, Terraform, Kafka, Celery, Elasticsearch, full Wazuh/SIEM, or blind model auto-promotion. Use lightweight implementation first and add heavier infrastructure only if a real shared-state or deployment need appears.

## Suggested Build Order

1. Harden bridge follow-mode transient `OSError` handling.
2. Decide ModSecurity audit log rotation and retention.
3. Create CRS-only baseline report for normal and attack traffic.
4. Capture final dashboard screenshot evidence for the proven WAF transaction.
5. Add bounded async inference queue using `asyncio.Queue(maxsize=N)`.
6. Queue health visibility in `/api/ml-health` or a small ops/health endpoint.
7. Minimal metrics endpoint.
8. Structured JSON logs with request/transaction IDs.
9. `CRITICAL >=90%` confidence tier.
10. Confidence-to-action policy mapping for LOW, MEDIUM, HIGH, and CRITICAL.
11. Real-time dashboard alerts using SSE/EventSource with polling fallback.
12. Email notifications using transactional email API with deduplication, cooldown, retry/failure logging, and summary behavior.
13. Standalone final demo/test script if the proof checklist is not enough for defense rehearsal.
14. API abuse/resource smoke tests.
15. Real user accounts or managed auth.
16. RBAC for Admin, Analyst, and Viewer.
17. 2FA/MFA and login hardening.
18. Lightweight DB-backed or in-memory enforcement state.
19. LOW light rate limiting.
20. MEDIUM aggressive throttling.
21. CAPTCHA/Turnstile challenge flow with server-side verification if Turnstile is used.
22. HIGH/CRITICAL temporary IP blocking or firewall action.
23. Analyst override/audit trail for model mistakes.
24. Automated retraining pipeline skeleton.
25. Dataset validation before retraining.
26. Challenger evaluation gate before promotion.
27. Real DistilBERT retraining mode if time allows.
28. Model promotion/rollback integration with manual approval.
29. Model artifact checksum/manifest validation.
30. Production edge checklist.
31. Backup/restore and migration rollback runbook.
32. Alert/archive retention policy with no physical DELETE for audit/traffic logs.
33. Wazuh export-only JSON/JSONL integration if time allows.
34. Align operator docs after implementation.
35. Dashboard polish for mitigation/security pages.

## Notes For Client Security Requirements

* Treat `CRITICAL >=90%` as a client confidence standard and update backend/frontend contracts together.
* Keep confidence tier separate from attack severity.
* Secure login, RBAC, and 2FA should be implemented as one account-security track:

  1. replace demo password login with real user accounts or managed auth,
  2. add Admin, Analyst, and Viewer roles,
  3. enforce RBAC in route handlers, API mutations, dashboard pages, and UI actions,
  4. add lightweight 2FA/MFA using TOTP or email OTP,
  5. add failed-login throttling, generic auth errors, session expiry, secure cookies, safe reset/recovery behavior, and login/admin audit records.
* Keep Auth.js as the current auth foundation unless a managed auth provider is selected.
* Email notification should use a transactional email provider/API instead of hand-built SMTP infrastructure.
* Email notifications must include deduplication, cooldown, retry/failure logging, and summary behavior to avoid spam during mass attack tests.

## Notes For ModSecurity Demo

The smallest useful demo target is enough:

* Search page.
* Login page.
* Comment form.
* Blog/forum-like route.

Minimum useful request path:

```text
Client/test script -> Nginx/ModSecurity + OWASP CRS -> demo target app
                         |
                         v
                 audit log watcher/bridge -> FastAPI ingest -> ML triage -> dashboard
```

Verified demonstration flow:

```text
WAF health request -> HTTP 200
API health through WAF -> HTTP 200
SQL injection-looking request -> CRS blocks with HTTP 403
Bridge reads audit log -> FastAPI ingests event
ML triage runs -> HIGH confidence SQL Injection
Policy action is recorded as BLOCKED
Docker-internal lookup returns source/request metadata and crs_score=5
```

ModSecurity tracker work must include:

* selected audit-log format,
* captured fields/log parts,
* transaction ID strategy,
* sensitive-data handling,
* log rotation,
* retention,
* CRS-only baseline report,
* repeatable end-to-end demo/test script.

## Notes For Queue And Inference Safety

* Use native `asyncio.Queue(maxsize=N)` before Redis/Celery.
* Queue goal: protect FastAPI and ML inference from log bursts and client mass attack tests.
* Define overflow behavior explicitly:

  * reject new event,
  * skip ML but store basic alert,
  * drop oldest pending event,
  * or mark overflow/degraded event.
* Do not silently drop WAF events.
* Expose queue depth, worker status, processed count, failed count, rejected/skipped count, and last worker error.
* Put queue status in `/api/ml-health` or a small ops/health endpoint.
* Keep worker count small and predictable for PD2.
* Redis is not required for inference queuing unless multiple processes/instances must share the same queue.

## Notes For Observability

* Add structured JSON logs across:

  * ModSecurity bridge,
  * FastAPI ingest,
  * ML prediction,
  * policy decision,
  * dashboard/BFF calls,
  * email send,
  * analyst override,
  * retraining jobs.
* Include these fields where applicable:

  * `transaction_id`,
  * `request_id`,
  * `alert_id`,
  * `model_version`,
  * `prediction`,
  * `confidence_tier`,
  * `action`,
  * `user_id`.
* Add a minimal metrics endpoint tracking:

  * total ingested,
  * total classified,
  * total failed,
  * queue depth,
  * inference latency,
  * confidence tier counts,
  * action counts,
  * email sent count,
  * model loaded status.
* Add API abuse/resource smoke tests for:

  * missing auth,
  * invalid token,
  * malformed JSON,
  * oversized payload,
  * duplicate transaction ID,
  * repeated requests,
  * queue overflow,
  * slow/failed inference,
  * invalid triage update,
  * dashboard API access.
* Add production edge checklist as a runbook only. Cover CORS, disabled docs outside dev, env validation, internal API token, auth bypass prevention, reverse proxy headers, TLS boundary, safe error responses, log retention, and demo data reset.

## Notes For Enforcement

* `ALLOWED`, `THROTTLED`, and `BLOCKED` are currently action records, not complete runtime enforcement.
* Add `CRITICAL >=90%` as a confidence tier, not as a replacement for severity.
* Suggested policy mapping:

  * LOW: monitor + light rate limit or challenge marker.
  * MEDIUM: aggressive throttle + challenge required.
  * HIGH: temporary block or strong throttle + real-time alert.
  * CRITICAL: temporary block/firewall action + real-time alert + email.
* Start with DB-backed or in-memory demo enforcement if it is enough for PD2.
* Redis-backed enforcement state is should-have-if-time-allows, not the first implementation step.
* Redis is only needed if Nginx/proxy/FastAPI/workers need shared throttle/block/challenge state.
* CAPTCHA/Turnstile challenge flow should be lightweight.
* If Turnstile is used, server-side token verification is mandatory.
* Challenge state must have expiry and audit logging.
* Firewall/IP blocking must be temporary, reversible, logged, and safe from permanent bad firewall changes.

## Notes For Retraining

* Retraining is required, but blind auto-promotion is not.
* Implement retraining pipeline skeleton first:

  * manual/scheduled trigger,
  * analyst-labeled data export,
  * dataset validation,
  * dry-run/smoke mode,
  * job status,
  * evaluation output,
  * candidate artifact path.
* Do not wait 20 real days for testing. Simulate the selected retraining window with timestamped labeled samples.
* Decide daily vs 20-day retraining window and make code/docs consistent.
* Keep two modes:

  * Dry-run/smoke mode: validates scheduler, label export, dataset checks, command orchestration, and job status without long training.
  * Real training mode: runs actual DistilBERT fine-tuning and evaluation.
* Full DistilBERT retraining automation is should-have-if-time-allows.
* Real training mode should not run in normal CI.
* A retrained model should only be promoted if metrics pass defined thresholds.
* Manual approval is required before promotion.
* Keep previous model available for rollback.
* Based on saved final artifacts, DistilBERT final confirmatory training took about 30.5 minutes per seed and about 1.5 hours for 3 seeds.

## Notes For Database, Retention, And Recovery

* Add backup/restore and migration rollback as a lightweight runbook.
* Use PostgreSQL/Supabase/Alembic expectations.
* Do not build full backup automation unless an adviser/client specifically requires it.
* Do not physically delete audit/traffic logs during PD2.
* Use archive/hide/retention wording instead.
* Suggested alert retention behavior:

  * `archived_at`
  * `archived_by`
  * `archive_reason`
  * `hidden_from_default_view`
* Keep audit logs available for defense evidence and debugging.

## Notes For Wazuh Export

* Wazuh integration should be export-only for PD2.
* Export normalized alerts as JSON/JSONL suitable for Wazuh collection.
* Do not add full Wazuh/SIEM deployment.
* Export should include:

  * timestamp,
  * transaction ID,
  * source IP,
  * method,
  * URI,
  * CRS score,
  * CRS rule IDs,
  * model prediction,
  * confidence tier,
  * action,
  * analyst status if available.
* Treat this as compatibility evidence, not a required SIEM deployment.

## Notes For Deferred / Overengineered Items

* Do not add full Wazuh/SIEM deployment for PD2.

  * Use Wazuh export-only JSON/JSONL compatibility if time allows.
* Do not add Kubernetes, Helm, or Terraform for PD2.

  * Use Docker Compose, env validation, runbooks, and checklists.
* Do not add Kafka, Celery, or Elasticsearch for PD2.

  * Use `asyncio.Queue`, PostgreSQL, and structured JSON logs first.
* Do not build custom SMTP infrastructure.

  * Use a transactional email API.
* Do not use WebSockets unless two-way communication is required.

  * Use SSE/EventSource first and keep polling fallback.
* Do not physically delete audit/traffic logs during PD2.

  * Use archive/hide/retention policy wording.
* Do not auto-promote retrained models blindly.

  * Use candidate artifact, evaluation gate, and manual approval.
