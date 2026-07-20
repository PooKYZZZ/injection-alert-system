# Migration Rollback Runbook

> General rollback policy background. Current V6.1 deployment configuration is
> documented in [`../SETUP.md`](../SETUP.md) and the security architecture in
> [`../architecture.md`](../architecture.md).

**Last updated:** 2026-07-13
**Audience:** developers, database operator, reviewer  
**Scope:** CyberTrace database/schema migration safety and rollback decision-making  
**Status:** operator documentation only; no migration or rollback automation is implemented by this file

---

## 1. Purpose

This runbook explains how to prepare for, execute, and recover from database migrations.

The main rule:

```text
Do not assume rollback exists just because Alembic has a downgrade concept.
Rollback exists only when the specific migration has a written, reviewed, and tested downgrade path or a tested restore fallback.
```

---

## 2. Current Project Truth

Current truth:

- The project uses SQLAlchemy/Alembic-style migration concepts.
- Production target is PostgreSQL/Supabase.
- The hosted Supabase migration head is `20260712_000020`.
- Hosted rollback must not be performed casually. The migration chain includes auth, MFA, notification, and authorization boundaries whose data and function contracts must remain compatible.
- Disposable PostgreSQL is the required target for downgrade and re-upgrade testing before any hosted rollback decision.
- This runbook does not create migrations.
- This runbook does not change the database.
- This runbook does not apply Supabase settings.
- The PR4 shadow recommendation migration is `20260720_000023`, child of
  `20260720_000022`. Its downgrade removes only `enforcement_recommendations`
  after explicit evidence export/review; it never deletes `traffic_logs`.

## 3.1 Required rollback boundaries

- **Application rollback:** first determine whether the failure is application-only. If the schema is valid, roll back or forward-fix the application while keeping the database at the current head.
- **Database rollback:** take and verify a backup before any downgrade. Use a disposable PostgreSQL database to prove the exact downgrade and re-upgrade path. Hosted downgrade requires explicit approval and a tested restore fallback.
- **Runtime feature kill switches:** disable the affected `AUTH_*` availability flag at container start when a feature must be stopped. Recreate or restart the frontend container so the new runtime values are used; flags do not replace authentication or authorization.
- **Container recovery:** rebuild only when the image changed; otherwise recreate the frontend container with the reviewed runtime environment. Confirm the container sees the intended flag values and inspect logs after the first request.
- **Compatibility warning:** old application code may not understand new auth/MFA/outbox schema or function contracts. Do not combine an application rollback with a database downgrade unless the older code/schema pair has been tested together.

---

## 3. Migration Risk Classes

| Risk Class | Examples | Approval Required | Rollback Requirement |
|---|---|---|---|
| Low | add nullable column, add index concurrently where supported | developer review | forward fix acceptable |
| Medium | add non-null column with default, rename internal column, add constraint | team lead/adviser | tested downgrade or restore fallback |
| High | drop column/table, destructive data migration, enum removal, auth/RLS policy change | explicit approval | backup + restore drill + tested plan |
| Critical | production data rewrite, irreversible migration, security policy change on exposed tables | client/adviser approval | restore plan required before execution |

---

## 4. Pre-Migration Checklist

Before running any migration outside a throwaway local DB:

- [ ] Confirm target environment: local, staging, production.
- [ ] Confirm current Git SHA.
- [ ] Confirm current migration revision.
- [ ] Confirm migration file(s) being applied.
- [ ] Read `upgrade()` and `downgrade()` bodies.
- [ ] Identify destructive operations.
- [ ] Identify long-running operations.
- [ ] Identify locks or downtime risk.
- [ ] Confirm backup exists.
- [ ] Confirm restore target exists.
- [ ] Confirm approval for target environment.
- [ ] Confirm post-migration checks.
- [ ] Confirm rollback/fallback decision tree.

Record:

```text
Environment:
Database/project:
Git SHA:
Current revision:
Target revision:
Backup source:
Operator:
Reviewer:
Approval:
Expected risk:
```

---

## 5. Local Dry Run

Run locally first when possible.

```powershell
alembic current
alembic history --verbose
alembic upgrade head
alembic current
```

Run tests:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/integration
.venv\Scripts\python.exe -m pytest -q
```

If migration changes API contracts, run frontend/BFF tests too.

Do not proceed to staging/production if local migration fails.

---

## 6. Staging Dry Run

For staging or Supabase branch/project:

- [ ] Take staging backup or snapshot.
- [ ] Apply migration.
- [ ] Run app startup checks.
- [ ] Run API smoke checks.
- [ ] Run WAF/demo smoke if relevant.
- [ ] Verify RLS/policy behavior if migration touches policies.
- [ ] Verify dashboard can read affected data.
- [ ] Record timing and errors.

Suggested commands:

```powershell
alembic current
alembic upgrade head
.venv\Scripts\python.exe scriptsun_final_demo_smoke.py --mode backend --json
.venv\Scripts\python.exe -m pytest -q tests/integration/test_app_startup.py
```

Adapt commands to the repo's current operational flow.

---

## 7. Production Migration Procedure

### 7.1 Stop conditions

Stop if any are true:

- [ ] Backup not available.
- [ ] Target environment uncertain.
- [ ] Migration has destructive change without approval.
- [ ] Downgrade is empty/unsafe and no restore fallback exists.
- [ ] Staging dry run failed.
- [ ] Secrets would need to be pasted into logs/chat.
- [ ] Migration touches auth/RLS without security review.

### 7.2 Execute

Record before running:

```text
Command:
Operator:
Start time:
```

Run migration with the project's approved command. Example only:

```powershell
alembic upgrade head
```

### 7.3 Verify after migration

```powershell
alembic current
.venv\Scripts\python.exe scriptsun_final_demo_smoke.py --mode backend --json
.venv\Scripts\python.exe -m pytest -q tests/integration/test_app_startup.py
```

Manual checks:

- [ ] Login/dashboard loads if frontend is part of release.
- [ ] Alerts list works.
- [ ] Alert detail works.
- [ ] Stats/ML health works.
- [ ] WAF transaction lookup works if relevant.
- [ ] Logs include request IDs.
- [ ] No secret values appear in logs.

---

## 8. Rollback Decision Tree

When a migration causes failure:

```text
1. Is the issue app-only and schema is valid?
   -> Prefer app rollback/forward fix.

2. Is the issue a small missing index/constraint/default?
   -> Prefer forward migration fix if safe.

3. Is the issue caused by bad data migration or destructive schema change?
   -> Consider restore from backup.

4. Does the specific migration have a tested downgrade?
   -> Downgrade may be allowed after approval.

5. Is downgrade untested or destructive?
   -> Do not run downgrade blindly; use restore plan.
```

Senior rule:

```text
Forward fix is often safer than downgrade for production if data has already changed, but destructive migrations require restore planning before execution.
```

---

## 9. Downgrade Procedure

Use only if the specific migration has a tested downgrade.

### 9.1 Confirm target revision

```powershell
alembic current
alembic history --verbose
```

### 9.2 Dry run in staging/local clone first

```powershell
alembic downgrade <previous-revision>
```

### 9.3 Verify

```powershell
alembic current
.venv\Scripts\python.exe -m pytest -q tests/integration
```

### 9.4 Production approval

Required:

- [ ] Incident owner approval.
- [ ] Backup exists.
- [ ] Expected data effect documented.
- [ ] Downgrade tested on staging/local clone.

### 9.5 Run downgrade

```powershell
alembic downgrade <previous-revision>
```

### 9.6 Post-downgrade checks

- [ ] App starts.
- [ ] Critical endpoints work.
- [ ] Dashboard works.
- [ ] Data is present.
- [ ] Logs are clean.

---

## 10. Restore Fallback Procedure

Use when downgrade is unsafe or unavailable.

Follow `BACKUP_RESTORE_RUNBOOK.md`.

Restore fallback is required when:

- A table/column was dropped.
- Important data was overwritten.
- Downgrade cannot reconstruct data.
- Migration affected security policies and access is broken.
- Production state is unknown.

---

## 11. RLS / Supabase Policy Migration Notes

Treat RLS/security policy migrations as high risk.

Checklist:

- [ ] Identify affected schemas/tables.
- [ ] Confirm RLS enabled state.
- [ ] Confirm policies for `anon`, `authenticated`, and `service_role`.
- [ ] Check `USING` expressions.
- [ ] Check `WITH CHECK` expressions for writes.
- [ ] Test unauthenticated access denial.
- [ ] Test authenticated allowed path.
- [ ] Test cross-user denial where applicable.
- [ ] Run Supabase Security Advisor after change if available.

Do not claim RLS hardened if policies are only documented and not applied/tested.

---

## 12. Destructive Change Rules

Destructive operations include:

- `DROP TABLE`
- `DROP COLUMN`
- `TRUNCATE`
- broad `DELETE`
- irreversible data rewrite
- enum value removal
- RLS policy removal or broadening
- index removal on hot path

Required controls:

- [ ] Backup before migration.
- [ ] Approval.
- [ ] Staging dry run.
- [ ] Rollback/restore plan.
- [ ] Post-migration verification.

Never run:

```sql
DELETE FROM table_name;
```

without a reviewed `WHERE`, backup, and approval. PostgreSQL `DELETE` without a `WHERE` removes all rows in the table.

---

## 13. Post-Incident Record Template

```markdown
# Migration Incident Record

- Date/time:
- Environment:
- Git SHA:
- Migration revision before:
- Migration revision target:
- Operator:
- Reviewer/approver:
- What failed:
- Detection method:
- User impact:
- Decision: forward fix / downgrade / restore
- Commands run:
- Verification result:
- Data loss:
- Follow-up tasks:
```

---

## 14. What This Branch Does Not Do

This runbook does not:

- create migration files,
- modify Alembic config,
- add downgrade implementations,
- change Supabase policies,
- run database commands,
- add backup automation,
- add production deployment automation.

It is operator guidance only.

---

## 15. Done Criteria for Real Migration Rollback Readiness

A future implementation can mark migration rollback readiness done only when:

- [ ] Runbook exists.
- [ ] Backup/restore drill exists.
- [ ] At least one staging migration dry run has been recorded.
- [ ] Destructive migration approval process is documented.
- [ ] Downgrade/restore decision tree is tested.
- [ ] Operators know how to verify post-rollback state.

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
