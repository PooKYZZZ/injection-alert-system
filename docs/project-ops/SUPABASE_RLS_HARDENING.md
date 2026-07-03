# Supabase and Row Level Security Operational Hardening Notes

**Last updated:** 2026-07-03  
**Audience:** developers, database operator, security reviewer  
**Scope:** Supabase/PostgreSQL operational hardening for CyberTrace  
**Status:** notes/checklist only; this file does not apply Supabase settings, SQL policies, or migrations

---

## 1. Purpose

This document explains how CyberTrace should be hardened when using Supabase/PostgreSQL.

It focuses on operational truth:

```text
Document what must be checked.
Do not claim settings are applied unless verified in the actual Supabase project.
```

Supabase RLS is powerful, but dangerous if misunderstood. RLS documentation says it should be enabled on exposed schemas/tables, and policies act like implicit filters on table access.

---

## 2. Current Project Truth

Expected current state:

- Supabase is a production target, but not all Supabase operational hardening is automated in repo.
- RLS hardening export is marked not started unless another branch changed it.
- This branch is documentation only.
- No SQL policy is created by this file.
- No Supabase dashboard setting is changed by this file.
- No migration is created by this file.

---

## 3. Hardening Areas

| Area | Why It Matters | Current Action |
|---|---|---|
| Project ownership | Avoid single-account lockout. | Document owner/MFA checklist. |
| MFA | Protect Supabase account access. | Enable in Supabase account. |
| Environment separation | Prevent staging/dev from touching prod. | Use separate projects/branches. |
| SSL | Protect DB traffic. | Enforce where supported. |
| Network restrictions | Reduce exposed DB attack surface. | Configure where plan supports it. |
| RLS | Protect exposed schemas/tables. | Enable and test policies. |
| Service-role key | Full bypass risk if leaked. | Server-only, never browser/logs. |
| Advisors | Catch common security/performance mistakes. | Run Security and Performance Advisors. |
| Backups/PITR | Recovery after failures. | Configure per plan and test restore. |
| Migrations | Prevent manual prod drift. | Use reviewed migration flow. |

---

## 4. Supabase Project Checklist

- [ ] Production project is separate from development.
- [ ] Staging project or branch exists for migration testing.
- [ ] At least two owners/admins or break-glass access path exist.
- [ ] MFA enabled on owner/admin accounts.
- [ ] Billing/plan supports required backup/PITR/network features.
- [ ] Project API keys are stored securely.
- [ ] Service-role key is not used in browser/frontend.
- [ ] Service-role key is not logged.
- [ ] Old/unused keys are rotated.
- [ ] Project URL/key values are not committed to Git.

---

## 5. Database Connection Checklist

- [ ] Use SSL/TLS where required.
- [ ] Use environment variables for connection strings.
- [ ] Do not paste DB URLs into logs/issues/PRs.
- [ ] Do not print connection strings in startup errors.
- [ ] Use least-privilege DB credentials where possible.
- [ ] Use connection pooling/Supavisor appropriately for deployment.
- [ ] Document pool limits and timeout behavior.

---

## 6. RLS Core Rules

### 6.1 Enable RLS on exposed schemas

Supabase documentation says RLS must always be enabled on tables stored in exposed schemas, with `public` being the default exposed schema.

Checklist:

- [ ] Identify exposed schemas.
- [ ] List tables in exposed schemas.
- [ ] Confirm RLS enabled for each exposed table.
- [ ] Confirm table permissions are scoped to required roles.
- [ ] Confirm no sensitive table is accidentally exposed to `anon`.

Example SQL for inspection:

```sql
select schemaname, tablename, rowsecurity
from pg_tables
where schemaname in ('public')
order by schemaname, tablename;
```

### 6.2 Default-deny behavior

PostgreSQL RLS generally denies access when RLS is enabled and no applicable policy permits the operation. Treat this as a safety property, but test it.

Checklist:

- [ ] Unauthenticated `anon` reads fail where they should.
- [ ] Authenticated reads succeed only for allowed records.
- [ ] Inserts require `WITH CHECK` rules where appropriate.
- [ ] Updates check both existing row access and new row validity.
- [ ] Deletes are restricted or absent.

---

## 7. Policy Review Checklist

For every table exposed through Supabase APIs:

```text
Table:
Schema:
RLS enabled: yes/no
Policies:
Roles affected: anon/authenticated/service_role/custom
Read allowed:
Insert allowed:
Update allowed:
Delete allowed:
Tested as anon:
Tested as authenticated user A:
Tested as authenticated user B:
Tested cross-user denial:
```

Policy questions:

- [ ] Does policy explicitly check authenticated user where needed?
- [ ] Does `auth.uid()` returning `null` deny unauthenticated access safely?
- [ ] Is `TO anon` intentional?
- [ ] Is `USING (true)` intentional?
- [ ] Is `WITH CHECK` present for inserts/updates where ownership matters?
- [ ] Are service-role operations server-only?
- [ ] Are policies indexed enough for performance?

---

## 8. Service-Role Key Rules

The service-role key is powerful. Treat leakage as a security incident.

Never:

- expose service-role key in frontend,
- commit service-role key,
- print service-role key,
- paste service-role key into ChatGPT/Codex logs,
- store service-role key in screenshots,
- use service-role key for normal browser user operations.

Allowed only:

- backend server environment,
- trusted admin script,
- migration/ops flow,
- tightly scoped CI secret if needed.

If leaked:

1. Rotate the key.
2. Invalidate exposed environment values.
3. Search logs/PRs/history for exposure.
4. Document incident.

---

## 9. Security Advisor / Performance Advisor Checklist

Supabase provides database advisors that can identify common security and performance issues.

Run before production claim:

- [ ] Security Advisor reviewed.
- [ ] Performance Advisor reviewed.
- [ ] Missing RLS warnings addressed or documented.
- [ ] Exposed sensitive columns addressed or documented.
- [ ] Permissive policies reviewed.
- [ ] Missing indexes on policy columns reviewed.
- [ ] Slow queries reviewed.

Record:

```markdown
# Supabase Advisor Review

- Date:
- Project:
- Reviewer:
- Security Advisor findings:
- Performance Advisor findings:
- Accepted risks:
- Fixes applied:
- Follow-up tasks:
```

---

## 10. Environment Separation

Minimum environments:

| Environment | Purpose | Data |
|---|---|---|
| Local | developer testing | fake/local |
| Staging/demo | rehearsal and proof | sanitized/demo |
| Production | client/live use | real only after approval |

Rules:

- [ ] Local `.env` must not point to production by accident.
- [ ] Staging and production use different DB projects.
- [ ] CI does not use production DB for tests.
- [ ] Migration dry runs happen before production.
- [ ] Demo screenshots avoid real sensitive data.

---

## 11. Migration and RLS Change Procedure

RLS changes are security-sensitive.

Before applying RLS migration:

- [ ] Backup exists.
- [ ] Policy reviewed.
- [ ] Staging test passes.
- [ ] Cross-user access tests pass.
- [ ] Supabase advisors reviewed.
- [ ] Rollback/restore plan exists.

After applying:

- [ ] Anonymous denial tested.
- [ ] Authenticated allowed path tested.
- [ ] Unauthorized authenticated path denied.
- [ ] Service-role backend flow still works.
- [ ] Dashboard/BFF still works.

---

## 12. Tables to Review for CyberTrace

Adapt to current schema. Expected high-value tables include:

- `traffic_logs`
- analyst feedback table if separate
- user/account table if implemented later
- session/audit/login tables if implemented later
- model registry metadata table if ever persisted

For each:

- Is it exposed to browser/Supabase API?
- Should browser access it directly? Usually no for this architecture.
- Should only backend service access it?
- Does RLS matter if backend uses service role only?
- Are policies still needed for defense-in-depth?

Current architecture preference:

```text
Browser -> Next.js BFF -> FastAPI -> database
```

Do not let browser directly query sensitive CyberTrace tables unless explicitly designed and protected.

---

## 13. Backup/PITR Checklist

- [ ] Confirm Supabase plan backup features.
- [ ] Confirm PITR availability and retention window.
- [ ] Confirm restore process and downtime behavior.
- [ ] Test restore to non-production target.
- [ ] Document RPO/RTO.
- [ ] Document who can initiate restore.

Use `BACKUP_RESTORE_RUNBOOK.md` for detailed process.

---

## 14. Production Claim Rules

Do not claim Supabase/RLS is production-hardened unless:

- [ ] Supabase production checklist is reviewed.
- [ ] RLS enabled and tested where applicable.
- [ ] Security Advisor reviewed.
- [ ] Performance Advisor reviewed.
- [ ] Backups/PITR selected and restore-tested.
- [ ] Service-role key is server-only.
- [ ] Environment separation is proven.
- [ ] Logs do not leak DB URLs/keys.

---

## 15. What This Branch Does Not Do

This documentation does not:

- enable RLS,
- create policies,
- alter tables,
- run migrations,
- configure Supabase dashboard settings,
- rotate keys,
- enable PITR,
- restrict network access,
- change backend/frontend code.

All of those require separate implementation or operations work.

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
