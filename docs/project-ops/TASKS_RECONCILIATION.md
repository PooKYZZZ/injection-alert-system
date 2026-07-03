# TASKS.md Reconciliation

**Last updated:** 2026-07-03  
**Audience:** project maintainers, Codex/AI-agent operators, reviewers  
**Scope:** reconciling stale task lists with maintained project truth  
**Status:** documentation-only guidance; update `TASKS.md` only if it exists and is tracked

---

## 1. Purpose

This document prevents stale task lists from confusing future work.

The project has moved toward maintained truth sources such as:

- `PD2_PRIORITY_TRACKER.md`
- `docs/project-ops/STATUS.md`
- `docs/project-ops/LIVING_CHECKLIST.md`
- specific runbooks under `docs/project-ops/`

If an older `TASKS.md` exists, it should not be treated as the primary roadmap unless it has been reconciled.

---

## 2. Rule of Truth

Use this priority order when files disagree:

1. Current code and tests.
2. Latest merged PR evidence.
3. `docs/project-ops/STATUS.md`.
4. `docs/project-ops/LIVING_CHECKLIST.md`.
5. `PD2_PRIORITY_TRACKER.md`.
6. Specific runbooks/proof reports.
7. Historical docs such as old `TASKS.md`.

If docs disagree with code, code/tests win and docs must be updated.

---

## 3. Recommended Banner for Stale TASKS.md

If `TASKS.md` exists and is tracked, add this at the top instead of deleting the file immediately:

```markdown
> [!WARNING]
> This file is historical and may be stale.
> Current task truth lives in `PD2_PRIORITY_TRACKER.md`, `docs/project-ops/STATUS.md`, and `docs/project-ops/LIVING_CHECKLIST.md`.
> Do not start work from this file unless the item has been reconciled against current code and tracker docs.
```

Why not delete immediately?

- It may contain historical context.
- It may help explain old decisions.
- Deleting can hide why something was deferred.
- A warning banner is safer and easier to review.

---

## 4. Reconciliation Process

For every item in `TASKS.md`:

1. Copy the task title into this table or a working note.
2. Search current repo for evidence.
3. Mark one of:
   - Done
   - Partial
   - Not started
   - Deferred
   - Obsolete
   - Moved to tracker
4. Link the maintained source of truth.
5. Update `PD2_PRIORITY_TRACKER.md` only if the task is still relevant and missing.
6. Do not mark done without code/test/doc evidence.

---

## 5. Reconciliation Table Template

```markdown
| TASKS.md Item | Current Status | Evidence | Action |
|---|---|---|---|
| Example old task | Done/Partial/Not started/Deferred/Obsolete | file/test/PR/doc path | moved to tracker / deleted / bannered / kept |
```

---

## 6. Current Known Tracker Truth

As of this documentation pack, expected tracker truth is:

| Area | Expected Status |
|---|---|
| WAF local proof | Done |
| Demo-target WAF proof | Done |
| Bounded inference queue | Done |
| Queue health visibility | Done |
| Structured JSON logs and request/trace/transaction correlation | Done |
| Final demo smoke suite | Done if merged after smoke-suite branch |
| API abuse/resource smoke tests | Done or stronger partial if smoke-suite branch merged |
| Real-time dashboard alerts | Not started |
| Email notifications | Not started |
| Real accounts | Not started |
| RBAC | Not started |
| 2FA/MFA | Not started |
| Runtime enforcement state | Partial metadata only |
| Production edge checklist | This docs branch creates it |
| Backup/restore runbook | This docs branch creates it |
| Migration rollback runbook | This docs branch creates it |
| Retention policy | This docs branch creates it |
| Supabase/RLS hardening notes | This docs branch creates it |
| Wazuh export-only integration | Not started |
| Full SIEM/Kubernetes/Terraform/Kafka/Celery/Elasticsearch | Deferred |

Update the table if current repo truth changes.

---

## 7. Stale Claim Patterns to Search

Run:

```powershell
rg -n "production-ready|prod ready|implemented|done|TODO|TASKS|473 passed|476 passed|488 passed|489 passed|Wazuh|SIEM|Kubernetes|Terraform|Celery|Kafka|RBAC|2FA|email|real-time|SSE|retention|backup|restore|rollback" .
```

Review hits in:

```text
docs/
PD2_PRIORITY_TRACKER.md
TASKS.md
README.md
AGENTS.md if tracked
```

Do not blindly replace historical evidence reports. Add clarification when needed.

---

## 8. AI-Agent Instructions for Task Reconciliation

When using Codex/AI agent:

```text
Inspect before editing.
Do not delete historical files without approval.
Do not mark planned features as implemented.
Do not change code in a docs reconciliation branch.
Do not create new tasks from imagination.
Prefer a banner and cross-link over destructive cleanup.
```

The agent must report:

```text
Files inspected:
Stale claims found:
Claims updated:
Claims preserved as history:
Files changed:
Remaining uncertainty:
```

---

## 9. What Not to Reconcile Away

Keep historical proof reports intact when they are explicitly dated and true for that date.

Examples:

- old ModSecurity proof reports,
- dated screenshots,
- test-count history inside PR bodies,
- branch-specific audit notes,
- historical implementation plans.

Do not rewrite history. Add current-status notes where needed.

---

## 10. When to Delete TASKS.md

Deletion is allowed only if all are true:

- [ ] The file is tracked.
- [ ] All useful tasks are migrated or declared obsolete.
- [ ] Maintainer approves deletion.
- [ ] `PD2_PRIORITY_TRACKER.md` fully replaces it.
- [ ] No docs/scripts link to it.
- [ ] PR clearly states why it was deleted.

Default recommendation: **do not delete; add stale banner**.

---

## 11. Reconciliation Done Criteria

- [ ] `TASKS.md` exists check completed.
- [ ] If tracked, stale banner added.
- [ ] Current source-of-truth files are linked.
- [ ] No planned feature is marked implemented without evidence.
- [ ] Historical proof is preserved.
- [ ] Tracker/status/checklist agree.
- [ ] `git diff --check` passes.

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
