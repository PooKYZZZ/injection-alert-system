# ML Health, User Management, and MFA Remediation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:executing-plans` to implement this plan task-by-task. The repository forbids subagents unless explicitly requested, so execution will remain inline with equivalent review checkpoints.

**Goal:** Make ML Health, Model Operations, User Management, and MFA technically honest, protocol-correct, accessible, and maintainable without widening the system into an enterprise control plane.

**Architecture:** Keep the existing Browser → Next.js route handler → FastAPI boundary. ML Health remains a snapshot-oriented view of serving and packaged evaluation evidence; Model Operations explicitly reports when the local retraining capability is unavailable. User Management remains a server-authorized admin workspace with validated safe account data, and MFA remains a password-level login challenge backed by the existing pre-authentication cookie and protected API.

**Tech Stack:** Next.js 16 App Router, React 19, TypeScript, TanStack Query 5, Zod 4, Vitest/Testing Library, existing FastAPI/Pydantic backend, CSS modules/Tailwind utility classes, and the authenticated in-app browser.

---

## Scope and governance decisions

- **Primary change kind:** `cross-cutting refactor`, because the same honesty, cancellation, date, and accessibility concerns cross several frontend owners and the BFF contract boundary.
- **Secondary change kinds:** `direct fix` for the hydration mismatch, wrong drift-threshold copy, Model Operations 503 loading behavior, and MFA page guard; `local refactor` for typed account parsing and action-state ownership; `boundary extraction` only for a shared date formatter if existing ownership and tests demonstrate real reuse.
- **Scope:** ML Health/Model Operations plus User Management/MFA only. No Dashboard/Alerts changes, migrations, new dependencies, model promotion, hosted-account mutation, or production registry writes.
- **Extraction outcome:** Keep presentation helpers local where one page owns them. Use the existing `frontend/lib/date-time.ts` only for deterministic timestamp behavior shared by User Management and Model Operations. Do not create a generic admin action framework or a new ML observability package.
- **Contract note:** Prefer frontend-only adaptation. Any additive BFF schema change must be validated directly and must preserve missing values as missing. No confidence thresholds, action mapping, or authorization semantics will be changed.
- **Convention decision:** Preserve the existing feature-folder structure, Vitest style, TanStack Query options, route-handler auth guards, and CSS modules. Improve the current owners before extracting new components.
- **Validation depth:** Focused red/green tests per task, then frontend full suite, lint, typecheck, production build, selected backend tests if a backend contract is touched, and fresh authenticated browser checks.
- **Escalation:** No escalation is currently required. If honest provenance requires a new public backend field or a schema/database change, stop and document that contract decision before implementing it; this plan deliberately avoids it unless the live source proves it necessary.

## Task 1: Establish ML Health truth states and remove misleading metrics

**Files:**

- Modify: `frontend/components/ml-health/MLHealthWorkspaceViewModel.ts`
- Modify: `frontend/components/ml-health/MLHealthOverviewSection.tsx`
- Modify: `frontend/components/ml-health/MLHealthDiagnosticsSection.tsx`
- Modify: `frontend/components/ml-health/MLHealthWorkspace.tsx`
- Modify: `frontend/features/ml-health/types.ts` only if a view-model contract needs a narrow additive field
- Test: `frontend/components/ml-health/MLHealthWorkspaceViewModel.test.ts`
- Test: add or modify `frontend/components/ml-health/MLHealthWorkspace.test.tsx` only if workspace semantics need direct rendering coverage

- [ ] **Step 1: Add failing view-model tests for no traffic and honest evidence labels.**

  Cover at least:

  - `traffic_processed === 0` produces `Not measured` for latency, not `0.0ms`;
  - a missing drift score/status remains `Not reported`;
  - evaluation metrics are described as reported evaluation evidence rather than current traffic quality;
  - distribution rows do not create a baseline comparison when only current counts exist;
  - policy ranges remain derived from the configured confidence thresholds and are not changed.

- [ ] **Step 2: Run the focused view-model test and confirm the new assertions fail for the expected reasons.**

  Run from `frontend`:

  ```powershell
  npx vitest run --pool=threads components/ml-health/MLHealthWorkspaceViewModel.test.ts
  ```

  Expected initial result: failure on the old `0.0ms` and/or missing evidence wording, not a test-discovery or import error.

- [ ] **Step 3: Implement the smallest view-model correction.**

  Use explicit “Not measured”/“Not reported” states. Keep the page labelled snapshot/reported-window. Remove the hardcoded `threshold 0.050` copy because it does not represent the backend drift decision; replace it with wording that does not imply an untransported threshold. Preserve the existing action policy and confidence thresholds.

- [ ] **Step 4: Add accessible state semantics and concise evidence context.**

  Ensure attention signals communicate their state through text, not only colored dots. Add table captions or visually-hidden labels and `scope="col"` where the current tables are made more understandable. Keep the existing numeric tables as the accessible fallback for visual summaries.

- [ ] **Step 5: Run the focused ML Health tests and inspect the diff.**

  Run the same Vitest command plus `git diff --check`. Confirm no new API fields or fake values were introduced.

- [ ] **Step 6: Commit the ML Health truth-state change.**

  ```powershell
  git add frontend/components/ml-health frontend/features/ml-health
  git commit -m "fix(frontend): make ML health evidence states explicit"
  ```

## Task 2: Make Model Operations capability-aware and cancellable

**Files:**

- Modify: `frontend/features/ml-model/queries.ts`
- Modify: `frontend/components/ml-model/MLModelWorkspace.tsx`
- Modify: `frontend/components/ml-model/MLModelOverviewSection.tsx` only if unavailable copy belongs there
- Test: `frontend/features/ml-model/queries.test.tsx`
- Test: `frontend/components/ml-model/MLModelWorkspace.test.tsx`

- [ ] **Step 1: Add failing query tests for abort propagation and 503 classification.**

  Exercise the real query option function with a stubbed `fetch` and assert:

  - the `AbortSignal` supplied by the query function is passed to `fetch`;
  - an HTTP 503 becomes a typed/status-bearing error that the UI can distinguish;
  - the retry policy does not retry a deliberate 503 capability response.

- [ ] **Step 2: Run the focused query tests and confirm the expected red failure.**

  ```powershell
  npx vitest run --pool=threads features/ml-model/queries.test.tsx
  ```

- [ ] **Step 3: Implement a narrow typed HTTP error and signal-aware fetch.**

  Keep the current query keys and API paths. Make the query function accept TanStack Query’s `signal`, pass it to `fetch`, and use a bounded retry predicate that returns false for 4xx/5xx capability responses. Preserve retries only where they are meaningful for transient failures.

- [ ] **Step 4: Add a failing workspace test for the explicit unavailable state.**

  Model the 503 state without enabling retraining and assert that the UI says Model Operations are unavailable in this environment, explains that local retraining control is disabled, and provides a manual retry. Assert it does not remain in a generic loading state after the query has failed.

- [ ] **Step 5: Implement the unavailable state and protect controls.**

  Render a role-alert/unavailable message with a retry button. Do not show run controls or pretend that a safe run list exists while the control plane is unavailable. Keep mutation authorization and backend behavior unchanged.

- [ ] **Step 6: Run focused Model Operations tests and inspect the exact network behavior locally.**

  Use the running local services to confirm `/api/ml-model/summary` and `/api/ml-model/runs` return 503 and the browser presents the explicit state promptly. Confirm aborts do not produce uncaught errors when navigating away.

- [ ] **Step 7: Commit the Model Operations change.**

  ```powershell
  git add frontend/features/ml-model frontend/components/ml-model
  git commit -m "fix(frontend): explain unavailable model operations"
  ```

## Task 3: Improve ML Health navigation and responsive discoverability

**Files:**

- Modify: `frontend/components/ml-health/MLHealthWorkspace.tsx`
- Modify: `frontend/components/ml-health/MLHealthDiagnosticsSection.tsx`
- Modify: `frontend/components/ml-health/MLHealthOverviewSection.tsx`
- Modify: `frontend/components/ml-health/MLHealthWorkspace.module.css`
- Modify: `frontend/components/ml-model/MLModelRunsTable.tsx`
- Modify: `frontend/components/ml-model/MLModelWorkspace.module.css`
- Test: nearby ML Health/Model Operations component tests as required

- [ ] **Step 1: Add failing tests for selected view/tab semantics and text summaries.**

  Assert the active Overview/Diagnostics control exposes selected state, diagnostic tabs expose their active state, and the page contains text that summarizes any chart-like signal without relying on color or hover.

- [ ] **Step 2: Implement semantic button/tab state and non-color status text.**

  Use native buttons with `aria-pressed` or a minimal tab pattern appropriate to the existing interaction. Do not build a generic ARIA abstraction. Keep visible labels and focus styles.

- [ ] **Step 3: Add a small horizontal-scroll affordance to wide tables.**

  Preserve the table data and current desktop layout. Add a visible, concise hint on narrow containers and ensure overflow remains keyboard/assistive-technology usable. Do not add a table virtualization dependency.

- [ ] **Step 4: Run focused component tests, lint, and typecheck.**

  ```powershell
  npx vitest run --pool=threads components/ml-health components/ml-model
  npm run lint
  npm run typecheck
  ```

- [ ] **Step 5: Commit only if this group has a coherent user-facing boundary.**

  ```powershell
  git add frontend/components/ml-health frontend/components/ml-model
  git commit -m "feat(frontend): improve ML observability navigation"
  ```

## Task 4: Remove proven-dead legacy ML Health components

**Files to verify before deletion:**

- Candidate delete: `frontend/components/ml-health/ConfidenceDriftChart.tsx`
- Candidate delete: `frontend/components/ml-health/ConfidenceThresholds.tsx`
- Candidate delete: `frontend/components/ml-health/ConfidenceThresholds.test.tsx`
- Candidate delete: `frontend/components/ml-health/ModelHeader.tsx`
- Candidate delete: `frontend/components/ml-health/PerClassF1Chart.tsx`
- Candidate delete: `frontend/components/ml-health/PredictionDistribution.tsx`
- Candidate delete: `frontend/components/ml-health/ReliabilityDiagram.tsx`

- [ ] **Step 1: Trace every candidate reference before editing.**

  Run repository-scoped searches for each basename and symbol across TypeScript, tests, CSS, route files, barrel exports, dynamic imports, Next configuration, and build scripts. Confirm the only references are self-definitions and the test belonging solely to `ConfidenceThresholds`.

- [ ] **Step 2: Confirm the current route imports.**

  Trace `frontend/app/(dashboard)/ml-health/page.tsx` and its workspace imports to ensure no candidate is loaded indirectly.

- [ ] **Step 3: Delete only candidates whose reference audit is clean.**

  Do not remove current `MLHealthWorkspace`, overview, diagnostics, view-model, CSS, or tests.

- [ ] **Step 4: Run the full static and focused checks before committing.**

  ```powershell
  npx vitest run --pool=threads components/ml-health
  npm run lint
  npm run typecheck
  npm run build
  ```

- [ ] **Step 5: Commit cleanup separately.**

  ```powershell
  git add frontend/components/ml-health
  git commit -m "chore(frontend): remove unused ML health components"
  ```

## Task 5: Add deterministic shared timestamp formatting

**Files:**

- Modify: `frontend/lib/date-time.ts`
- Test: `frontend/lib/date-time.test.ts`
- Modify: `frontend/components/ml-model/MLModelOverviewSection.tsx`
- Modify: `frontend/components/ml-model/MLModelRunsTable.tsx`
- Test: `frontend/components/ml-model/MLModelWorkspace.test.tsx` if model date output is covered there

- [ ] **Step 1: Add failing formatter tests.**

  Cover an explicit stable UTC output with calendar context, a timezone-bearing timestamp, and malformed/null values. Keep existing alert formatting and relative-time behavior unchanged.

- [ ] **Step 2: Run the date test red.**

  ```powershell
  npx vitest run --pool=threads lib/date-time.test.ts
  ```

- [ ] **Step 3: Implement the smallest shared formatter.**

  Reuse `parseApiTimestamp`, use an explicit timezone/format suitable for server and client output, and return safe unknown text for malformed values. Do not use `suppressHydrationWarning`.

- [ ] **Step 4: Replace Model Operations’ local `toLocaleString()` calls.**

  Use the shared formatter for run/report timestamps so the page has calendar context and does not silently depend on server/browser locale differences.

- [ ] **Step 5: Run date and Model Operations tests green.**

- [ ] **Step 6: Commit the shared timestamp change.**

  ```powershell
  git add frontend/lib/date-time.ts frontend/components/ml-model
  git commit -m "fix(frontend): make model timestamps deterministic"
  ```

## Task 6: Validate and harden User Management behavior

**Files:**

- Modify: `frontend/features/user-management/contract.ts`
- Test: `frontend/features/user-management/contract.test.ts`
- Modify: `frontend/features/user-management/UserManagementWorkspace.tsx`
- Test: `frontend/features/user-management/UserManagementWorkspace.test.tsx`

- [ ] **Step 1: Add failing contract tests for account-list parsing.**

  Cover a valid safe account, a malformed timestamp/role/status, and an unexpected sensitive field. The parser must validate the safe shape and must not render an unsafe or malformed record as if valid.

- [ ] **Step 2: Add failing workspace tests for visible refresh/action failures and independent pending state.**

  Cover a failed refresh showing an actionable message, a per-row action disabling only the relevant action while pending, and email-verification wording that matches “queue/send a verification request.” Do not test against real accounts or hosted services.

- [ ] **Step 3: Run the focused User Management tests red.**

  ```powershell
  npx vitest run --pool=threads features/user-management/contract.test.ts features/user-management/UserManagementWorkspace.test.tsx
  ```

- [ ] **Step 4: Implement typed parsing and explicit error handling.**

  Add a Zod schema for the safe response. Make refresh reject non-2xx or malformed responses, preserve the prior list only with an explicit error notice, and provide a retry button. Keep server-side authorization unchanged.

- [ ] **Step 5: Implement per-row action state and accessible names.**

  Track pending actions by account/action, prevent duplicate submissions for the same action, preserve independent rows, and include the account name in button accessible names where needed. Keep MFA reset deliberate and protected; do not add automatic resets or destructive traffic mutations.

- [ ] **Step 6: Add table semantics and responsive guidance.**

  Add a caption/column scopes and a concise horizontal-scroll hint that appears when appropriate. Preserve all important account fields. Avoid an enterprise bulk-action redesign.

- [ ] **Step 7: Run focused tests, lint, and typecheck.**

- [ ] **Step 8: Commit the User Management change.**

  ```powershell
  git add frontend/features/user-management
  git commit -m "feat(frontend): harden user management feedback"
  ```

## Task 7: Make MFA verification protocol-correct and accessible

**Files:**

- Modify: `frontend/app/(auth)/mfa/verify/page.tsx`
- Modify: `frontend/features/user-management/MfaVerifyForm.tsx`
- Test: `frontend/features/user-management/MfaVerifyForm.test.tsx`
- Test: `frontend/lib/auth/route-guard.test.ts` or a new small page-guard helper test if the guard is extracted
- Test: `frontend/lib/auth/preauth.test.ts` only if a pure helper is added

- [ ] **Step 1: Add failing MFA form tests.**

  Assert semantic form submission, six-digit required/pattern behavior, `autocomplete="one-time-code"`, `inputMode="numeric"`, initial focus or an equivalent accessible focus path, `aria-describedby`/`aria-invalid` on errors, Enter-key submission, and safe API error rendering.

- [ ] **Step 2: Run the focused MFA form test red.**

  ```powershell
  npx vitest run --pool=threads features/user-management/MfaVerifyForm.test.tsx
  ```

- [ ] **Step 3: Implement the semantic accessible form.**

  Keep the six-digit client validation and existing API endpoint. Submit through the form, trim behavior only as appropriate, preserve generic server errors, and avoid adding recovery/bypass behavior. Use the existing backend rate-limit/replay protections.

- [ ] **Step 4: Add a failing page-guard test for the fully authenticated-session case.**

  Demonstrate that a session with `auth_level: 'mfa'` is not allowed to render the login-MFA verification form, and that a password-level `login_mfa` session with a valid pre-auth handle remains eligible. Use the existing auth guard seams rather than weakening the API route.

- [ ] **Step 5: Implement the narrow page guard.**

  Read the pre-auth handle with `readPreAuthHandleFromCookies()`. Require password-level authentication, `auth_method === 'password'`, active `login_mfa` challenge metadata, and a valid pre-auth handle before rendering. Redirect invalid/direct visits to `/login`. Do not change the generic guard used by enrollment/recovery routes unless a test proves it is wrong for those flows.

- [ ] **Step 6: Run MFA tests and inspect the authenticated browser route.**

  A normal fully authenticated browser session should redirect from `/mfa/verify` rather than show a form that cannot work. Do not submit invalid TOTP values to the hosted auth system.

- [ ] **Step 7: Commit the MFA change.**

  ```powershell
  git add frontend/app/(auth)/mfa/verify frontend/features/user-management/MfaVerifyForm.tsx frontend/features/user-management/MfaVerifyForm.test.tsx frontend/lib/auth
  git commit -m "fix(auth): align MFA page with login challenge"
  ```

## Task 8: Fresh senior review and regression correction

**Files:** any affected files only, after evidence.

- [ ] **Step 1: Review all touched files for duplicated state, unsafe casts, stale copy, dead imports, and misleading status labels.**
- [ ] **Step 2: Re-run repository-wide reference searches after legacy cleanup.**
- [ ] **Step 3: Run the complete frontend validation set.**

  ```powershell
  cd frontend
  npx vitest run --pool=threads
  npm run lint
  npm run typecheck
  npm run build
  ```

- [ ] **Step 4: Run relevant backend tests if the implementation touched backend contracts.**

  If no backend files changed, record backend contract validation as not required for this branch and retain the already observed local `/api/ml-health`/503 evidence. If backend files changed, run the narrow tests first and then the broad suite, reporting environment failures separately.

- [ ] **Step 5: Re-audit the authenticated browser.**

  Inspect `/ml-health`, `/ml-model`, `/user-management`, and `/mfa/verify` for desktop layout, semantic state, network responses, console errors, hydration warnings, route behavior, and no accidental hosted mutations. The in-app browser currently cannot expose a viewport-resize capability; use DOM/CSS evidence and report narrow viewport runtime as unverified if that remains true.

- [ ] **Step 6: Review the complete diff and commit graph.**

  Confirm no secrets, generated changes, unrelated user edits, credentials, hosted DB writes, or production model writes are included. Use `git diff --check`, `git status`, and a commit-by-commit review.

- [ ] **Step 7: Stop when remaining issues are subjective polish, speculative optimization, or enterprise scope.**

## Expected commit sequence

1. `docs: define ML health admin and MFA remediation` — already created as `c3b000b`.
2. `fix(frontend): make ML health evidence states explicit`.
3. `fix(frontend): explain unavailable model operations`.
4. `feat(frontend): improve ML observability navigation` if Task 3 is non-trivial and coherent.
5. `chore(frontend): remove unused ML health components` — separate cleanup commit.
6. `fix(frontend): make model timestamps deterministic`.
7. `feat(frontend): harden user management feedback`.
8. `fix(auth): align MFA page with login challenge`.
9. Optional small cleanup commit only if fresh review identifies a directly related, proven defect.

Do not create or push an external PR automatically in this task. Leave the branch with logical commits ready for review unless the user explicitly asks for PR creation.

## Final reporting requirements

The final report will record, per change: Before → Problem → Root cause → Research → Decision → Implementation → Tests → Browser validation → Result. It will distinguish `PASS`, `FAIL`, `NOT_RUN`, local-only proof, hosted behavior, production readiness, and unresolved evidence gaps. It will explicitly list unchanged/deferred items, including numeric system confidence, severity-model expansion, retraining enablement, database changes, and any viewport limitation.
