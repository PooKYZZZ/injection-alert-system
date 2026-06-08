# Codebase Audit Verified - Land Records Demo Portal

Generated from local inspection of `G:\AI\land-records-portal`. This audit is documentation-only: no source code fixes, refactors, route changes, dependency changes, or behavior changes were applied.

## 1. Executive Verdict

**Needs Cleanup.** The project has the right broad shape for a WAF-visible Next.js mock target: App Router routes, native HTML form submissions, explicit route handlers, local demo docs, and a Prisma schema for the intended SQLite future. It is not ready as-is because dependency installation fails, build/lint cannot run, TypeScript fails on the ES5 target, Prisma usage is half-implemented without required dependencies in `package.json`, cookie-backed persistence still stores main submission data, middleware rewrites make important POST paths ambiguous, and public UI still exposes WAF/CyberTrace/security-lab wording.

## 2. Verification Commands

| Command | Result | Evidence/output summary | Notes |
|---|---:|---|---|
| `Get-Location` | Pass | `G:\AI\land-records-portal` | Verified project root. |
| `node -v` | Pass | `v22.22.2` | Runtime is newer than README's Node 18/20 guidance. |
| `npm -v` | Pass | `10.9.7` | npm available. |
| `git status --short` | Not available | `fatal: not a git repository` | Git diff verification unavailable in this folder. |
| `Test-Path node_modules` | Pass | `False` before install attempt | Dependencies were not installed. |
| `npm install` | Fail | `ERESOLVE could not resolve`; `eslint-config-next@16.2.7` requires `eslint >=9.0.0`, root uses `eslint ^8.57.0` | Real blocker for install/build/lint. |
| `npm run build` | Fail | `'next' is not recognized` | Expected after failed install; `next` binary unavailable. |
| `npm run lint` | Fail | `'next' is not recognized` | Expected after failed install. Also `next lint` is legacy in modern Next. |
| `npx tsc --noEmit` | Fail | `TS5107: Option 'target=ES5' is deprecated` at `tsconfig.json:3` | Cleanup blocker for type verification. |
| `npx prisma validate` | Fail | `npx` fetched `prisma@7.8.0`; schema failed because Prisma 7 no longer accepts datasource `url` in schema | Also proves `prisma` is missing locally. |
| `npx prisma generate` | Fail | Same Prisma 7 datasource `url` error | Prisma cannot generate with fetched CLI. |
| `rg --files ...` | Pass | Listed app, lib, docs, scripts, Prisma, config files | Used for file tree and scope inventory. |
| `rg -n "<form|action=|method=|onSubmit|fetch"` | Pass | Found native forms in app pages/raw HTML and fetch usage only in scripts | Used for form audit. |
| `rg -n "cookies|prisma|JSON.parse|DATABASE_URL"` | Pass | Found mixed cookie and Prisma usage | Used for persistence audit. |
| `rg -n "WAF|ModSecurity|OWASP|CyberTrace|SQLi|XSS|LFI|Su Yao|Bruce Wayne|Tony Stark"` | Pass | Found public and developer-facing terminology/data flags | Used for wording audit. |

## 3. Actual Stack

| Layer | Expected | Actual | Evidence | Verdict |
|---|---|---|---|---|
| Framework | Next.js App Router | Next `15.1.0` with `app/` routes | `package.json:14`; `app/*/page.tsx`; `app/*/route.ts` | Verified |
| React | React 19 | `react` and `react-dom` `19.0.0` | `package.json:15-16` | Verified |
| TypeScript | Strict TS | `typescript ^5`, `strict: true`, `target: es5` | `package.json:27`; `tsconfig.json:3-9` | Partial, target needs cleanup |
| Tailwind | Tailwind CSS v4 | `tailwindcss ^4.0.0`, `@tailwindcss/postcss ^4.0.0` | `package.json:19,26`; `postcss.config.mjs` | Verified |
| Icons | Lucide | `lucide-react ^0.468.0` and imports throughout pages | `package.json:12`; `app/layout.tsx:4` | Verified |
| Motion | Present or unused | `motion ^11.15.0`, `transpilePackages: ['motion']`; little/no direct usage found | `package.json:13`; `next.config.ts:23` | Questionable |
| Forms | Native HTML forms | Forms use `method="get"` / `method="post"` and explicit actions | `app/records/search/page.tsx:72-75`; `app/support/page.tsx:138-142` | Verified |
| Persistence | Prisma + SQLite intended | Prisma schema and DB file exist, but main flows still use cookies | `prisma/schema.prisma`; `app/support/submit/route.ts:30-64` | Partial |
| Prisma deps | `@prisma/client`, `prisma` | Missing from `package.json` | `package.json` dependency lists; imports in `prisma/seed.ts:1` and app routes | Broken |
| Zod | Present if used | Code imports `zod`, but package is missing | `app/login/submit/route.ts:3`; `app/records/[recordNo]/request-copy/submit/route.ts:3`; absent in `package.json` | Broken |
| Scripts runtime | `tsx` if scripts use TS directly | README says `npx tsx`, but `tsx` is missing | `README.md:80-89`; absent in `package.json` | Missing |
| Docker | Local container support | `docker-compose.yml` references missing `Dockerfile` | `docker-compose.yml:6-8`; no Dockerfile in file tree | Not runnable as-is |
| Lockfile | npm lock consistency | `package-lock.json` exists and matches top-level dependencies, but install fails due peer conflict | `package-lock.json:11-26`; `npm install` output | Risky |

## 4. Top Findings

1. **Severity: Critical - Install/build blocker**  
   **Evidence:** `npm install` fails with `eslint-config-next@16.2.7` requiring `eslint >=9.0.0` while `package.json:23-24` pins ESLint 8 and `eslint-config-next ^16.2.7`.  
   **Why it matters:** The project cannot be reliably installed, built, or linted from a clean checkout.  
   **Fix recommendation:** Align ESLint and `eslint-config-next` versions; prefer a Next-compatible ESLint 9 setup or pin Next ESLint config to the matching generation.  
   **Fix now or later:** Now.

2. **Severity: Critical - Prisma/Zod code imports missing packages**  
   **Evidence:** `prisma/seed.ts:1` imports `@prisma/client`; `app/login/submit/route.ts:3` and `app/records/[recordNo]/request-copy/submit/route.ts:3` import `zod`; neither package appears in `package.json`.  
   **Why it matters:** Prisma-backed routes cannot compile after dependency install is corrected unless packages are added.  
   **Fix recommendation:** Add `@prisma/client`, `prisma`, `zod`, and `tsx` if the README/script workflow remains.  
   **Fix now or later:** Now.

3. **Severity: High - TypeScript target blocks verification**  
   **Evidence:** `npx tsc --noEmit` fails with `TS5107` at `tsconfig.json:3`; `target` is `es5`.  
   **Why it matters:** Type checking cannot pass, and ES5 is not a sensible target for this Next/React stack.  
   **Fix recommendation:** Move to a modern target such as `ES2020` or `ES2022`.  
   **Fix now or later:** Now.

4. **Severity: High - Main submission state is still cookie-backed**  
   **Evidence:** `app/support/submit/route.ts:30-64`, `app/appointments/submit/route.ts:31-64`, `app/records/[recordNo]/request-copy/route.ts:344-377`, `app/comments/submit/route.ts:12-34`, and `app/login/route.ts:217`.  
   **Why it matters:** Client-readable cookies store user names, emails, messages, requests, and login usernames; this is brittle and easy to tamper with.  
   **Fix recommendation:** Move submissions to Prisma/SQLite; keep cookies only for short-lived success/reference state.  
   **Fix now or later:** Now for WAF integration readiness.

5. **Severity: High - Middleware rewrites obscure POST destinations**  
   **Evidence:** `middleware.ts:9-19` rewrites `POST /login` to `/login/submit` and `POST /records/[recordNo]/request-copy` to `/records/[recordNo]/request-copy/submit`; base route handlers also define POST handlers.  
   **Why it matters:** WAF logs, docs, browser-visible URLs, and app handlers disagree about where submission logic lives.  
   **Fix recommendation:** Prefer explicit submit routes in form actions or remove duplicate base POST handlers; keep external WAF paths unambiguous.  
   **Fix now or later:** Now.

6. **Severity: High - Raw HTML route handlers**  
   **Evidence:** `app/login/route.ts:5` returns a raw HTML login page; `app/records/[recordNo]/request-copy/route.ts:13` returns a raw HTML copy request page.  
   **Why it matters:** Raw HTML bypasses normal React/layout conventions, duplicates validation scripts, and uses external CDN Tailwind.  
   **Fix recommendation:** Convert GET UI to `page.tsx` and keep route handlers for POST only.  
   **Fix now or later:** Later, after install/persistence cleanup.

7. **Severity: Medium - Public WAF/security wording leaks**  
   **Evidence:** `app/layout.tsx:69,94`; `components/SiteHeader.tsx:28`; `components/SiteFooter.tsx:28-35`; `app/records/[recordNo]/page.tsx:191`; `app/success/page.tsx:39,48`.  
   **Why it matters:** Public pages do not read like a boring public records portal.  
   **Fix recommendation:** Replace public labels with neutral registry wording; keep security terms in docs or hidden demo guide only.  
   **Fix now or later:** Now before demos.

8. **Severity: Medium - Fake/lore data undermines professionalism**  
   **Evidence:** `lib/db.ts:15-45`; `app/page.tsx:27-28`; `app/support/page.tsx:192`; `app/transactions/status/page.tsx:66,75,83`.  
   **Why it matters:** Names like Su Yao, Sarah Connor, Bruce Wayne, Tony Stark, and Delta Mutant data make the target feel unserious.  
   **Fix recommendation:** Replace with neutral demo owners, branches, and classifications.  
   **Fix now or later:** Now before panel/demo use.

9. **Severity: Medium - Docs overclaim current implementation**  
   **Evidence:** `README.md:26` claims Prisma/SQLite persistence; `docs/TECHNICAL_AUDIT.md:436-437` claims WAF/CyberTrace readiness; code still uses cookies and install fails.  
   **Why it matters:** Reviewers will trust docs that do not match the app.  
   **Fix recommendation:** Reword docs around current status: partially implemented Prisma, WAF-visible forms, future CyberTrace ingest.  
   **Fix now or later:** Now.

10. **Severity: Medium - Docker cannot run as-is**  
    **Evidence:** `docker-compose.yml:6-8` references `Dockerfile`; no Dockerfile exists in file tree.  
    **Why it matters:** `docker-compose up --build` cannot succeed.  
    **Fix recommendation:** Add a minimal Dockerfile later and include Prisma generate/migrate/seed decisions.  
    **Fix now or later:** Later, after app build is fixed.

11. **Severity: Low - Validation strategy is split**  
    **Evidence:** Shared validators in `lib/validation.ts`; Zod schemas in `/login/submit` and `/request-copy/submit`; raw HTML client scripts in `app/login/route.ts` and copy request route.  
    **Why it matters:** Rules can drift across client, cookie routes, and Prisma routes.  
    **Fix recommendation:** Use one server-boundary validation strategy, preferably Zod or a single shared validation layer; client validation remains UX-only.  
    **Fix now or later:** Later.

12. **Severity: Low - Generated docs are in audit scope**  
    **Evidence:** `docs/CODEBASE.md`, `docs/codebase_manifest.json`, and `docs/codebase_verify_report.md` exist from prior bundling.  
    **Why it matters:** Future codebase searches can double-count source snippets embedded in `docs/CODEBASE.md`.  
    **Fix recommendation:** Exclude generated bundle docs from future source audits or move them to an archive path.  
    **Fix now or later:** Later.

## 5. Route Audit

| Public URL | Method | File path | Type | UI/response | Middleware rewrite | Cookies | Prisma | WAF relevance | Recommendation |
|---|---|---|---|---|---|---|---|---|---|
| `/` | GET | `app/page.tsx` | `page.tsx` | React page | No | Reads `citizen_comments` | No | Low; public landing and feedback display | Keep, remove public lab wording and cookie comments. |
| `/services` | GET | `app/services/page.tsx` | `page.tsx` | React page | No | No | No | Low | Keep. |
| `/records/search` | GET | `app/records/search/page.tsx` | `page.tsx` | React page | No | No | No | High; query parameter inspection | Keep native GET; align docs field name with actual `query`. |
| `/records/[recordNo]` | GET | `app/records/[recordNo]/page.tsx` | `page.tsx` | React page | No | No | No | Medium; path param inspection | Keep; remove CyberTrace/ModSecurity wording. |
| `/transactions/status` | GET | `app/transactions/status/page.tsx` | `page.tsx` | React page | No | Reads `user_tickets`, `user_appointments`, `user_copy_requests` | No | High; reference query route | Keep, migrate reads to Prisma. |
| `/support` | GET | `app/support/page.tsx` | `page.tsx` | React client page | No | No | No | Medium; form source | Keep native form; clean categories. |
| `/support/submit` | POST | `app/support/submit/route.ts` | `route.ts` | Redirect/JSON error | No | Reads/writes `user_tickets` | No | High; form body inspection | Keep path, migrate persistence. |
| `/appointments` | GET | `app/appointments/page.tsx` | `page.tsx` | React client page | No | No | No | Medium | Keep native form. |
| `/appointments/submit` | POST | `app/appointments/submit/route.ts` | `route.ts` | Redirect/JSON error | No | Reads/writes `user_appointments` | No | High | Keep path, migrate persistence. |
| `/comments` | GET | `app/comments/page.tsx` | `page.tsx` | React page | No | No | Reads `prisma.comment` | Medium | Keep, but reconcile with homepage cookie comments. |
| `/comments/submit` | POST | `app/comments/submit/route.ts` | `route.ts` | Redirect | No | Reads/writes `citizen_comments` | No in this handler | High | Decide cookie or Prisma; preferred Prisma. |
| `/login` | GET | `app/login/route.ts` | `route.ts` | Raw HTML | No | No | No | High; login form body | Convert GET UI to `page.tsx` later. |
| `/login` | POST | `app/login/route.ts` | `route.ts` | Redirect | Yes, rewritten to `/login/submit` by middleware | Writes `demo_user_logged` if reached | No | High | Remove duplicate/competing handler or rewrite. |
| `/login/submit` | POST | `app/login/submit/route.ts` | `route.ts` | Redirect/error | Internal target from middleware | No | Writes `LoginAttempt` | High | Keep only if form action points here explicitly. |
| `/records/[recordNo]/request-copy` | GET | `app/records/[recordNo]/request-copy/route.ts` | `route.ts` | Raw HTML | No | No | No | Medium | Convert GET UI to `page.tsx` later. |
| `/records/[recordNo]/request-copy` | POST | `app/records/[recordNo]/request-copy/route.ts` | `route.ts` | Redirect/JSON error | Yes, rewritten to `/request-copy/submit` by middleware | Reads/writes `user_copy_requests` if reached | No | High | Remove duplicate/competing handler or rewrite. |
| `/records/[recordNo]/request-copy/submit` | POST | `app/records/[recordNo]/request-copy/submit/route.ts` | `route.ts` | Redirect/error | Internal target from middleware | No | Reads `Record`, writes `Transaction` | High | Keep only with explicit action or documented rewrite. |
| `/success` | GET | `app/success/page.tsx` | `page.tsx` | React page | No | No | No | Low | Keep; reduce query-string personal data. |
| `/demo-guide` | GET | `app/demo-guide/page.tsx` | `page.tsx` | React page | No | No | No | Developer/WAF docs | Keep hidden/developer-facing; reword overclaims. |

No same-segment `page.tsx` plus `route.ts` conflicts were found. The main route clarity issue is duplicated POST behavior hidden behind middleware rewrites.

## 6. Form Audit

| Form | File path | Method/action | Fields | Validation | Success/error | WAF-visible body | Findings |
|---|---|---|---|---|---|---|---|
| Records search | `app/records/search/page.tsx:72-90` | GET `/records/search` | `query` | Browser text input only | Results/empty state in page | Yes, query string | Good; docs/scripts sometimes use `q`, `city`, `status`, which do not match actual page. |
| Transaction lookup | `app/transactions/status/page.tsx:170-195` | GET `/transactions/status` | `ref` required | Browser required only | Match or not found state | Yes, query string | Good WAF route; reads cookie stores. |
| Support ticket | `app/support/page.tsx:138-285`; handler `app/support/submit/route.ts` | POST `/support/submit` | `email`, `category`, `subject`, `referenceNo`, `message` | Client React validation plus `validateSupportForm` server validation | 303 `/success` or JSON 400 | Yes | Good form mechanics; cookie persistence and public wording need cleanup. |
| Appointment request | `app/appointments/page.tsx:149-322`; handler `app/appointments/submit/route.ts` | POST `/appointments/submit` | `fullName`, `email`, `branch`, `serviceType`, `preferredDate`, `notes` | Client React validation plus `validateAppointmentForm` server validation | 303 `/success` or JSON 400 | Yes | Good mechanics; cookie persistence. |
| Homepage comments | `app/CommentsForm.tsx:83-151`; handler `app/comments/submit/route.ts` | POST `/comments/submit` | `displayName`, `message` | Client React validation; handler does not use shared/Zod validation | 303 `/success` | Yes | Duplicates `/comments` page form; writes cookie while `/comments` page reads Prisma. |
| Comments page form | `app/comments/page.tsx:99-138`; handler `app/comments/submit/route.ts` | POST `/comments/submit` | `displayName`, `message` | Browser required only | 303 `/success` | Yes | Handler persistence conflicts with page's Prisma read path. |
| Demo login | `app/login/route.ts:70-128`; handler path rewritten by middleware | POST `/login` externally | `username`, `password` | Raw HTML JS validation; Zod in `/login/submit` | Redirect to `/login?attempt=true&username=...` if rewritten; `/success` if base POST reached | Yes | Password not stored, but username is put in query params; duplicate handlers. |
| Certified copy request | `app/records/[recordNo]/request-copy/route.ts:94-223`; handler path rewritten by middleware | POST `/records/${recordNo}/request-copy` externally | `fullName`, `email`, `purpose`, `deliveryOption`, `remarks` | Raw HTML JS validation; shared validation in base POST; Zod in `/submit` POST | Redirect to `/transactions/status?ref=...` if rewritten; `/success` if base POST reached | Yes | Duplicate handlers and different persistence destinations. |

No Server Actions were found. Fetch/AJAX is used only in traffic scripts (`scripts/normal-requests.ts`, `scripts/suspicious-requests.ts`), not in user-facing forms.

## 7. Persistence Audit

| Flow | Current write location | Current read location | Store | Raw user input | Email/name/message | Password stored | Cookie attributes | JSON guarded | Risk | Recommended final path |
|---|---|---|---|---|---|---|---|---|---|---|
| Homepage comments | `app/comments/submit/route.ts` | `app/page.tsx` | `citizen_comments` cookie | Yes | Name/message | No | `maxAge`, `path`; no `httpOnly`, `secure`, `sameSite` | Yes | Medium | Move to Prisma `Comment`; keep flash cookie only. |
| Comments page | Handler writes cookie, page reads `prisma.comment` | `app/comments/page.tsx:18` | Mismatched cookie vs Prisma | Yes | Name/message | No | Same as above | Yes in handler | High consistency risk | Make submit handler write Prisma. |
| Support ticket | `app/support/submit/route.ts:30-64` | `app/transactions/status/page.tsx` | `user_tickets` cookie | Yes | Email/subject/message | No | `maxAge`, `path` only | Yes | High | Prisma `SupportTicket`. |
| Appointment | `app/appointments/submit/route.ts:31-64` | `app/transactions/status/page.tsx` | `user_appointments` cookie | Yes | Full name/email/notes | No | `maxAge`, `path` only | Yes | High | Prisma `Appointment`. |
| Certified copy | Base POST writes cookie; submit route writes DB | `app/transactions/status/page.tsx` cookie reads; submit route redirects by transaction ref | `user_copy_requests` cookie and Prisma `Transaction` | Yes | Full name/email/remarks | No | `maxAge`, `path` only | Yes | High | Prisma `Transaction`; remove cookie path. |
| Demo login | `app/login/route.ts` cookie if base handler reached; `/login/submit` writes Prisma | Query string and DB | `demo_user_logged` cookie / `LoginAttempt` | Username only | Username | No | `maxAge`, `path` only | N/A | Medium | Prisma `LoginAttempt`; no username in query string if avoidable. |
| Transaction status | No direct write | `app/transactions/status/page.tsx` | Cookie session arrays plus static seeds | Shows stored labels | Email/name can appear in subtext | No | N/A | Yes | Medium | Read Prisma submissions by reference. |
| Records search/detail | Static in-memory data | Pages import `MOCK_RECORDS` | `lib/db.ts` array | No user input stored | Mock owner data | No | N/A | N/A | Low | Move to Prisma `Record` when persistence cleanup starts. |

Classification: comments/support/appointments/copy request need Prisma migration; login needs cookie cleanup; records can remain mock for audit but should use seeded Prisma before Docker/WAF demo.

## 8. Prisma/SQLite Audit

`prisma/schema.prisma` defines `Record`, `Transaction`, `SupportTicket`, `Appointment`, `Comment`, and `LoginAttempt`. `prisma/seed.ts` seeds records, transactions, and comments, and deletes all six model tables first.

Verified issues:

| Area | Evidence | Verdict |
|---|---|---|
| SQLite configured | `prisma/schema.prisma:1-3` uses `provider = "sqlite"` and `url = env("DATABASE_URL")` | Verified, but Prisma 7 CLI rejects this legacy config. |
| Models present | `prisma/schema.prisma:10-69` | Verified. |
| Seed present | `prisma/seed.ts:8-194` | Verified. |
| Prisma client export | App routes import `prisma` from `@/lib/db`, but `lib/db.ts` only exports `MOCK_RECORDS` and no Prisma client | Broken/needs follow-up. |
| Missing dependencies | `package.json` lacks `prisma`, `@prisma/client`, `zod`, `tsx` | Verified. |
| Seed script | `package.json` has no `prisma` seed config and no `db:*` scripts | Missing. |
| Database URL docs | `.env.example` exists but was not included in source audit content due env exclusion; compose sets `DATABASE_URL=file:./dev.db` | Partial. |
| Consistency | Comments page reads Prisma, comment submit writes cookie; copy submit route writes Prisma, base copy route writes cookie | Half-implemented. |

Plan: first fix dependencies and `lib/db.ts` Prisma client export, then migrate one flow at a time to the models already present. Keep URLs and form fields unchanged.

## 9. Middleware/Proxy Audit

`middleware.ts` matches `/login` and `/records/:path*/request-copy` (`middleware.ts:27-30`). For POST requests, it rewrites:

| External request | Internal destination | Evidence | Recommendation |
|---|---|---|---|
| `POST /login` | `/login/submit` | `middleware.ts:9-11` | Remove rewrite by making form action explicit, or remove duplicate base POST. |
| `POST /records/[recordNo]/request-copy` | `/records/[recordNo]/request-copy/submit` | `middleware.ts:14-19` | Same: prefer explicit route clarity for WAF logs. |

The rewrite preserves external clean URL behavior but creates audit confusion because base route handlers also implement POST logic. Do not migrate `middleware.ts` to `proxy.ts` yet; document and simplify route behavior in a later fix batch.

## 10. Validation Audit

| Flow | Current validation | Evidence | Recommendation |
|---|---|---|---|
| Support | Client React validation plus `validateSupportForm` | `app/support/page.tsx:13-65`; `app/support/submit/route.ts:18`; `lib/validation.ts:24` | Keep server validation authoritative. |
| Appointment | Client React validation plus `validateAppointmentForm` | `app/appointments/page.tsx:13-70`; `app/appointments/submit/route.ts:19`; `lib/validation.ts:77` | Keep server validation authoritative. |
| Cookie copy request | Raw HTML JS plus `validateCopyForm` | `app/records/[recordNo]/request-copy/route.ts:237-311`; `route.ts:332`; `lib/validation.ts:142` | Replace raw JS with shared client component later. |
| Prisma copy submit | Zod schema | `app/records/[recordNo]/request-copy/submit/route.ts:5-11,40` | Keep if Zod dependency is added. |
| Login submit | Zod schema | `app/login/submit/route.ts:5-7,19` | Keep if Zod dependency is added. |
| Comments | Client/browser required only; no shared server validator in cookie handler | `app/CommentsForm.tsx:13-44`; `app/comments/page.tsx:99-129`; `app/comments/submit/route.ts` | Add server validation. |

Preferred strategy: choose Zod or one shared validation layer for all server route boundaries. Client-side validation can remain for UX but must not be the source of truth.

## 11. Public Wording/Data Audit

| Phrase | File | Public or developer-only | Action | Suggested wording |
|---|---|---|---|---|
| `WAF Demo Guide` | `app/layout.tsx:69` | Public header | Replace/hide | `Demo Guide` or remove from header. |
| `WAF Test Guide` | `app/layout.tsx:94` | Public footer | Replace/hide | `Technical Notes` or remove. |
| `CyberTrace Cybersecurity WAF Testing` | `components/SiteHeader.tsx:28` | Public component if used | Replace | `Demo records portal - no real transactions`. |
| `CyberTrace Capstone Project`, `ModSecurity`, `OWASP Core Rule Set`, `WAF traffic inspection` | `components/SiteFooter.tsx:28-35` | Public component if used | Replace | `Demonstration environment. Do not enter real personal data.` |
| `CyberTrace compliance evaluation and ModSecurity protection diagnostics` | `app/records/[recordNo]/page.tsx:191` | Public record detail | Replace | `mock data for local demonstration only`. |
| `WAF inspection checks`, `WAF form compliance` | `app/success/page.tsx:39,48` | Public success page | Replace | `demo reference tracking`. |
| `Su Yao` | `app/page.tsx:27`; `app/CommentsForm.tsx:100`; `app/appointments/page.tsx:165`; `lib/db.ts:15` | Public | Replace | `Maria Santos` or `Demo Resident A`. |
| `Delta-level mutant zones`, `Delta Mutant Classification` | `app/page.tsx:28`; `app/support/page.tsx:192`; `lib/demo-config.ts:29`; `lib/db.ts:16,20` | Public | Replace | `Rural cadastral zone`, `Classification inquiry`. |
| `Sarah Connor`, `Bruce Wayne`, `Tony Stark` | `lib/db.ts:25,35,45`; status seeds | Public data | Replace | Neutral demo names. |
| `Penetration Testing`, `SQL Injection`, `XSS`, `LFI`, `OWASP CRS` | `app/demo-guide/page.tsx`; `docs/*`; `scripts/*` | Developer-only if hidden | Keep but reword overclaims | Use `inspection/anomaly scoring` language and local-only safety notes. |

Public pages should feel like a records portal. Security terms belong in docs or a non-public demo guide only.

## 12. UI/UX and Accessibility Audit

Must-fix:

| Issue | Evidence | Recommendation |
|---|---|---|
| Raw HTML pages are outside shared layout/component accessibility patterns | `app/login/route.ts`; `app/records/[recordNo]/request-copy/route.ts` | Convert to React pages later. |
| Public lab/security disclaimers distract from citizen flows | `app/layout.tsx:69,94`; `app/success/page.tsx:39,48` | Neutral wording. |
| Comments have two UI entry points with different read/write storage | `app/CommentsForm.tsx`; `app/comments/page.tsx`; `app/comments/submit/route.ts` | Decide one canonical comment flow. |

Nice-to-have:

| Strength / improvement | Evidence | Recommendation |
|---|---|---|
| Labels and required indicators are mostly present | `app/support/page.tsx:148-260`; `app/appointments/page.tsx:158-304`; raw HTML routes include `<label>` | Preserve this. |
| Error summaries and focus management exist in client forms | `app/support/page.tsx:116-127`; `app/appointments/page.tsx:127-138`; `app/CommentsForm.tsx:62-73` | Keep pattern. |
| Tables have headers and horizontal overflow | `app/records/search/page.tsx:132-142`; `app/demo-guide/page.tsx:193-202` | Keep. |
| Header component includes an `h1`, while pages also have `h1` | `components/SiteHeader.tsx:40`; page `h1`s | If this header is used globally later, make brand text non-`h1`. |

The UI is acceptable for a capstone demo after targeted wording, data, and persistence cleanup. No large redesign is needed.

## 13. WAF/CyberTrace Readiness

Ready parts:

| Area | Evidence | Verdict |
|---|---|---|
| Native forms | `rg` found standard `method="post"` / `method="get"` forms and no Server Actions | Good. |
| Explicit public route paths | `/records/search`, `/transactions/status`, `/support/submit`, `/appointments/submit`, `/comments/submit` | Good. |
| Request metadata helper | `lib/request-metadata.ts:13-24` documents WAF/CyberTrace separation and `x-demo-trace-id` | Useful. |
| Scripts use `BASE_URL` | `scripts/normal-requests.ts:7`; `scripts/suspicious-requests.ts:7` | Good; should target WAF port later. |

Missing or risky parts:

| Area | Evidence | Recommendation |
|---|---|---|
| Middleware rewrite ambiguity | `middleware.ts:9-19` | Simplify before relying on WAF route logs. |
| Docs overclaim blocking | `docs/WAF_READY_ROUTES.md:31,39`; scripts log `BLOCKED`/`PASSED` | Reword to anomaly scoring / inspection results. |
| Evasion/bypass risk | Scripts include obvious test payloads, no evasion guidance found | Keep local-only wording; avoid adding bypass examples. |
| CyberTrace ingest | Docs correctly describe future external ingest, but some UI exposes it publicly | Keep in docs; remove from public UI. |
| Route docs mismatch actual fields | Docs/scripts use `q`, `city`, `status` for search; app uses only `query` | Align docs/scripts with app or app with docs. |

## 14. Docker/Runtime Audit

| Check | Evidence | Verdict |
|---|---|---|
| Docker compose exists | `docker-compose.yml` | Verified. |
| Dockerfile exists | `docker-compose.yml:8` references `Dockerfile`; file tree has none | Missing. |
| Standalone output | `next.config.ts:22` sets `output: 'standalone'` | Good for Docker later. |
| Runtime DB | `docker-compose.yml:13` sets `DATABASE_URL=file:./dev.db` | Needs persistence/volume decision. |
| Prisma setup in container | No Dockerfile and no package scripts for `prisma generate`, migrate, or seed | Missing. |
| WAF proxy service | No ModSecurity/CRS service in compose | Future work only. |

Can it run in Docker as-is? **No.** Minimal cleanup later: add Dockerfile, fix dependency installation, add Prisma generate/migrate/seed strategy, mount or initialize SQLite deliberately, and add a separate future WAF compose service only after the app builds.

## 15. Recommended Fix Batches

**Batch 1: must-fix before WAF integration**

- Fix npm dependency conflict.
- Add missing Prisma/Zod/tsx dependencies or remove unused Prisma/Zod code paths.
- Update TypeScript target.
- Make `npm install`, `npm run build`, `npm run lint`, and `npx tsc --noEmit` meaningful again.

**Batch 2: persistence cleanup**

- Add a correct Prisma client export in `lib/db.ts` or a separate `lib/prisma.ts`.
- Move support, appointment, comment, copy request, and login attempt writes to Prisma.
- Use cookies only for flash/reference state.
- Keep form URLs and field names stable.

**Batch 3: route/raw HTML cleanup**

- Remove middleware rewrite ambiguity.
- Convert login and copy request GET UIs from raw HTML route handlers to React pages.
- Keep native HTML forms and route handlers.

**Batch 4: public wording/docs cleanup**

- Remove WAF/CyberTrace/security terms from public pages.
- Replace lore/famous demo data with neutral records data.
- Reword docs around local-only inspection/anomaly scoring, not guaranteed blocking.
- Align route docs and scripts with actual field names.

**Batch 5: Docker/ModSecurity readiness**

- Add Dockerfile.
- Add Prisma startup strategy.
- Add persistent SQLite volume or documented seeded DB workflow.
- Add ModSecurity/CRS proxy compose service later, with scripts targeting the WAF port.

## 16. Do-Not-Change List

- Keep native browser form submissions.
- Keep explicit route handlers for WAF-visible POSTs.
- Keep GET `/records/search` and GET `/transactions/status`.
- Keep local-only traffic scripts, but reword them safely.
- Keep `x-demo-trace-id` request metadata support.
- Keep the Prisma model direction.
- Keep accessibility patterns: labels, required markers, focus rings, error summaries, table headers.

## 17. Exact Files to Edit Later

Tooling and install:

- `package.json`
- `package-lock.json`
- `tsconfig.json`
- `.eslintrc.json`
- `eslint.config.mjs`

Prisma/persistence:

- `lib/db.ts`
- `prisma/schema.prisma`
- `prisma/seed.ts`
- `app/comments/submit/route.ts`
- `app/support/submit/route.ts`
- `app/appointments/submit/route.ts`
- `app/records/[recordNo]/request-copy/route.ts`
- `app/records/[recordNo]/request-copy/submit/route.ts`
- `app/login/route.ts`
- `app/login/submit/route.ts`
- `app/transactions/status/page.tsx`
- `app/page.tsx`

Route cleanup:

- `middleware.ts`
- `app/login/route.ts`
- `app/records/[recordNo]/request-copy/route.ts`
- `app/login/submit/route.ts`
- `app/records/[recordNo]/request-copy/submit/route.ts`

Public wording/data:

- `app/layout.tsx`
- `components/SiteHeader.tsx`
- `components/SiteFooter.tsx`
- `app/page.tsx`
- `app/records/[recordNo]/page.tsx`
- `app/success/page.tsx`
- `app/support/page.tsx`
- `app/transactions/status/page.tsx`
- `lib/db.ts`
- `lib/demo-config.ts`

Docs/scripts:

- `README.md`
- `docs/WAF_READY_ROUTES.md`
- `docs/FUTURE_INTEGRATION.md`
- `docs/TECHNICAL_AUDIT.md`
- `app/demo-guide/page.tsx`
- `lib/routes.ts`
- `scripts/normal-requests.ts`
- `scripts/suspicious-requests.ts`

Docker:

- `docker-compose.yml`
- `Dockerfile` (new later)

## 18. Final Recommendation

Fix the dependency/tooling baseline first: align ESLint/Next lint packages, add missing Prisma/Zod/tsx dependencies, update the TypeScript target, and rerun install/build/type/lint. Do not start persistence or WAF cleanup until the project can install and verify from a clean workspace.

