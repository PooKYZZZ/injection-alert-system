# PD2 Priority Tracker

**Purpose:** Track what still needs to be implemented for PD2 without claiming that planned features already exist.
**Last updated:** 2026-07-03

## Legend

**Urgency:** How soon this matters for the PD2 demo/defense.  
**Difficulty:** How hard it is to implement correctly in the current codebase.

**Status:**

- `[x]` Done
- `[~]` Partial
- `[ ]` Not started
- `[!]` Blocked

## Evidence Basis

This tracker is based on the following.

### Current Repo Inspection

- `web_app/application/triage_use_case.py` currently maps confidence to `ALLOWED`, `THROTTLED`, and `BLOCKED`.
- `frontend/auth.ts` uses Supabase `auth_accounts` with Argon2id password hashes, role/version claims, local login throttling, and safe audit events; protected BFF routes recheck current DB account state.
- `ml_model/retraining/README.md` says the retraining pipeline is still design-level only.
- `reports/modsecurity-live-proof/e2e-proof.md` proves the local ModSecurity/OWASP CRS -> bridge -> FastAPI WAF ingest path through `localhost:8088`.
- Runtime evidence from 2026-06-27 proves the realistic demo-target path through `localhost:8089`: `demo-target-bridge` posted transaction `178249138618.813428`, backend lookup returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, and `crs_score=15`.
- `reports/modsecurity-live-proof/dashboard-evidence.md` and `reports/modsecurity-live-proof/screenshots/` contain dashboard overview, `/records/search` alerts table, WAF alert detail, and ML health overview screenshot evidence; the alert detail drawer screenshots in the latest set show the default `8088` path, not the `8089` `/records/search` transaction.
- `docs/architecture.md` says Redis-backed enforcement is planned, not implemented.
- `web_app/application/inference_queue.py`, `tests/unit/test_inference_queue.py`, and `/api/ml-health` queue schema wiring prove the bounded in-process inference queue and queue health API are implemented.
- Latest verification passed: backend `496 passed`, frontend full Vitest `316 passed`, frontend typecheck, lint, and production build.
- CRITICAL remains a confidence tier only. Persisted `confidence_level` and action values `ALLOWED`/`THROTTLED`/`BLOCKED` remain unchanged; `confidence_tier` is preferred and `severity` is a legacy query alias. Persisted-alert UI grouping/styling uses `confidence_level`, enforcement-policy counts exclude Normal predictions, and tier badges always display the canonical tier.

### Client Requirements

- The system should be secure and controlled.
- The system should implement user access management using RBAC with secure login.
- The system should provide timely alerts for detected threats.
- The system shall send email notifications after detection.
- The system should ensure strong account security.
- The system shall implement two-factor authentication (2FA).
- The client standard includes a `CRITICAL >=90%` confidence tier.
- Canonical requirement notes live in `docs/client-requirements.md`.

### External Implementation References

- OWASP CRS: <https://owasp.org/www-project-modsecurity-core-rule-set/>
- ModSecurity reference manual: <https://github.com/owasp-modsecurity/ModSecurity/wiki/Reference-Manual-%28v2.x%29>
- Python `asyncio.Queue`: <https://docs.python.org/3/library/asyncio-queue.html>
- FastAPI background tasks: <https://fastapi.tiangolo.com/tutorial/background-tasks/>
- MDN Server-Sent Events: <https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events>
- Auth.js RBAC: <https://authjs.dev/guides/role-based-access-control>
- OWASP Authentication Cheat Sheet: <https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html>
- OWASP MFA Cheat Sheet: <https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html>
- Redis rate limiting: <https://redis.io/docs/latest/develop/use-cases/rate-limiter/>
- Cloudflare Turnstile server validation: <https://developers.cloudflare.com/turnstile/get-started/server-side-validation/>
- PostgreSQL backup/restore: <https://www.postgresql.org/docs/current/app-pgdump.html>
- Alembic migrations: <https://alembic.sqlalchemy.org/>
- Wazuh documentation: <https://documentation.wazuh.com/>
- Google MLOps continuous training: <https://docs.cloud.google.com/architecture/mlops-continuous-delivery-and-automation-pipelines-in-machine-learning>
- AWS retraining guidance: <https://docs.aws.amazon.com/machine-learning/latest/dg/retraining-models-on-new-data.html>

## Priority List

| Status | Task | Urgency | Difficulty | Why This Is Ranked Here |
|---|---|---|---|---|
| `[x]` | Build a small demo target website | Critical | Medium | External target exists at `G:\AI\land-records-portal` with WAF route inventory and live Playwright PASS evidence. The source remains separate; this repo's demo-target Compose profile builds it as internal service `demo-portal:3010`. |
| `[x]` | Put ModSecurity in the actual test request path | Critical | High | Done for local proof: `localhost:8088` reached ModSecurity/OWASP CRS, `/healthz` and `/api/health` returned 200, and SQLi probe `/api/health?id=17%27%20OR%2017%3D17--` returned 403. This is not a production deployment claim. |
| `[~]` | Decide ModSecurity audit log format and retention | Critical | Low | Partial: Policy documented in `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`; JSONL path is `logs/modsecurity/modsec_audit.jsonl`; automatic rotation is not implemented and production retention is not implemented. |
| `[x]` | Build ModSecurity JSON audit-log watcher/bridge | Critical | High | Done for local proof: bridge followed the live JSON audit log and posted `status=200`, `transaction_id=17821639659.909603`, `rule_ids=['942100', '949110']`; follow-mode transient `readline()` `OSError` resilience is implemented and unit-tested in `tests/scripts/test_waf_audit_bridge.py`. |
| `[x]` | Connect ModSecurity detections to FastAPI ingest reliably | Critical | High | Done for local proof: lookup for transaction `17821639659.909603` returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, source/request metadata, `crs_score=5`, and rules `942100`, `949110`. |
| `[x]` | Create CRS-only baseline test report | Critical | Medium | Done: `reports/modsecurity-live-proof/crs-baseline.md` records normal traffic, SQLi, XSS-like, command/file-access-like, and false-positive check results through `localhost:8088` with observed CRS rule IDs and transaction IDs. |
| `[x]` | Create demo-target WAF proof using portal-pre-waf | Critical | Medium | Done: `reports/modsecurity-live-proof/demo-target-crs-proof.md` records observed portal route checks through `localhost:8089`, including normal traffic, SQLi/XSS checks, CRS transaction IDs, rule IDs, and matched messages where available. |
| `[x]` | Connect demo-target WAF audit log to CyberTrace via demo-target-bridge | Critical | Medium | Done: `demo-target-bridge` watches `logs/modsecurity/demo-target/modsec_audit.jsonl`; verified transaction `178249138618.813428` posted with `status=200` and backend lookup returned `/records/search`, `SQL Injection`, `BLOCKED`, `crs_score=15`. |
| `[x]` | Verify end-to-end attack flow | Critical | Medium-High | Done for local proof: request -> WAF -> audit log -> bridge -> FastAPI -> ML -> persisted lookup is proven for both `8088` and realistic `8089`; fresh dashboard screenshot evidence now includes `/records/search`, `SQL Injection`, `Blocked`, and `crs_score=15` in `reports/modsecurity-live-proof/screenshots/demo-target-8089-alerts-table.png`. |
| `[x]` | Add bounded async inference queue | Critical | Medium | Done: `web_app/application/inference_queue.py` implements a bounded `asyncio.Queue(maxsize=N)` gate for synchronous WAF ingest, with overflow handling covered by `tests/unit/test_inference_queue.py`. |
| `[x]` | Add queue health visibility | Critical | Low | Done: `/api/ml-health` includes optional queue health fields through the backend schema/BFF passthrough; UI-specific queue panel evidence is not claimed. |
| `[~]` | Add minimal metrics endpoint | High | Low | Partial by design: `/api/stats` and `/api/ml-health` expose app/model stats and queue health, and bridge JSON summary logs expose total/success/failed counts; no separate bridge/email metrics endpoint exists. |
| `[x]` | Add structured JSON logs with transaction/request IDs | High | Medium | Done for the approved scope: bridge operations and FastAPI request/WAF/prediction boundaries emit JSON; handled and generic unhandled `500` responses carry `X-Request-ID`, valid `traceparent` IDs are preserved, and `transaction_id` joins bridge and backend WAF events. Unrelated legacy logs and the Next.js BFF are not claimed as converted. |
| `[x]` | Add `CRITICAL >=90%` confidence tier | Critical | Medium | Done: backend/frontend contracts expose LOW, MEDIUM, HIGH, and CRITICAL; persisted UI grouping/styling uses `confidence_level`; enforcement-policy displays apply to non-Normal predictions and preserve the Normal exception; tier badges always display the canonical tier; the legacy `severity` query alias remains compatibility-only. |
| `[ ]` | Add real-time dashboard alerts | High | Medium | Not started: no SSE/EventSource route or client stream found. |
| `[ ]` | Add email notifications after detection | High | Medium | Not started: no transactional email integration found. |
| `[x]` | Add end-to-end demo/test script | High | Medium | Done for the maintained proof boundary: `scripts/run_final_demo_smoke.py` provides explicit backend, `8088`, and `8089` modes, safe PASS/FAIL/SKIP and JSON output, timeouts, and nonzero required-check failures; `tests/scripts/test_run_final_demo_smoke.py` is Docker-free. Docker-internal transaction lookup remains an explicit manual runbook step. |
| `[x]` | Add API abuse/resource smoke tests | High | Medium | Done for the current backend surface: `tests/integration/test_api_abuse_smoke.py` covers malformed JSON, missing/invalid auth correlation, token non-leakage, and invalid triage input; existing body-limit, duplicate transaction, model-unavailable, queue-overflow, lookup, and BFF-auth tests cover the remaining implemented boundaries. Future email/SSE/RBAC abuse cases remain not applicable until those features exist. |
| `[~]` | Add analyst override/audit trail for model mistakes | High | Medium | Partial: `POST /api/feedback` stores analyst label/email/timestamp, but no full old/new action, reason, or model-version override audit trail exists. |
| `[x]` | Replace demo login with real user accounts | High | High | Done in repo: Supabase `auth_accounts` provides ids/emails/usernames, roles, required `authz_version`, and Argon2id hashes; no demo-password or env-registry fallback remains. |
| `[x]` | Implement RBAC for Admin, Analyst, and Viewer roles | High | High | Done: role/session claims and fresh per-request DB account checks protect all six BFF routes; Viewer reads, Analyst triages, and Admin may update actions. |
| `[ ]` | Add 2FA/MFA | High | High | Not started: no TOTP/email OTP enrollment, challenge, recovery, or factor reset flow found. |
| `[~]` | Add login hardening | High | Medium-High | Partial: generic errors, Argon2id dummy verification, per-identifier/global local throttles, two-operation password-hash cap, eight-hour sessions, and safe JSON audit events are implemented. MFA, reset/recovery, distributed throttling, and persistent audit storage remain missing. |
| `[x]` | Add auth/security schema foundation | High | Medium | Done in repo: additive Alembic migration, nine public-schema tables with RLS/revocations/no policies, tested app-runtime and script-only Supabase boundaries, Argon2id, provisioning scripts, and DB-backed login/freshness. Live migration application and MFA remain unimplemented. |
| `[~]` | Implement real enforcement state for block/throttle/challenge | High | High-Critical | Partial: `action_taken` is persisted as metadata; no request-path block/throttle/challenge state is enforced at runtime. |
| `[ ]` | Implement LOW light rate limiting | High | High | Not started: no LOW runtime rate-limit enforcement found. |
| `[ ]` | Implement MEDIUM aggressive throttling | High | High | Not started: no MEDIUM runtime throttle enforcement found. |
| `[ ]` | Implement CAPTCHA/Turnstile challenge flow | High | High | Not started: no CAPTCHA/Turnstile server-side verification or challenge state found. |
| `[ ]` | Implement HIGH/CRITICAL temporary IP blocking or firewall action | High | High-Critical | Not started: no temporary IP blocklist/firewall handoff with expiry and rollback found. |
| `[ ]` | Implement automated retraining pipeline skeleton | High | Critical | Not started: `ml_model/retraining/README.md` says the package is design-level only and has no committed retraining entrypoint or scheduler. |
| `[ ]` | Add dataset validation before retraining | High | High | Not started for analyst-labeled retraining exports; no retraining dataset validation entrypoint found. |
| `[ ]` | Add challenger evaluation gate before promotion | High | High | Not started for retrained candidates; promotion safety exists separately but no closed retraining challenger gate is present. |
| `[~]` | Add model artifact checksum/manifest validation | Medium-High | Medium | Partial: `ModelService` reads manifest/eval metadata, but checksum validation is not implemented. |
| `[~]` | Add model promotion/rollback integration | Medium-High | Critical | Partial: `ml_model/export/promote_final_training_run.py` implements archive/rollback safety, but real promotion currently fails closed on checkpoint shape mismatch per ops docs. |
| `[x]` | Add production edge checklist | Medium | Low | Done as operator documentation: `docs/project-ops/PRODUCTION_EDGE_CHECKLIST.md` defines production-edge readiness checks and explicit non-production truth. This does not claim production deployment is complete. |
| `[x]` | Add backup/restore and migration rollback runbook | Medium | Medium | Done as operator documentation: `BACKUP_RESTORE_RUNBOOK.md` and `MIGRATION_ROLLBACK_RUNBOOK.md` document safe backup, restore, and rollback procedures. No automated backup/restore job or migration change was implemented. |
| `[x]` | Add retention policy for alerts and audit logs | Medium | Low-Medium | Done as policy documentation: `RETENTION_POLICY.md` defines archive/hide-first retention rules and explicitly says no physical DELETE behavior or retention job was added. |
| `[ ]` | Implement full DistilBERT retraining automation | Medium | Critical | Not started: final-training artifacts exist, but no production retraining automation flow is checked in. |
| `[ ]` | Decide daily vs 20-day retraining window | Medium | Low-Medium | Not started: docs still reference 20-day design while newer tracker requirements mention daily-vs-20-day decision. |
| `[x]` | Align maintained docs for the CRITICAL rollout | Medium | Low | Done: maintained implementation, setup, contributor, operator, and tracker docs describe CRITICAL as implemented and retain planned/deferred wording for unfinished features. |
| `[ ]` | Add Wazuh export-only integration | Low-Medium | Medium | Not started: no Wazuh JSON/JSONL export implementation found. |
| `[x]` | Supabase/RLS operational hardening export | Low-Medium | Medium | Done as operator documentation: `SUPABASE_RLS_HARDENING.md` documents RLS/security-advisor/project-hardening checks. No Supabase dashboard setting or RLS policy was changed by this branch. |
| `[~]` | Dashboard polish for mitigation/security pages | Low | Low-Medium | Partial: dashboard/alerts/ML-health UI exists; mitigation/security-specific pages remain planned. |
| `[x]` | Defer Wazuh full SIEM deployment | Defer | Critical | Done as a scope decision: tracker keeps Wazuh as export-only and marks full SIEM as deferred. |
| `[x]` | Defer Kubernetes/Helm/Terraform | Defer | Critical | Done as a scope decision: tracker keeps Docker Compose/runbooks/checklists as the PD2 path. |
| `[x]` | Defer Kafka/Celery/Elasticsearch | Defer | Critical | Done as a scope decision: tracker prefers `asyncio.Queue`, PostgreSQL, and structured logs first. |

## Current Recommended Focus

Based on priority and implementation hardness, focus on the highest-value work that proves the system before starting the hardest platform pieces.

### Focus Order

| Order | Task | Why Now |
|---:|---|---|
| 1 | Maintain structured-log and API abuse/resource smoke coverage | Bridge and FastAPI boundary JSON logs plus current backend abuse/failure paths are automated; extend them only when implemented API surfaces change. |
| 2 | Track ModSecurity audit log rotation as future hardening | Policy is documented; automatic rotation and production retention remain unimplemented and should not be marked done without tested rotation. |
| 3 | Create CRS-only baseline test report | Done in `reports/modsecurity-live-proof/crs-baseline.md`; keep it as the CRS baseline evidence source. |
| 4 | Create demo-target WAF proof using portal-pre-waf | Done in `reports/modsecurity-live-proof/demo-target-crs-proof.md`; normal traffic and controlled CRS checks were recorded through `localhost:8089`. |
| 5 | Capture final dashboard screenshot evidence | Done for the current local proof set: screenshots under `reports/modsecurity-live-proof/screenshots/` show the `8089` dashboard overview, `/records/search` alerts table with `crs_score=15`, default `8088` WAF detail drawer evidence, and ML health overview. |
| 6 | Preserve minimal metrics and structured-log contracts | Existing stats, queue health, bridge summary counts, and correlated JSON events are the current PD2 boundary. |
| 7 | Maintain `CRITICAL >=90%` confidence tier coverage | Client standard requires it and the backend/frontend contracts now implement it. |
| 8 | Add real-time dashboard alerts and email notification path | Client requires timely alerts and email notification after detection. |
| 9 | Maintain API abuse/resource smoke tests | Current backend proof is checked in; add cases only for newly implemented surfaces. |
| 10 | Implement secure login, RBAC, 2FA, and login hardening | Client requires secure login, RBAC, strong account security, and 2FA. |
| 11 | Implement lightweight enforcement and challenge flow | Required for confidence-based response, but should follow stable WAF-to-dashboard proof. |
| 12 | Implement analyst override and retraining skeleton | Supports HITL feedback and retraining objective without unsafe auto-promotion. |

Do not start with Kubernetes, Helm, Terraform, Kafka, Celery, Elasticsearch, full Wazuh/SIEM, or blind model auto-promotion. Use lightweight implementation first and add heavier infrastructure only if a real shared-state or deployment need appears.

## Suggested Build Order

1. Harden bridge follow-mode transient OSError handling.
2. Keep ModSecurity audit log rotation as future hardening unless explicitly approved and tested.
3. Keep CRS-only baseline report as the current baseline evidence source.
4. Keep `reports/modsecurity-live-proof/demo-target-crs-proof.md` as the observed demo-target WAF proof source.
5. Add a queue-specific ML health screenshot only if the final evidence checklist must show queue fields in the UI; the current replacement screenshot covers the `/ml-health` overview but does not visibly show queue-health fields.
6. Keep metrics minimal: existing stats, ML health, queue health, and bridge summary logs; a new endpoint remains unimplemented.
7. Maintain implemented structured JSON logs with request/trace/transaction IDs at the bridge and FastAPI request/WAF/prediction boundaries.
8. `CRITICAL >=90%` confidence tier is implemented and maintained across backend/frontend contracts.
9. Confidence-to-action policy mapping for LOW, MEDIUM, HIGH, and CRITICAL.
10. Real-time dashboard alerts using SSE/EventSource with polling fallback.
11. Email notifications using transactional email API with deduplication, cooldown, retry/failure logging, and summary behavior.
12. Maintain the standalone final demo/test script and local-only Docker modes.
13. Maintain API abuse/resource smoke tests as implemented surfaces change.
14. Real user accounts or managed auth.
15. RBAC for Admin, Analyst, and Viewer.
16. 2FA/MFA and login hardening.
17. Lightweight DB-backed or in-memory enforcement state.
18. LOW light rate limiting.
19. MEDIUM aggressive throttling.
20. CAPTCHA/Turnstile challenge flow with server-side verification if Turnstile is used.
21. HIGH/CRITICAL temporary IP blocking or firewall action.
22. Analyst override/audit trail for model mistakes.
23. Automated retraining pipeline skeleton.
24. Dataset validation before retraining.
25. Challenger evaluation gate before promotion.
26. Real DistilBERT retraining mode if time allows.
27. Model promotion/rollback integration with manual approval.
28. Model artifact checksum/manifest validation.
29. Production edge checklist.
30. Backup/restore and migration rollback runbook.
31. Alert/archive retention policy with no physical DELETE for audit/traffic logs.
32. Wazuh export-only JSON/JSONL integration if time allows.
33. Maintain operator-doc truth after each implementation.
34. Dashboard polish for mitigation/security pages.

## Notes For Client Security Requirements

Treat `CRITICAL >=90%` as a client confidence standard and update backend/frontend contracts together.

Keep confidence tier separate from attack severity.

Current repo naming note: LOW, MEDIUM, HIGH, and CRITICAL are the current confidence tiers. The app now prefers `confidence_tier` naming while retaining legacy `severity` query compatibility during migration. `CRITICAL >=90%` is implemented as the confidence threshold, and historical rows are not retroactively reclassified.

The DB-backed named-account and RBAC foundation is implemented. Remaining account-security work is:

1. Add the notification outbox/email-provider foundation in the maintained plan order.
2. Add lightweight 2FA/MFA using TOTP with the documented email fallback risk.
3. Add secure password reset/recovery.
4. Replace local-only throttling and logs with distributed controls and persistent audit storage if production deployment is approved.

Keep Auth.js as the current auth foundation unless a managed auth provider is selected.

Email notification should use a transactional email provider/API instead of hand-built SMTP infrastructure.

Email notifications must include deduplication, cooldown, retry/failure logging, and summary behavior to avoid spam during mass attack tests.

## Notes For ModSecurity Demo

The smallest useful demo target is enough:

- Search page.
- Login page.
- Comment form.
- Blog/forum-like route.

Minimum useful request path:

```text
Client/test script -> Nginx/ModSecurity + OWASP CRS -> demo target app
                         |
                         v
                 audit log watcher/bridge -> FastAPI ingest -> ML triage -> dashboard
```

Verified demonstration flow:

1. WAF health request -> HTTP 200.
2. API health through WAF -> HTTP 200.
3. SQL injection-looking request -> CRS blocks with HTTP 403.
4. Bridge reads audit log -> FastAPI ingests event.
5. ML triage runs -> HIGH confidence SQL Injection.
6. Policy action is recorded as BLOCKED.
7. Docker-internal lookup returns source/request metadata and `crs_score=5`.

ModSecurity tracker work must include:

- Selected audit-log format.
- Captured fields/log parts.
- Transaction ID strategy.
- Sensitive-data handling.
- Log rotation.
- Retention.
- CRS-only baseline report.
- Repeatable end-to-end demo/test script (`scripts/run_final_demo_smoke.py`);
  Docker-internal lookup remains a manual proof step.

## Notes For Queue And Inference Safety

Native `asyncio.Queue(maxsize=N)` is implemented for synchronous WAF ingest before Redis/Celery.

Queue goal: protect FastAPI and ML inference from log bursts and client mass attack tests.

Current overflow behavior:

- reject new WAF ingest work with HTTP 503
- return `Retry-After: 5`
- preserve the synchronous WAF ingest response contract for accepted work

Future enforcement design should still define behavior for non-inference queues explicitly:

- Reject new event.
- Skip ML but store basic alert.
- Drop oldest pending event.
- Mark overflow/degraded event.

Do not silently drop WAF events.

Queue health is exposed in `/api/ml-health`, including depth, capacity, worker status, processed count, failed count, overflow count, and sanitized last worker error.

Keep worker count small and predictable for PD2.

Redis is not required for inference queuing unless multiple processes/instances must share the same queue.

## Notes For Observability

Structured JSON logging is implemented for:

- ModSecurity bridge.
- FastAPI ingest.
- ML prediction.

The FastAPI request middleware also logs request completion/failure. WAF ingest and prediction completion events include the policy outcome. The following remain future scope:

- Dashboard/BFF calls.
- Email send.
- Analyst override.
- Retraining jobs.

Include these fields where applicable:

- `transaction_id`
- `request_id`
- `alert_id`
- `model_version`
- `prediction`
- `confidence_tier`
- `action_taken`
- `user_id`

Current minimal metrics are `/api/stats`, `/api/ml-health` queue health, and bridge summary log counts. A separate metrics endpoint with the following broader counters remains unimplemented:

- Total ingested.
- Total classified.
- Total failed.
- Queue depth.
- Inference latency.
- Confidence tier counts.
- Action counts.
- Email sent count.
- Model loaded status.

Current API abuse/resource smoke proof covers:

- Missing auth and invalid token, including `X-Request-ID` and token non-leakage.
- Malformed JSON and invalid triage updates.
- Oversized payloads through the body-limit middleware.
- Duplicate/repeated transaction IDs and safe unknown transaction lookup.
- Queue overflow with `503`, `Retry-After`, structured correlation fields, and
  secret non-leakage.
- Failed/model-unavailable inference.
- Dashboard BFF access without a session through existing frontend route tests.

Email, SSE, and 2FA abuse cases remain not applicable until those features
exist. RBAC denial/stale-session and login-throttle/audit cases are covered by
frontend tests.

Document production edge checklist as operator guidance only. Cover CORS, disabled docs outside dev, env validation, internal API token, auth bypass prevention, reverse proxy headers, TLS boundary, safe error responses, log retention, and demo data reset.

## Notes For Enforcement

`ALLOWED`, `THROTTLED`, and `BLOCKED` are currently action records, not complete runtime enforcement.

Maintain `CRITICAL >=90%` as an implemented confidence tier, not as a business/security severity value.

Suggested policy mapping:

| Confidence Tier | Suggested Response |
|---|---|
| LOW | Monitor + light rate limit or challenge marker. |
| MEDIUM | Aggressive throttle + challenge required. |
| HIGH | Temporary block or strong throttle + real-time alert. |
| CRITICAL | Temporary block/firewall action + real-time alert + email. |

Start with DB-backed or in-memory demo enforcement if it is enough for PD2.

Redis-backed enforcement state is should-have-if-time-allows, not the first implementation step.

Redis is only needed if Nginx/proxy/FastAPI/workers need shared throttle/block/challenge state.

CAPTCHA/Turnstile challenge flow should be lightweight.

If Turnstile is used, server-side token verification is mandatory.

Challenge state must have expiry and audit logging.

Firewall/IP blocking must be temporary, reversible, logged, and safe from permanent bad firewall changes.

## Notes For Retraining

Retraining is required, but blind auto-promotion is not.

Implement retraining pipeline skeleton first:

- Manual/scheduled trigger.
- Analyst-labeled data export.
- Dataset validation.
- Dry-run/smoke mode.
- Job status.
- Evaluation output.
- Candidate artifact path.

Do not wait 20 real days for testing. Simulate the selected retraining window with timestamped labeled samples.

Decide daily vs 20-day retraining window and make code/docs consistent.

Keep two modes:

- **Dry-run/smoke mode:** validates scheduler, label export, dataset checks, command orchestration, and job status without long training.
- **Real training mode:** runs actual DistilBERT fine-tuning and evaluation.

Full DistilBERT retraining automation is should-have-if-time-allows.

Real training mode should not run in normal CI.

A retrained model should only be promoted if metrics pass defined thresholds.

Manual approval is required before promotion.

Keep previous model available for rollback.

Based on saved final artifacts, DistilBERT final confirmatory training took about 30.5 minutes per seed and about 1.5 hours for 3 seeds.

## Notes For Database, Retention, And Recovery

Add backup/restore and migration rollback as a lightweight runbook.

Use PostgreSQL/Supabase/Alembic expectations.

Do not build full backup automation unless an adviser/client specifically requires it.

Do not physically delete audit/traffic logs during PD2.

Use archive/hide/retention wording instead.

Suggested alert retention behavior:

- `archived_at`
- `archived_by`
- `archive_reason`
- `hidden_from_default_view`

Keep audit logs available for defense evidence and debugging.

## Notes For Wazuh Export

Wazuh integration should be export-only for PD2.

Export normalized alerts as JSON/JSONL suitable for Wazuh collection.

Do not add full Wazuh/SIEM deployment.

Export should include:

- `timestamp`
- Transaction ID.
- Source IP.
- Method.
- URI.
- CRS score.
- CRS rule IDs.
- Model prediction.
- Confidence tier.
- Action.
- Analyst status, if available.

Treat this as compatibility evidence, not a required SIEM deployment.

## Notes For Deferred / Overengineered Items

Do not add full Wazuh/SIEM deployment for PD2.

Use Wazuh export-only JSON/JSONL compatibility if time allows.

Do not add Kubernetes, Helm, or Terraform for PD2.

Use Docker Compose, env validation, runbooks, and checklists.

Do not add Kafka, Celery, or Elasticsearch for PD2.

Use `asyncio.Queue`, PostgreSQL, and structured JSON logs first.

Do not build custom SMTP infrastructure.

Use a transactional email API.

Do not use WebSockets unless two-way communication is required.

Use SSE/EventSource first and keep polling fallback.

Do not physically delete audit/traffic logs during PD2.

Use archive/hide/retention policy wording.

Do not auto-promote retrained models blindly.

Use candidate artifact, evaluation gate, and manual approval.
