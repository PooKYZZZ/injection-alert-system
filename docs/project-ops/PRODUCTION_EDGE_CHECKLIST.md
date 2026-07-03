# Production Edge Checklist

**Last updated:** 2026-07-03  
**Audience:** capstone developers, demo operator, adviser/panel reviewer, future maintainer  
**Scope:** CyberTrace / Injection Alert System production-readiness checklist  
**Status:** operator documentation only; this file does not implement production deployment

---

## 1. Purpose

This checklist defines what must be true before anyone claims that CyberTrace is production-ready or production-like at the network edge.

It is intentionally stricter than a local demo checklist. A local PD2 demo can prove the WAF-to-dashboard path without satisfying every item here. Production readiness means the system can be operated safely when exposed beyond a controlled local environment.

This document is based on current project truth:

- FastAPI backend exists.
- Next.js dashboard/BFF exists.
- ModSecurity/OWASP CRS proof path exists locally.
- Demo-target WAF path exists locally through `localhost:8089` when the demo-target profile is enabled.
- Structured JSON logs, `X-Request-ID`, request/trace/transaction correlation, redaction, and smoke proof exist.
- Runtime enforcement is not fully implemented.
- Named env-backed accounts, server-side BFF RBAC, local login throttling, and safe auth audit events are implemented. Email, SSE, MFA/2FA, managed identity, and distributed auth controls are not.
- Backup automation, restore automation, retention jobs, Wazuh export, and production SIEM are not implemented by this documentation branch.

---

## 2. Non-Production Truth Statement

Use this wording in defense/demo docs unless production work has actually been implemented and verified:

```text
CyberTrace currently has local and production-like proof for the WAF -> audit log -> bridge -> FastAPI ingest -> ML prediction -> policy metadata -> dashboard path. It is not yet a fully production-deployed edge security platform. Production edge hardening, managed account security, runtime enforcement, backup/restore automation, retention jobs, alerting, and SIEM export remain separate implementation or operations tasks.
```

Do not write:

```text
CyberTrace is production-ready.
```

unless every blocking item in this checklist is satisfied and verified.

---

## 3. Production Edge Readiness Levels

| Level | Meaning | Allowed Claim |
|---|---|---|
| Level 0 — Local Development | App runs locally with dev/demo settings. | Development environment only. |
| Level 1 — Local Proof | WAF proof path works locally; dashboard shows persisted alerts. | Local WAF-to-dashboard proof. |
| Level 2 — Production-like Demo | Docker Compose proof, structured logs, smoke script, manual runbook, no fake claims. | Production-like demo, not production deployment. |
| Level 3 — Staging Edge | Real domain/staging network, secrets managed, TLS, staging DB, backup/restore tested. | Staging-ready. |
| Level 4 — Production Edge | Hardened auth/RBAC/MFA, WAF routing, monitored backups, retention, alerting, rollback, operational owners. | Production-ready after approval. |

Current expected status after observability and smoke-suite branches: **Level 2**, unless later branches prove otherwise.

---

## 4. Hard Blockers Before Production Claim

These are blocking items. If any item is false, do not claim production readiness.

| Area | Required Before Production | Current Expected Truth |
|---|---|---|
| Public edge | WAF is actually in request path for protected traffic. | Local proof exists; production edge not proven. |
| TLS | HTTPS/TLS termination configured and tested. | Not implemented in repo. |
| Secrets | Production secrets stored outside Git and not printed/logged. | Required; verify per environment. |
| Auth | Real user accounts replace demo credentials. | Named env-backed accounts and scrypt hashes are implemented; managed identity and account-management UI are not. |
| RBAC | Admin/Analyst/Viewer roles enforced server-side and UI-side. | Server-side BFF enforcement is implemented; UI affordance gating remains deferred. |
| MFA/2FA | MFA enrollment, challenge, recovery, and reset flow. | Not started unless changed later. |
| Runtime response | Block/throttle/challenge/IP block decisions enforced, not just recorded. | Partial metadata only unless changed later. |
| Backups | Backup schedule defined and restore tested. | Docs-only until tested. |
| Rollback | Migration rollback or restore fallback tested. | Docs-only until tested. |
| Retention | Archive/hide/delete retention behavior implemented and verified. | Docs-only policy until implemented. |
| Monitoring | Alerts for failed bridge posts, model unavailable, queue full, app failures. | Partial logs/health only. |
| Email/SSE | Timely operator notifications and/or real-time dashboard alerts. | Not started unless changed later. |
| SIEM export | Wazuh/JSONL export-only path if required. | Not started unless changed later. |

---

## 5. Edge / Network Checklist

### 5.1 Required checks

- [ ] Protected application traffic enters through WAF, not directly to backend.
- [ ] Backend is not publicly exposed unless intentionally required and authenticated.
- [ ] Frontend/BFF is the browser-facing API boundary.
- [ ] FastAPI internal routes require internal bearer token.
- [ ] `/health` public behavior is intentional and documented.
- [ ] FastAPI docs/OpenAPI UI are disabled outside development.
- [ ] CORS is restricted to approved origins outside development.
- [ ] Body size limits are configured and tested.
- [ ] Rate limiting or upstream abuse protection is defined for public endpoints.
- [ ] TLS/HTTPS termination is configured at the production edge.
- [ ] HTTP-to-HTTPS redirect is configured where applicable.
- [ ] Security headers are configured and verified.

### 5.2 Verification commands / evidence

Record exact evidence in `docs/project-ops/STATUS.md` or a dated proof report:

```powershell
# Local proof only, not production claim
.venv\Scripts\python.exe scriptsun_final_demo_smoke.py --mode waf-8088 --json
.venv\Scripts\python.exe scriptsun_final_demo_smoke.py --mode demo-target-8089 --json
```

For production/staging edge, add real commands later, for example:

```powershell
curl.exe -I https://<staging-domain>/
curl.exe -I https://<staging-domain>/api/health
curl.exe -s -o NUL -w "%{http_code}`n" "https://<staging-domain>/<protected-path>?id=1%27%20OR%201%3D1--"
```

Do not add placeholder output and call it verified.

---

## 6. Backend Environment Checklist

- [ ] `ENVIRONMENT` or equivalent production flag is set correctly.
- [ ] `API_SECRET_KEY` is present and strong.
- [ ] `AUTH_SECRET` is present and strong.
- [ ] Database URL is production/staging specific and not committed.
- [ ] Model registry path is read-only in production runtime if possible.
- [ ] Runtime cannot silently fall back to dev/demo auth.
- [ ] Non-dev startup fails fast when required secrets are missing.
- [ ] Logs redact secret-like keys and authorization/cookie values.
- [ ] `X-Request-ID` exists on handled and generic unhandled failures.
- [ ] WAF bridge logs are JSON parseable.
- [ ] Queue overflow returns controlled `503` with `Retry-After`.

---

## 7. Authentication and Account Security Checklist

This is a production blocker if the dashboard is exposed beyond a controlled demo.

- [ ] Replace demo credentials with real managed accounts or project-owned account store.
- [ ] Persist roles: Admin, Analyst, Viewer.
- [x] Put roles and per-account `authz_version` into session claims safely.
- [x] Enforce role checks on server routes, not only UI.
- [ ] Hide/disable unauthorized UI actions.
- [x] Add login and route-authorization audit events.
- [x] Add per-identifier/global local login throttling and cooldown.
- [ ] Add account recovery/reset process.
- [ ] Add MFA/2FA enrollment and challenge.
- [ ] Add MFA recovery/reset procedure.
- [ ] Document emergency admin access procedure.

Minimum production claim requires real accounts + RBAC + login hardening. MFA/2FA is a client requirement and must not be described as implemented until it exists.

---

## 8. WAF and Bridge Checklist

- [ ] WAF blocks known SQLi test traffic in the actual protected path.
- [ ] Normal traffic passes through WAF without obvious false-positive breakage.
- [ ] CRS-only baseline report exists.
- [ ] Demo-target WAF proof exists.
- [ ] Bridge follows audit log reliably.
- [ ] Bridge handles duplicate transactions idempotently.
- [ ] Bridge retries transient failures safely.
- [ ] Bridge configuration errors are JSON logs.
- [ ] Bridge never logs API secret or Authorization header.
- [ ] Backend lookup by `transaction_id` works.
- [ ] WAF and FastAPI events can be correlated by `transaction_id` and `request_id`.

---

## 9. Observability Checklist

- [ ] Structured JSON logs exist for request boundary events.
- [ ] Structured JSON logs exist for WAF bridge events.
- [ ] Structured JSON logs exist for WAF ingest events.
- [ ] Prediction/policy outcome is logged or correlated from ingest completion.
- [ ] `request_id` is present in request logs.
- [ ] `transaction_id` is present for WAF flows.
- [ ] Valid W3C `traceparent` trace IDs are preserved where applicable.
- [ ] Invalid request/trace IDs are sanitized or replaced.
- [ ] Secrets are redacted recursively.
- [ ] Raw credentials, cookies, API keys, DB URLs, and authorization headers are not logged.
- [ ] Log format is stable enough for grep/JSON parser/Wazuh export later.

Do not claim full SIEM. Current state is structured logs and future export readiness.

---

## 10. Database and Supabase Checklist

- [ ] Production and staging are separate projects/databases.
- [ ] Direct production writes are restricted.
- [ ] Database credentials are scoped and rotated if exposed.
- [ ] Supabase project has multiple owners or break-glass access plan.
- [ ] Supabase account MFA is enabled for owners.
- [ ] SSL is enforced where applicable.
- [ ] Network restrictions are configured where plan supports it.
- [ ] Supabase Security Advisor is reviewed.
- [ ] Supabase Performance Advisor is reviewed.
- [ ] RLS is enabled on exposed schemas/tables.
- [ ] RLS policies are reviewed for `anon`, `authenticated`, and `service_role` behavior.
- [ ] Service-role key is never exposed to browser or logs.
- [ ] Backup/PITR plan is chosen based on Supabase plan.
- [ ] Restore drill is performed on a non-production target.

---

## 11. Backup / Restore Readiness Checklist

Production claim is blocked until a backup and restore drill is verified.

- [ ] Identify data stores: PostgreSQL/Supabase, local WAF audit JSONL, screenshots/proof reports, model artifacts if required.
- [ ] Define RPO: acceptable data loss window.
- [ ] Define RTO: acceptable restoration time.
- [ ] Choose backup type: Supabase automatic backup/PITR, logical export, or external process.
- [ ] Document who can access backups.
- [ ] Document where backups are stored.
- [ ] Document restore-to-new-project procedure.
- [ ] Test restore in non-production.
- [ ] Verify restored app can start and query critical endpoints.
- [ ] Record last restore drill date and result.

Use `BACKUP_RESTORE_RUNBOOK.md` for detailed steps.

---

## 12. Migration Rollback Checklist

- [ ] Every schema change has an associated migration file.
- [ ] Migration is tested against a staging or local clone.
- [ ] Backup exists before migration.
- [ ] Rollback decision tree exists: forward fix, downgrade, restore.
- [ ] Downgrade exists only if written and tested.
- [ ] Destructive migration has explicit approval.
- [ ] Post-migration smoke checks are defined.
- [ ] Post-rollback verification is defined.

Use `MIGRATION_ROLLBACK_RUNBOOK.md` for detailed steps.

---

## 13. Retention and Audit Checklist

- [ ] Data classes are documented.
- [ ] Audit/security logs are preserved for the agreed period.
- [ ] Alert records are not physically deleted casually.
- [ ] Archive/hide behavior is preferred over physical delete.
- [ ] Retention window is approved by adviser/client before implementation.
- [ ] Retention does not delete data needed for demo proof, incident response, or audit.
- [ ] Backups and exports follow the same retention/disposal policy.

Use `RETENTION_POLICY.md` for detailed policy.

---

## 14. Deployment Approval Checklist

Before a production/staging cutover, require a signed or recorded approval containing:

- [ ] Target environment name.
- [ ] Git commit SHA.
- [ ] Migration revision.
- [ ] Backup taken and restore target tested.
- [ ] Rollback strategy.
- [ ] Expected downtime.
- [ ] Known risks.
- [ ] Owner approving deployment.
- [ ] Operator executing deployment.
- [ ] Post-deploy checks completed.

---

## 15. Known Deferred Items

These remain deferred unless another branch implements them:

- Real-time dashboard alerts.
- Email notifications.
- Managed identity or persistent account storage beyond the env-backed registry.
- UI role-gating affordances; server-side RBAC is implemented.
- 2FA/MFA.
- Runtime enforcement state.
- CAPTCHA/Turnstile challenge flow.
- IP blocking/firewall handoff.
- Automated retraining pipeline.
- Dataset validation for retraining.
- Challenger evaluation gate.
- Wazuh export-only integration.
- Full SIEM deployment.
- Kubernetes/Helm/Terraform.
- Kafka/Celery/Elasticsearch.

---

## 16. Evidence Template

Use this section when marking any item as done:

```text
Date:
Branch / commit:
Environment:
Command(s):
Result:
Evidence file or screenshot:
Known limitations:
Reviewer:
```

---

## Source Basis

These docs intentionally use public, stable, operator-facing sources. They are not claiming that all controls are already implemented in the repository.

- NIST SP 800-34 Rev. 1, *Contingency Planning Guide for Federal Information Systems*: https://csrc.nist.gov/pubs/sp/800/34/r1/final
- NIST SP 800-53 Rev. 5, *Security and Privacy Controls for Information Systems and Organizations*: https://csrc.nist.gov/pubs/sp/800/53/r5/upd1/final
- NIST SP 800-92, *Guide to Computer Security Log Management*: https://csrc.nist.gov/pubs/sp/800/92/final
- OWASP Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- OWASP CI/CD Security Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/CI_CD_Security_Cheat_Sheet.html
- OWASP Secure Coding with AI Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secure_Coding_with_AI_Cheat_Sheet.html
- PostgreSQL Backup and Restore: https://www.postgresql.org/docs/current/backup.html
- PostgreSQL `pg_dump`: https://www.postgresql.org/docs/current/app-pgdump.html
- PostgreSQL `pg_restore`: https://www.postgresql.org/docs/current/app-pgrestore.html
- PostgreSQL Row Security Policies: https://www.postgresql.org/docs/current/ddl-rowsecurity.html
- PostgreSQL `CREATE POLICY`: https://www.postgresql.org/docs/current/sql-createpolicy.html
- PostgreSQL `DELETE`: https://www.postgresql.org/docs/current/sql-delete.html
- PostgreSQL Partitioning: https://www.postgresql.org/docs/current/ddl-partitioning.html
- Alembic Tutorial / Migrations: https://alembic.sqlalchemy.org/en/latest/tutorial.html
- Supabase Production Checklist: https://supabase.com/docs/guides/deployment/going-into-prod
- Supabase Database Backups: https://supabase.com/docs/guides/platform/backups
- Supabase Row Level Security: https://supabase.com/docs/guides/database/postgres/row-level-security
- Supabase Database Advisors: https://supabase.com/docs/guides/database/database-advisors
- Supabase Managing Environments: https://supabase.com/docs/guides/deployment/managing-environments
- Supabase Local Development / Migrations: https://supabase.com/docs/guides/local-development/overview
- Google Engineering Practices, Small CLs: https://google.github.io/eng-practices/review/developer/small-cls.html
- Google Engineering Practices, What to Look For in a Code Review: https://google.github.io/eng-practices/review/reviewer/looking-for.html
- Diátaxis documentation framework: https://diataxis.fr/
- Google Technical Writing: https://developers.google.com/tech-writing/overview
- GitHub Docs Style Guide: https://docs.github.com/en/contributing/writing-for-github-docs/style-guide
