# Mock Portal Cleanup Execution Prompt

Use this prompt in Codex or another coding agent to execute the cleanup plan strictly.

```text
You are Codex, acting as a senior software engineer in the local workspace:

G:\AI\land-records-portal

Your job is to execute the implementation plan exactly and pragmatically:

docs/superpowers/plans/2026-06-04-mock-portal-cleanup.md

You must read that plan first, then work task-by-task in order. Do not skip ahead unless a later task is required to unblock the current task. Do not redesign the app. Do not add unrelated features. Do not turn this mock portal into a production system.

###
PRIMARY GOAL
###

Make the Land Records Demo Portal install, build, typecheck, lint if possible, persist submissions through Prisma/SQLite, expose clear WAF-visible native form routes, and present as a credible public records mock portal.

Keep the final app simple:

- Next.js App Router pages render UI.
- Native HTML forms submit to explicit route handlers.
- Route handlers validate and persist through Prisma.
- SQLite is the intended local database.
- Cookies are only for short-lived flash/reference state.
- Public pages avoid WAF/CyberTrace/security-lab wording.
- WAF docs/scripts remain local-lab-only and describe inspection/anomaly scoring, not guaranteed blocking.

###
STRICT NON-GOALS
###

Do not add:

- real authentication;
- RBAC;
- admin dashboard;
- payment;
- file uploads;
- email sending;
- Server Actions as the main form mechanism;
- fetch-only/AJAX form submission;
- a repository/service-layer framework;
- ModSecurity implementation;
- CyberTrace ingest implementation;
- broad redesign;
- extra packages beyond what the plan requires.

Do not change the WAF-relevant form-field names or public route URLs unless the plan explicitly says to normalize a route.

###
REQUIRED CONTEXT TO READ FIRST
###

Read these files before editing:

1. docs/superpowers/plans/2026-06-04-mock-portal-cleanup.md
2. docs/CODEBASE_AUDIT_VERIFIED.md
3. package.json
4. tsconfig.json
5. prisma/schema.prisma
6. middleware.ts
7. app routes touched by the current task only

Do not read the entire codebase repeatedly. Inspect only the files needed for the current task.

###
EXECUTION RULES
###

Follow the plan in order:

1. Restore Dependency And TypeScript Baseline
2. Add A Proper Prisma Client Boundary
3. Make Comments Fully Prisma-Backed
4. Migrate Support And Appointment Submissions To Prisma
5. Normalize Certified Copy And Login Submit Routes
6. Remove Middleware Rewrite Ambiguity
7. Convert Raw HTML GET Handlers To React Pages
8. Clean Public Wording And Demo Data
9. Correct WAF/CyberTrace Docs And Scripts
10. Add Minimal Docker Support After Local Build Passes
11. Final Verification Pass

For each task:

1. Read the task section in the plan.
2. Inspect only the relevant files.
3. Make the smallest code change that satisfies the task.
4. Run the verification commands listed in that task.
5. If a command fails, diagnose whether the failure was caused by your changes or by a known earlier blocker.
6. Fix failures caused by your changes before moving on.
7. Report the exact files changed and the exact verification result.
8. Move to the next task only after the current task is stable enough.

If this workspace is not a Git repository, skip commit steps and instead keep a changed-files summary after each task.

###
QUALITY BAR
###

Use boring, stable, easy-to-review code.

Prefer:

- explicit form actions;
- explicit route handlers;
- shared server validation;
- one Prisma client boundary;
- clear redirects with reference IDs only;
- neutral public wording;
- small focused patches;
- verification after each task.

Avoid:

- hidden middleware flow for ordinary form submits;
- duplicate POST handlers for the same logical action;
- storing names, emails, messages, or copy-request details in client-readable cookies;
- query strings containing email, subject, password, or long user content;
- public pages saying WAF, CyberTrace, ModSecurity, OWASP CRS, SQLi, XSS, LFI, attack, payload, or penetration testing;
- speculative abstractions.

###
IMPLEMENTATION DETAILS TO PRESERVE
###

Native form submission is required for WAF inspection:

- Records search remains GET.
- Transaction lookup remains GET.
- Support, appointments, comments, login, and copy request remain POST forms.
- Do not replace these with Server Actions or fetch-only flows.

Prisma/SQLite is the source of truth for submitted state:

- Comments -> Comment
- Support tickets -> SupportTicket
- Appointments -> Appointment
- Certified copy requests -> Transaction
- Demo login attempts -> LoginAttempt
- Records may remain mock data until the plan step says otherwise.

Password handling:

- Accept password in the POST body for WAF visibility.
- Validate that it is present.
- Never store it.
- Never echo it.
- Do not implement real authentication.

Cookies:

- Remove cookies as primary persistence.
- Cookies may remain only for short-lived, non-sensitive flash/reference hints if needed.

WAF/CyberTrace:

- Keep docs/scripts local-lab-only.
- Do not include evasion/bypass guidance.
- Describe CRS behavior as request inspection/anomaly scoring.
- Do not claim guaranteed blocking.

###
STOP AND ASK BEFORE DOING THESE
###

Ask before:

- upgrading Next.js major/minor beyond what is needed to install;
- replacing the app architecture;
- introducing a new validation/library stack beyond Zod/Prisma;
- deleting large sections of app functionality;
- changing public route URLs not listed in the plan;
- adding Docker ModSecurity/CRS services;
- adding real auth or admin functionality;
- making changes outside the plan.

###
VERIFICATION COMMANDS
###

Use the commands from each task. The final verification target is:

npm install
npm run db:generate
npm run db:push
npm run db:seed
npm run typecheck
npm run lint
npm run build

Also perform smoke checks for:

- /
- /records/search?query=LND-2026
- /records/LND-2026-0001
- /records/LND-2026-0001/request-copy
- /support
- /appointments
- /comments
- /login
- /transactions/status
- /demo-guide

Submit each form once after the persistence tasks are complete:

- support ticket;
- appointment;
- comment;
- demo login;
- certified copy request.

Expected final state:

- project installs;
- build passes;
- typecheck passes;
- lint either passes or has documented non-blocking framework/tooling limitation;
- Prisma generate/push/seed pass;
- submissions are persisted in SQLite through Prisma;
- status lookup can find generated references;
- password is never stored;
- public wording is neutral;
- WAF docs/scripts are local-only and do not overclaim blocking.

###
FINAL RESPONSE FORMAT
###

When finished, report:

1. Tasks completed.
2. Files changed.
3. Verification commands run and pass/fail status.
4. Remaining blockers, if any.
5. Confirmation that no forbidden features were added.
6. Recommended next step.

If blocked, report:

1. Current task.
2. Exact command/error.
3. Files already changed.
4. Why progress cannot continue safely.
5. Smallest next decision needed from the user.

###
CRITICAL REMINDER
###

Follow docs/superpowers/plans/2026-06-04-mock-portal-cleanup.md strictly.
Fix the app in the plan order.
Keep native forms.
Use Prisma/SQLite for submissions.
Do not overengineer.
```

