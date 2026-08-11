# Dashboard Responsive Layout and Attack-Type View Toggle Implementation Plan

> **For agentic workers:** Execute this plan task-by-task in the isolated worktree. The repository explicitly forbids subagents, so execution is inline with review checkpoints. Use TDD for behavior changes.

**Goal:** Make the master dashboard responsive at medium/narrow widths and let users switch the attack-type panel between the current bar visualization and the existing panel-review pie visualization using one shared data model.

**Architecture:** Preserve Browser → Next.js BFF → FastAPI and the current React/TanStack Query/Recharts boundaries. Keep shell responsiveness in the shell/layout components, keep chart-view state inside `AttackTypePanel`, and keep query transformations shared rather than adding global state or a generic chart abstraction.

**Tech Stack:** Next.js 16, React 19, Tailwind CSS v4, Radix Dialog, Recharts 3.8, TanStack Query 5, Vitest, Testing Library, Playwright.

---

## Working contract

### Scope

- Use `master` as the implementation and PR base.
- Read `panel-review` only for the existing pie-chart behavior and styling source.
- Improve the active dashboard shell, grids, chart sizing, table overflow, view toggle, and focused state/accessibility behavior.
- Preserve all existing API payloads, query keys, confidence/action mappings, and backend behavior.

### Out of scope

- Backend, API, database, schema, or deployment changes.
- New npm dependencies.
- A full visual redesign or replacement of the existing color/token system.
- A generic chart abstraction.
- Global/URL/persisted view state.
- Source-IP view switching.
- Changes to inactive legacy dashboard analytics components unless live ownership requires them.

### Primary and secondary change kinds

- Primary: `new feature slice`.
- Secondary: `direct fix`, `local refactor`.

### Extraction decision

- Keep the normalized attack-type entry transformation local to `AttackTypePanel`.
- Keep bar and pie rendering in the existing component boundary.
- Reuse existing `StateViews`; do not create a dashboard-wide state framework.

### Contract and escalation decision

No public API, database, authentication, backend, or external integration contract changes are planned. Escalate if live inspection shows the toggle requires a new data shape or if responsive navigation conflicts with an existing shell contract.

## PR dependency map

> **REVISED after implementation:** The three bounded slices below were executed as three dependency-ordered commits in one hosted PR. Keeping one PR avoids temporarily merging a responsive foundation without the requested toggle and keeps the final review focused on the single active dashboard boundary. The commit boundaries remain available for review and rollback.

### PR1 — `dashboard responsive foundation`

**Depends on:** `master`.

**Makes true:** The dashboard shell and active content change layout before medium-width intrinsic sizing fails; the table owns its overflow; chart parents remain usable.

**Includes:** shell responsiveness, dashboard grid modes, shrinkable internal rows, responsive pie geometry, local table overflow/semantics/empty row.

**Excludes:** attack-type view switching and broad query-state redesign.

**Proof:** focused component tests, lint, typecheck, browser viewport matrix, keyboard/zoom/overflow checks.

### PR2 — `dashboard attack-type view toggle`

**Depends on:** PR1 merged into `master`.

**Makes true:** The active attack-type panel defaults to the existing bar visualization and can switch to the panel-review pie visualization using the same normalized entries.

**Includes:** local view state, shared entries, responsive pie rendering, accessible text control, toggle tests.

**Excludes:** source-IP toggle, URL persistence, new chart abstraction, new dependency.

**Proof:** component tests demonstrate default bar view, pie selection, shared counts, empty/loading states, keyboard interaction, lint/typecheck, browser switching checks.

### PR3 — `dashboard state and accessibility corrections`

**Depends on:** PR2 merged into `master`.

**Makes true:** The touched dashboard surfaces distinguish failed data from empty data, expose selected control state, and provide stable semantic feedback.

**Includes:** query error/retry presentation at the owning dashboard boundaries, selected time-window semantics, heading/table naming, chart series labeling where needed, stable state layout.

**Excludes:** unrelated page accessibility cleanup and broad ARIA additions without a semantic need.

**Proof:** focused state/accessibility tests, lint/typecheck, browser keyboard/zoom/error/empty checks.

## Phase 0 — Baseline and plan materialization

### Task 0.1 — Verify isolated worktree baseline

**Files:** none.

- [x] Create worktree `C:\Users\froi\.config\superpowers\worktrees\injection-alert-system\dashboard-responsive-foundation` from `master`.
- [ ] Run `npm ci` in `frontend`.
- [ ] Run the existing focused dashboard tests before editing.
- [ ] Record any baseline failures as pre-existing.

**Commands:**

```powershell
cd frontend
npm ci
npx vitest run --pool=threads components/dashboard/RecentAlertsTable.test.tsx components/dashboard/TimelineChart.test.tsx components/layout/Sidebar.test.tsx
```

**Expected outcome:** Clean dependency setup and a known baseline; no production behavior changed.

### Task 0.2 — Commit the approved design and plan

**Files:**

- `docs/superpowers/specs/2026-08-12-dashboard-responsive-toggle-design.md`
- `docs/superpowers/plans/2026-08-12-dashboard-responsive-toggle.md`

- [x] Write the design record.
- [x] Write this implementation plan.
- [ ] Review both documents against the live `master` source before the first code commit.
- [ ] Commit the plan/design only if they remain accurate after baseline inspection.

**Expected outcome:** The plan is durable and any change in assumptions is recorded before implementation.

## PR1 Phase — Responsive dashboard foundation

### Task 1.1 — Define responsive shell behavior with tests first

**Files:**

- Modify: `frontend/components/layout/Sidebar.tsx`
- Modify: `frontend/components/layout/TopBar.tsx`
- Modify: `frontend/components/layout/Sidebar.test.tsx`
- Create or modify: `frontend/components/layout/TopBar.test.tsx`

- [ ] Add focused tests for the mobile navigation trigger, accessible dialog labeling, and preserved desktop navigation.
- [ ] Run the tests and verify the new assertions fail for the expected missing behavior.
- [ ] Reuse the existing Radix Dialog dependency to add a narrow-screen navigation surface.
- [ ] Keep the desktop sidebar visible only at the wide shell breakpoint and keep navigation content owned by the sidebar boundary.
- [ ] Make the top bar title/status/search groups shrinkable and give the search control responsive width without removing its accessible name.
- [ ] Run the focused tests and verify they pass.

**Expected outcome:** Narrow layouts retain discoverable navigation and the top bar does not require the fixed desktop width.

### Task 1.2 — Define dashboard grid and intrinsic-size behavior with tests where useful

**Files:**

- Modify: `frontend/app/(dashboard)/layout.tsx`
- Modify: `frontend/app/(dashboard)/dashboard/page.tsx`
- Modify: `frontend/components/dashboard/MLConfidenceBands.tsx`
- Modify: `frontend/components/dashboard/MLEnforcementMap.tsx`
- Modify: `frontend/components/dashboard/TopTargetedPaths.tsx`

- [ ] Add or update focused assertions for stable semantic labels and responsive class ownership where component tests exist.
- [ ] Run the new assertions and verify the intended behavior is not already present.
- [ ] Reduce main/page edge padding at narrow widths while preserving desktop spacing.
- [ ] Replace fixed six-column metrics with one/medium/wide modes.
- [ ] Replace fixed four-column distributions with one/medium/wide modes.
- [ ] Add `min-w-0` and `minmax(0, ...)` only at the rows that currently retain unsafe intrinsic minimums.
- [ ] Preserve readable labels and numeric columns without changing confidence thresholds or action semantics.
- [ ] Remove avoidable time-window remount keys if they reset local visualization state.
- [ ] Run focused tests and inspect the diff for unrelated styling changes.

**Expected outcome:** The dashboard changes structure before content compression becomes severe.

### Task 1.3 — Make chart geometry and table overflow responsive

**Files:**

- Modify: `frontend/components/dashboard/AttackTypePanel.tsx`
- Modify: `frontend/components/dashboard/TopSourceIPs.tsx`
- Modify: `frontend/components/dashboard/RecentAlertsTable.tsx`
- Modify: `frontend/components/dashboard/RecentAlertsTable.test.tsx`

- [ ] Add a failing empty-table/accessible-name assertion.
- [ ] Run it and verify it fails for the current blank table behavior.
- [ ] Preserve definite chart parent heights while changing pie radii to responsive percentage geometry.
- [ ] Add a local table overflow region with an accessible name.
- [ ] Use a meaningful heading element for the table title and associate it with the table.
- [ ] Render a clear empty row when there are no alerts.
- [ ] Run focused table/chart tests and verify they pass.

**Expected outcome:** Pie and table content remain available when their cards become narrower.

### Task 1.4 — Validate PR1 and review the diff

- [ ] Run `git diff --check`.
- [ ] Run focused Vitest tests.
- [ ] Run `npm run lint`.
- [ ] Run `npm run typecheck`.
- [ ] Run `npm run build` if dependencies and environment permit.
- [ ] Run the browser viewport matrix if the dashboard can start with the available auth/mock setup.
- [ ] Classify every result as `PASS`, `FAIL`, `NOT_RUN`, `BLOCKED`, or `UNRELATED_FAILURE`.
- [ ] Review the complete diff and remove unrelated changes.
- [ ] Commit PR1 by coherent behavior, not by file count.
- [ ] Push, open PR1, verify checks, merge into `master`, and update this plan.

## PR2 Phase — Attack-type bar/pie toggle

### Task 2.1 — Define normalized entries and toggle behavior with tests first

**Files:**

- Modify: `frontend/components/dashboard/AttackTypePanel.tsx`
- Create: `frontend/components/dashboard/AttackTypePanel.test.tsx`

- [ ] Mock only the Recharts rendering boundary as needed by existing test conventions.
- [ ] Add failing tests for bar-default behavior, pie selection, shared counts/labels, and selected-state semantics.
- [ ] Run the tests and verify they fail because the toggle does not exist.
- [ ] Add one local ordered-entry transformation used by both views.
- [ ] Keep the master bar view as the default.
- [ ] Integrate the panel-review pie rendering with responsive radius values.
- [ ] Add labeled native buttons with `type="button"`, selected state, and focus-visible styling.
- [ ] Keep loading and empty states structurally stable.
- [ ] Run the focused tests and verify they pass.

**Expected outcome:** One query result and one normalized view model drive both chart modes without refetching.

### Task 2.2 — Validate PR2 behavior

- [ ] Run the new `AttackTypePanel` tests in isolation.
- [ ] Run the dashboard component test subset.
- [ ] Run lint and typecheck.
- [ ] Use Playwright or an equivalent browser check to switch views with mouse and keyboard.
- [ ] Verify the selected view survives ordinary re-renders and does not trigger a network request.
- [ ] Review the diff for duplicated transformations or chart abstractions.
- [ ] Commit PR2, push, open PR2, verify checks, merge into `master`, and update this plan.

## PR3 Phase — Focused state and accessibility corrections

### Task 3.1 — Add failing tests for query errors and selected states

**Files:**

- Modify: `frontend/app/(dashboard)/dashboard/page.tsx`
- Modify: `frontend/components/ui/StateViews.tsx`
- Modify: affected dashboard component tests.

- [ ] Add tests showing that stats and alerts failures are not rendered as successful empty data.
- [ ] Add tests for selected time-window semantics and button type.
- [ ] Run them and confirm expected failures.

### Task 3.2 — Implement the smallest state/accessibility fix

- [ ] Use the existing `ErrorState` and query retry functions at the owning dashboard boundaries.
- [ ] Keep cached successful content visible during background refetch when available.
- [ ] Add selected-state semantics to time-window controls.
- [ ] Use native headings and table naming where the content is actually a section.
- [ ] Add only necessary status/alert semantics; do not blanket the dashboard with ARIA.
- [ ] Run focused tests and verify they pass.

### Task 3.3 — Final validation and integration

- [ ] Run `git diff --check`.
- [ ] Run focused dashboard tests.
- [ ] Run `npm run lint`.
- [ ] Run `npm run typecheck`.
- [ ] Run `npm run build`.
- [ ] Run the available browser/accessibility checks.
- [ ] Review the full PR3 diff.
- [ ] Commit, push, open PR3, verify checks, merge into `master`, and update the plan.
- [ ] Re-check the merged `master` worktree and final repository status.

## Final completion gate

- [ ] The single hosted PR containing the three dependency-ordered slices is merged.
- [ ] The final plan records any `REVISED`, `REJECTED`, `DEFERRED`, or `NOT_RUN` items.
- [ ] No API/backend/database/dependency changes were introduced.
- [ ] Responsive behavior was actually inspected or explicitly marked `NOT_RUN`.
- [ ] Keyboard and selected-state behavior was verified.
- [ ] The working tree is clean.

## Execution record

- `CONFIRMED` — `master` was the implementation base; `panel-review` supplied only the existing pie presentation reference.
- `CONFIRMED` — one alerts query and one local normalized attack-type entry list drive both visualization modes.
- `CONFIRMED` — no new npm dependencies, API changes, backend changes, or persisted/global view state were required.
- `REVISED` — PR1/PR2/PR3 remain separate commit-level slices inside one hosted PR because of their direct dependency chain.
- `BLOCKED` — `npm run build` compiled and typechecked but page-data collection requires `AUTH_SECRET` or `NEXTAUTH_SECRET`, which is not present in the isolated worktree; no credential was copied or exposed.
- `NOT_RUN` — authenticated browser viewport and production dashboard interaction checks were not run because the isolated worktree lacks the required auth runtime secret/session setup.
- `BLOCKED` — branch push succeeded, but both `gh pr create` (GraphQL) and the REST pull-request endpoint returned `401 Bad credentials`; no hosted PR or merge was claimed.
