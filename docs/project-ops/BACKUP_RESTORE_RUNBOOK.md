# Backup and Restore Runbook

**Last updated:** 2026-07-03  
**Audience:** operators, developers, capstone maintainer  
**Scope:** CyberTrace / Injection Alert System database and operational evidence backup/restore  
**Status:** operator documentation only; no backup job or restore automation is implemented by this file

---

## 1. Purpose

This runbook explains how to plan, execute, and verify backups and restores for CyberTrace.

The goal is not only to create backups. The goal is to prove that data can be restored safely when something fails.

A backup that has never been restored is not trustworthy.

---

## 2. Current Project Truth

Current expected state:

- Development uses local and/or SQLite-style test stores depending on test context.
- Production target is PostgreSQL/Supabase.
- Supabase/RLS operational hardening is not automated by this documentation branch.
- Backup automation is not implemented in the repository.
- Restore automation is not implemented in the repository.
- Migrations exist separately from this runbook.
- Security/audit evidence includes database records, WAF audit JSONL files, bridge logs, screenshots, and Markdown proof reports.

Do not claim automated backup/restore exists unless a future branch implements and verifies it.

---

## 3. Data Inventory

| Data Class | Example | Importance | Backup Method |
|---|---|---:|---|
| Alert/traffic records | WAF ingest alerts, predictions, action metadata | Critical | PostgreSQL/Supabase backup/export |
| Analyst feedback | Analyst label/email/timestamp | High | PostgreSQL/Supabase backup/export |
| WAF audit JSONL | `logs/modsecurity/*.jsonl` | High for local proof | File copy/archive |
| Demo proof reports | `reports/modsecurity-live-proof/*.md` | Medium-High | Git-tracked or external archive |
| Screenshots | proof screenshots | Medium | Git-tracked if intentionally committed or artifact archive |
| Model artifacts | `ml_model/model_registry/**` | Medium-High | Git/LFS/artifact store depending on size and policy |
| App config | `.env`, `frontend/.env.local` | Critical but secret | Secret manager/manual secure copy, never Git |
| Structured logs | bridge/backend JSON logs | Medium-High | log retention/export process |

---

## 4. Recovery Terms

Define these before any production claim:

| Term | Meaning | Project Placeholder |
|---|---|---|
| RPO | Recovery Point Objective: maximum acceptable data loss. | Not decided. |
| RTO | Recovery Time Objective: maximum acceptable restore time. | Not decided. |
| Backup owner | Person responsible for backups existing. | Not assigned. |
| Restore owner | Person responsible for executing restore. | Not assigned. |
| Approval owner | Person who approves destructive restore. | Adviser/client/team lead. |

Recommended for capstone staging/demo:

```text
RPO target: last successful daily backup or latest manual pre-demo backup.
RTO target: same day recovery for demo/staging.
```

Do not use this as a production SLA without client approval.

---

## 5. Backup Approaches

PostgreSQL documentation identifies three broad backup approaches: SQL dump, file-system-level backup, and continuous archiving/PITR. Each has trade-offs. For this project, the likely practical choices are Supabase managed backup/PITR and logical export using `pg_dump` for controlled snapshots.

### 5.1 Supabase managed backup

Use when:

- Supabase is the production database provider.
- Project plan supports required backup frequency and PITR.
- Restore can be performed through Supabase platform workflow.

Notes:

- Confirm backup availability for the actual Supabase plan.
- Confirm whether PITR is enabled and for how long.
- Confirm restore behavior and downtime expectations.
- Prefer restore-to-new-project or staging clone when validating backups.

### 5.2 Logical export with `pg_dump`

Use when:

- A portable SQL/archive backup is needed.
- You need a snapshot before migration.
- You need a local/staging restore drill.

General pattern:

```powershell
# Do not paste real credentials into terminal history if avoidable.
# Prefer environment variables or a secure connection string mechanism.
$env:PGPASSWORD = "<password>"
pg_dump --format=custom --file cybertrace_backup_YYYYMMDD_HHMM.dump "postgresql://<user>@<host>:5432/<db>?sslmode=require"
Remove-Item Env:\PGPASSWORD
```

Do not commit `.dump`, `.sql`, or `.env` files to Git.

### 5.3 Continuous archiving / PITR

Use when:

- You need point-in-time recovery.
- Downtime/data-loss tolerance is lower.
- Supabase plan and operational owner support it.

This is production-grade work. Do not claim PITR unless it is enabled and restore-tested.

---

## 6. Backup Naming Convention

Use a boring, searchable naming scheme:

```text
cybertrace_<env>_<type>_<YYYYMMDD-HHMM>_<git-sha-short>.<ext>
```

Examples:

```text
cybertrace_staging_pg_dump_20260703-1500_dcfd3c2.dump
cybertrace_demo_modsec_audit_20260703-1500.tar.gz
```

Include a sidecar metadata file:

```text
cybertrace_staging_pg_dump_20260703-1500_dcfd3c2.metadata.md
```

Metadata template:

```markdown
# Backup Metadata

- Environment:
- Database/project:
- Git SHA:
- Migration revision:
- Backup command:
- Backup started:
- Backup completed:
- Backup size:
- Operator:
- Storage location:
- Encryption/storage control:
- Restore-tested: yes/no
- Restore test date:
- Notes:
```

---

## 7. Pre-Backup Checklist

Before creating a backup:

- [ ] Confirm target environment.
- [ ] Confirm database/project ID.
- [ ] Confirm Git SHA deployed.
- [ ] Confirm current migration revision.
- [ ] Confirm whether backup contains sensitive data.
- [ ] Confirm storage destination.
- [ ] Confirm backup will not be committed to Git.
- [ ] Confirm credentials will not be printed or stored in shell history.
- [ ] Confirm operator has approval for production backup.

---

## 8. Logical Backup Procedure

### 8.1 Prepare environment

```powershell
git rev-parse --short HEAD
```

Record current migration revision if applicable:

```powershell
alembic current
```

If using Supabase CLI or dashboard, also record the Supabase project/environment name.

### 8.2 Run backup

Preferred archive format:

```powershell
$timestamp = Get-Date -Format "yyyyMMdd-HHmm"
$sha = git rev-parse --short HEAD
$out = "cybertrace_staging_pg_dump_${timestamp}_${sha}.dump"
pg_dump --format=custom --file $out "postgresql://<user>:<password>@<host>:5432/<db>?sslmode=require"
```

Safer secret handling depends on the environment. Avoid pasting passwords directly into commands if possible.

### 8.3 Verify backup file exists

```powershell
Get-Item $out | Format-List Name, Length, LastWriteTime
```

### 8.4 Store backup safely

- [ ] Store outside Git.
- [ ] Restrict access.
- [ ] Encrypt if policy requires.
- [ ] Record storage location in metadata.
- [ ] Do not upload to public/shared drive without access control.

---

## 9. Restore Strategy

### Preferred: restore to a new/staging target first

This is the safest restore pattern.

Do not restore directly over production unless:

- production is already declared broken,
- the restore target is approved,
- a current backup exists,
- stakeholders approve downtime/data-loss risk,
- there is a rollback/abort plan.

### Restore options

| Restore Target | Use When | Risk |
|---|---|---:|
| New local DB | developer validation | Low |
| Staging Supabase project | restore drill / pre-prod validation | Medium |
| Existing staging DB | staging reset | Medium |
| Production DB | emergency only | High |

---

## 10. Restore-to-New-Database Procedure

### 10.1 Create target database

Create a clean local or staging PostgreSQL database.

Example local:

```powershell
createdb cybertrace_restore_test
```

### 10.2 Restore archive-format dump

```powershell
pg_restore --dbname cybertrace_restore_test --clean --if-exists cybertrace_staging_pg_dump_YYYYMMDD-HHMM_SHA.dump
```

If using connection string:

```powershell
pg_restore --dbname "postgresql://<user>:<password>@<host>:5432/<db>?sslmode=require" --clean --if-exists cybertrace_staging_pg_dump_YYYYMMDD-HHMM_SHA.dump
```

### 10.3 Verify schema

```powershell
psql cybertrace_restore_test -c "\dt"
```

### 10.4 Verify critical records

Examples to adapt to current schema:

```sql
select count(*) from traffic_logs;
select max(created_at) from traffic_logs;
select count(*) from traffic_logs where transaction_id is not null;
```

### 10.5 Verify app can connect

Use a staging/local `.env` pointing to the restored database and run:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/integration/test_app_startup.py
.venv\Scripts\python.exe -m pytest -q tests/integration/test_api.py
```

---

## 11. Production Restore Emergency Procedure

Use only in emergency.

### 11.1 Decision gate

Stop unless all are true:

- [ ] Production data is broken or unavailable.
- [ ] Incident owner approves restore.
- [ ] Restore point is selected.
- [ ] Current broken state is backed up if possible.
- [ ] Expected data loss is documented.
- [ ] Expected downtime is documented.
- [ ] Communication plan exists.

### 11.2 Before restore

```text
Environment:
Current Git SHA:
Current migration revision:
Backup selected:
Restore target:
Expected data loss:
Expected downtime:
Approval:
Operator:
```

### 11.3 Restore

Follow Supabase platform restore workflow or `pg_restore`, depending on the chosen backup source.

Do not paste production secrets into chat, issue comments, screenshots, or commit messages.

### 11.4 After restore

Run:

```powershell
.venv\Scripts\python.exe scriptsun_final_demo_smoke.py --mode backend --json
```

Then run app-specific checks:

- [ ] Backend health works.
- [ ] Dashboard can load.
- [ ] `/api/stats` works through BFF if applicable.
- [ ] `/api/ml-health` works.
- [ ] Known WAF transaction lookup works if restoring proof data.
- [ ] New WAF ingest can be created in staging/demo mode.
- [ ] Logs contain request IDs.

---

## 12. WAF Audit JSONL Backup

Local WAF proof logs are files, not database rows.

Likely paths:

```text
logs/modsecurity/modsec_audit.jsonl
logs/modsecurity/demo-target/modsec_audit.jsonl
```

Backup command:

```powershell
$timestamp = Get-Date -Format "yyyyMMdd-HHmm"
Compress-Archive -Path logs\modsecurity\* -DestinationPath "cybertrace_modsecurity_logs_$timestamp.zip"
```

Rules:

- Do not include secrets.
- Treat WAF logs as sensitive because they may include payload fragments, source IPs, paths, headers, and attack strings.
- Do not upload publicly.
- Do not use WAF logs as permanent production retention without a retention policy.

---

## 13. Restore Drill Template

Use this for every restore drill:

```markdown
# Restore Drill Record

- Date:
- Operator:
- Environment restored from:
- Restore target:
- Backup file/source:
- Git SHA:
- Migration revision:
- Commands used:
- Restore result: PASS/FAIL
- Verification commands:
- Verification result:
- Data loss observed:
- Time to restore:
- Issues found:
- Follow-up actions:
```

---

## 14. Security Rules

Never:

- Commit backup files.
- Commit `.env` files.
- Paste production DB URLs into docs, PRs, or tickets.
- Print service-role keys.
- Restore production without approval.
- Run destructive restore commands without confirming target database.
- Assume backup is good without restore testing.

Always:

- Prefer restore to non-production first.
- Record backup metadata.
- Restrict backup access.
- Verify restored data.
- Keep backup and retention rules aligned.

---

## 15. What Is Not Implemented Yet

This runbook does not implement:

- automated scheduled backups,
- automated restore scripts,
- backup encryption tooling,
- remote backup storage,
- PITR enablement,
- Supabase project setting changes,
- migration rollback automation,
- retention jobs.

Those are separate implementation/operations tasks.

---

## 16. Done Criteria for Future Implementation

A future branch may mark backup/restore implementation done only when:

- [ ] Backup source is configured.
- [ ] Backup schedule exists.
- [ ] Restore target exists.
- [ ] Restore drill passes.
- [ ] Secrets are not exposed.
- [ ] RPO/RTO are documented.
- [ ] Owner is assigned.
- [ ] Runbook reflects the tested commands.

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
