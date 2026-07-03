# Retention Policy for Alerts, Audit Logs, and Operational Evidence

**Last updated:** 2026-07-03  
**Audience:** developers, operators, adviser/panel reviewer, future maintainer  
**Scope:** CyberTrace alert/audit/traffic/security records  
**Status:** policy documentation only; no retention job, archive column, hide column, or physical delete behavior is implemented by this file

---

## 1. Purpose

This policy defines how CyberTrace should think about retaining and disposing of security-relevant records.

The goal is to balance:

- security investigation needs,
- academic demo evidence,
- storage limits,
- privacy/data minimization,
- auditability,
- safe future implementation.

This file must not be read as implementation proof.

---

## 2. Current Project Truth

Expected current truth:

- Alerts/traffic logs are persisted by the backend.
- WAF audit JSONL proof files exist locally.
- Structured logs exist for bridge/FastAPI boundaries.
- Analyst feedback exists partially.
- No production retention job is implemented.
- No archive/hide database behavior is implemented unless a future branch adds it.
- No physical delete policy is implemented in code by this docs branch.

---

## 3. Policy Summary

Default policy:

```text
Preserve security records by default.
Prefer archive/hide over physical delete.
Do not physically delete audit/traffic records without explicit approved retention implementation.
Do not retain sensitive data forever without a documented reason and disposal process.
```

---

## 4. Data Classes

| Data Class | Examples | Sensitivity | Default Handling |
|---|---|---:|---|
| Alert records | prediction, confidence, action_taken, status | Medium-High | Retain for investigation/demo |
| Traffic/WAF ingest metadata | transaction_id, source_ip, path, headers metadata, CRS score/rules | High | Retain with access control |
| WAF audit JSONL | ModSecurity audit entries | High | Retain only in controlled storage |
| Structured backend logs | request_id, trace_id, transaction_id, route, status | Medium | Rotate/archive by environment policy |
| Analyst feedback | analyst label/email/timestamp | High | Retain as audit trail |
| Raw payloads | request body/query snippets | High/Critical | Avoid or sanitize; do not expand storage |
| Secrets | tokens, API keys, cookies, passwords | Critical | Never retain in logs/data |
| Screenshots/proof reports | dashboard evidence, proof notes | Medium | Retain as capstone evidence |

---

## 5. Proposed Retention Windows

These are proposed defaults, not implemented code.

| Data | Development | Demo/Staging | Production Candidate |
|---|---:|---:|---:|
| Alert records | until reset/manual cleanup | 90 days or capstone period | 180-365 days, client-approved |
| Traffic/WAF metadata | 30-90 days | 90 days | 180-365 days, client-approved |
| WAF audit JSONL | 7-30 days local | 30-90 days | policy-defined, storage-controlled |
| Structured app logs | 7-30 days | 30-90 days | policy-defined based on log volume |
| Analyst feedback | capstone period | 180 days | align with model governance policy |
| Demo screenshots/reports | capstone period | capstone period | not production evidence by default |
| Backups | manual/local | until replaced by newer verified backup | per backup policy/RPO/RTO |

Before implementing these, get approval from adviser/client because retention is partly a governance decision.

---

## 6. Archive/Hide vs Physical Delete

### Archive/hide preferred

Preferred future behavior:

```text
archived_at timestamp
hidden_at timestamp
retention_reason
retention_actor
retention_note
```

Archive/hide means:

- record remains available for audit/admin review,
- normal dashboard can hide old/noisy records,
- investigations can still recover history,
- accidental loss risk is lower.

### Physical delete restricted

Physical delete should require:

- approved retention policy,
- backup/restore plan,
- audit trail of deletion action,
- explicit filters,
- dry run/count before execution,
- reviewer approval.

Never implement broad physical deletes casually.

Bad:

```sql
DELETE FROM traffic_logs;
```

Better future pattern:

```sql
-- Example only. Do not run until implemented and approved.
UPDATE traffic_logs
SET archived_at = now()
WHERE created_at < now() - interval '180 days'
  AND archived_at IS NULL;
```

---

## 7. Retention Procedure for Operators

Until automated retention exists, use manual review only.

### 7.1 Review data volume

Use database-specific queries later. Example only:

```sql
select count(*) from traffic_logs;
select min(created_at), max(created_at) from traffic_logs;
select count(*) from traffic_logs where transaction_id is not null;
```

### 7.2 Decide action

| Situation | Action |
|---|---|
| Local dev DB too large | Reset local DB only after confirming no needed proof data. |
| Demo proof DB contains important screenshots/transactions | Preserve until capstone defense is complete. |
| Production candidate contains stale alerts | Archive/hide only after policy approval. |
| Logs contain secrets | Treat as incident; rotate exposed secret and restrict/delete leaked log per incident process. |

### 7.3 Record decision

```markdown
# Retention Decision Record

- Date:
- Operator:
- Environment:
- Data class:
- Age range:
- Count:
- Decision: keep / archive / hide / delete
- Reason:
- Approval:
- Backup before action: yes/no
- Commands run:
- Verification:
```

---

## 8. WAF Audit JSONL Retention

WAF JSONL can be sensitive because it may include:

- source IP,
- request URI,
- headers,
- query strings,
- attack payload fragments,
- CRS rule matches.

Rules:

- [ ] Do not commit live WAF JSONL unless intentionally sanitized and required for proof.
- [ ] Do not upload WAF logs publicly.
- [ ] Keep demo proof extracts minimal.
- [ ] Prefer screenshots/reports with transaction IDs over full raw logs.
- [ ] Use compression/encryption for long-term archive if needed.
- [ ] Document retention and disposal.

---

## 9. Structured Log Retention

Current logs are useful because they include:

- `request_id`,
- `trace_id`,
- `transaction_id`,
- route/status/duration,
- WAF bridge events,
- queue-full/model-not-ready events,
- redacted fields.

Rules:

- [ ] Keep fields stable.
- [ ] Do not add raw credentials.
- [ ] Do not add raw request body unless strictly sanitized and approved.
- [ ] Keep logs single-line JSON where possible.
- [ ] Rotate logs based on environment.
- [ ] Protect logs from unauthorized access.

---

## 10. Analyst Feedback Retention

Analyst feedback can influence future retraining or evaluation.

Until full override/audit trail exists:

- [ ] Preserve analyst label/email/timestamp records.
- [ ] Do not use feedback for automatic model promotion.
- [ ] Do not delete feedback without approval.
- [ ] Keep analyst PII limited.
- [ ] Document how feedback exports will be validated before retraining.

Future fields to consider:

```text
old_prediction
new_analyst_label
old_action_taken
new_action_requested
reason
analyst_id
created_at
model_version
review_status
```

---

## 11. Backup and Retention Relationship

Retention applies to backups too.

If records are archived/hidden/deleted in the live DB, old backups may still contain them.

Before claiming disposal:

- [ ] Identify backup copies.
- [ ] Identify exported JSON/CSV files.
- [ ] Identify screenshots/proof reports.
- [ ] Identify WAF JSONL archives.
- [ ] Define backup expiry.
- [ ] Confirm disposal if required.

---

## 12. Legal / Privacy Note

This is not legal advice.

Before production/client deployment, confirm retention requirements with the client/adviser, especially for:

- IP addresses,
- security event logs,
- analyst/user identifiers,
- attack payload samples,
- customer/land-record demo data,
- email notifications,
- backups.

---

## 13. Future Implementation Plan

A safe retention implementation should be separate from this docs branch.

Suggested future branch:

```text
feat/alert-retention-archive-policy
```

Suggested implementation order:

1. Add archive/hide fields through migration.
2. Add repository methods for archive/hide, not physical delete.
3. Add admin-only operation or script.
4. Add audit trail.
5. Add tests proving no physical delete occurs.
6. Add dashboard filter for archived records.
7. Add retention runbook update.

Do not implement retention by adding broad DELETE jobs first.

---

## 14. Done Criteria for Retention Implementation

This docs branch can mark the policy as documented. Future implementation is done only when:

- [ ] Data classes are implemented in schema/policy.
- [ ] Archive/hide behavior exists.
- [ ] Physical delete is restricted or absent.
- [ ] Audit trail exists for retention actions.
- [ ] Tests prove records are preserved/hidden as intended.
- [ ] Backup interaction is documented.
- [ ] Client/adviser-approved retention windows are recorded.

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
