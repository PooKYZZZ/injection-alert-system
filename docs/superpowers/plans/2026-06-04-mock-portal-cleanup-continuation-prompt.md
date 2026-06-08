# Mock Portal Cleanup Continuation Prompt

Use this prompt to continue the cleanup after the interrupted partial execution.

```text
You are Codex, acting as a senior software engineer in the local workspace:

G:\AI\land-records-portal

You are continuing an interrupted implementation of:

docs/superpowers/plans/2026-06-04-mock-portal-cleanup.md

Do not restart from scratch. First verify what has already changed, repair any broken partial edits, then resume the plan from the correct task.

###
CURRENT KNOWN STATE
###

A previous worker started Task 1 and Task 2.

Known landed changes:

- package.json was modified.
- package-lock.json was modified by npm install.
- tsconfig.json target was changed to ES2022.
- node_modules exists.
- lib/prisma.ts exists.
- Prisma imports were updated in:
  - app/comments/page.tsx
  - app/login/submit/route.ts
  - app/records/[recordNo]/request-copy/submit/route.ts
- npm run db:generate passed.
- npx prisma validate passed.

Known problems:

- npm run typecheck currently fails because app/login/route.ts has a syntax error around lines 207-241.
- That file appears to contain a duplicated leftover raw HTML/script fragment after the GET handler closes.
- eslint.config.mjs is missing.
- .eslintrc.json still exists.
- This folder is not a Git repository, so git status/diff commands are unavailable.

###
PRIMARY OBJECTIVE
###

Continue the cleanup plan properly, but first do a comprehensive check of all modified files and fix any partial/broken edits from the previous worker.

The final direction remains:

- install/build/typecheck/lint baseline;
- one Prisma client boundary;
- Prisma/SQLite for submitted state;
- native HTML forms;
- explicit route handlers;
- no middleware magic for normal form submits;
- neutral public wording;
- WAF docs/scripts remain local-lab-only and anomaly-scoring oriented.

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
- extra packages beyond what the plan already requires.

Do not change WAF-relevant form field names or public route URLs unless the plan explicitly calls for route normalization.

###
READ FIRST
###

Read these before editing:

1. docs/superpowers/plans/2026-06-04-mock-portal-cleanup.md
2. docs/CODEBASE_AUDIT_VERIFIED.md
3. package.json
4. tsconfig.json
5. prisma/schema.prisma
6. middleware.ts
7. lib/prisma.ts
8. app/login/route.ts
9. app/comments/page.tsx
10. app/login/submit/route.ts
11. app/records/[recordNo]/request-copy/submit/route.ts
12. .eslintrc.json, if it exists
13. eslint.config.mjs, if it exists

Do not read the entire codebase repeatedly. Inspect only files needed for the current task after this initial recovery audit.

###
PHASE 0 - RECOVERY AUDIT OF MODIFIED FILES
###

Before continuing the plan, perform a comprehensive check of the files already modified by the previous worker.

Check:

- package.json
- package-lock.json
- tsconfig.json
- .eslintrc.json
- eslint.config.mjs, if present
- lib/prisma.ts
- app/comments/page.tsx
- app/login/submit/route.ts
- app/records/[recordNo]/request-copy/submit/route.ts
- app/login/route.ts

For each file, verify:

1. It parses.
2. It matches the cleanup plan.
3. It does not introduce forbidden features.
4. Imports resolve.
5. It does not move persistence backward to cookies.
6. It does not expose password or personal data unnecessarily.
7. It keeps native form behavior.

Run these checks after inspecting:

npm run db:generate
npx prisma validate
npm run typecheck

Expected initial result:

- db:generate should pass.
- prisma validate should pass.
- typecheck may fail on app/login/route.ts.

###
PHASE 1 - FIX PARTIAL/BROKEN EDITS
###

First repair the known broken file:

app/login/route.ts

The expected minimal repair is:

- Keep the GET handler returning the raw HTML login page for now.
- Remove the stray duplicated script/html block after the GET handler.
- Keep or remove the base POST handler only according to the current plan stage:
  - If still in Task 2, leave route behavior mostly unchanged except syntax repair.
  - Do not prematurely complete Task 6 unless you intentionally move to that task later.

After repairing app/login/route.ts, run:

npm run typecheck
npm run build

If failures remain, classify them:

- caused by partial previous edits;
- expected blocker for the next planned task;
- unrelated pre-existing issue.

Fix only the first category immediately.

###
PHASE 2 - COMPLETE TASK 1 AND TASK 2 BASELINE
###

After recovery:

Task 1 should be considered complete only if:

- npm install has succeeded;
- package.json contains only needed dependencies from the plan;
- TypeScript target is modern;
- Prisma local CLI is pinned;
- db:generate passes;
- prisma validate passes.

Task 2 should be considered complete only if:

- lib/prisma.ts exists and is correct;
- all Prisma-using files import from @/lib/prisma;
- lib/db.ts is not pretending to export Prisma;
- npm run typecheck passes or only fails for an explicitly documented next-task blocker.

If eslint.config.mjs is missing, decide conservatively:

- If npm run lint works with .eslintrc.json, leave it alone.
- If npm run lint fails because config is missing or incompatible, add the smallest compatible config.
- Do not churn ESLint config beyond making the project lint command meaningful.

Run:

npm run typecheck
npm run build
npm run lint

Document exact status.

###
PHASE 3 - RESUME THE PLAN FROM THE NEXT INCOMPLETE TASK
###

After Task 1 and Task 2 are stable, resume:

Task 3: Make Comments Fully Prisma-Backed

Follow the plan exactly:

- app/comments/submit/route.ts should validate server-side.
- comments should write to Prisma Comment.
- app/page.tsx should read comments from Prisma instead of citizen_comments cookie.
- Do not store comments in cookies.
- Keep native form submission.

Then continue task-by-task only if each task is stable.

Do not skip ahead to wording cleanup, Docker, or raw HTML conversion until the earlier persistence and route tasks are done.

###
QUALITY RULES
###

Use boring, stable, easy-to-review code.

Prefer:

- explicit imports;
- explicit form actions;
- explicit route handlers;
- one Prisma client boundary;
- Zod or one shared server validation boundary;
- short redirects with reference IDs only;
- small patches with verification.

Avoid:

- middleware for ordinary form routing;
- duplicate POST handlers for the same logical action;
- storing names, emails, messages, or request details in client-readable cookies;
- query strings containing email, subject, password, or long user content;
- public pages saying WAF, CyberTrace, ModSecurity, OWASP CRS, SQLi, XSS, LFI, attack, payload, or penetration testing;
- broad refactors or speculative abstractions.

###
STOP AND ASK BEFORE DOING THESE
###

Ask before:

- upgrading Next.js beyond what is required to install;
- changing public URLs outside the plan;
- deleting large files or major route groups;
- replacing the architecture;
- adding Docker ModSecurity/CRS services;
- adding real auth/admin/payment/upload/email;
- introducing a new library beyond Prisma/Zod/tsx/clsx/tailwind-merge/tooling already in plan.

###
VERIFICATION COMMANDS
###

Use task-level verification from the plan. At minimum after recovery, run:

npm run db:generate
npx prisma validate
npm run typecheck
npm run build
npm run lint

After persistence tasks, also run:

npm run db:push
npm run db:seed

When enough of the app is stable, smoke-test:

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

###
FINAL RESPONSE FORMAT
###

Report:

1. Where the previous worker left off.
2. What broken/partial edits you found.
3. What you fixed.
4. Which plan tasks are now complete.
5. Files changed.
6. Verification commands and pass/fail status.
7. Remaining blockers.
8. Confirmation that no forbidden features were added.
9. Recommended next task.

If blocked, report:

1. Current task.
2. Exact command/error.
3. Files already changed.
4. Why progress cannot continue safely.
5. Smallest decision needed from the user.

###
CRITICAL REMINDER
###

Do not restart from scratch.
First repair the interrupted Task 1/Task 2 state.
Then resume docs/superpowers/plans/2026-06-04-mock-portal-cleanup.md in order.
Keep native forms.
Use Prisma/SQLite for submitted state.
Do not overengineer.
```

