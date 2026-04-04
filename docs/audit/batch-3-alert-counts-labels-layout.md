# Batch 3 Audit: User-visible alert count/label semantics and layout/nav impact

## 1. Batch summary

### Pre-audit restatement (required)
- What this batch is supposed to do:
  - Align alert-facing UI semantics across alerts page, dashboard, top/nav badges, and table/card labels.
  - Ensure displayed numbers and status labels (count badges, NEW/IN REVIEW labels, selected counts, totals, card values) map to the correct data meaning.
  - Keep layout/nav presentation from creating misleading mental models.
- Why this batch is risky:
  - It touches multiple independent count surfaces that can look equivalent while being sourced from different queries/scopes.
  - It mixes global totals, filtered totals, page-local counts, and optimistic state transitions in nearby UI regions.
  - It modifies both dashboards and alerts work surfaces, increasing cross-view semantic drift risk.
- Main files:
  - frontend/components/alerts/AlertsTable.tsx
  - frontend/components/layout/TopBar.tsx
  - frontend/components/layout/AlertsNavItem.tsx
  - frontend/components/alerts/FilterBar.tsx
  - frontend/components/dashboard/StatCard.tsx
  - frontend/app/(dashboard)/dashboard/page.tsx
  - frontend/components/dashboard/AlertsTable/AlertsTable.tsx
- Supporting files:
  - frontend/components/alerts/AlertDrawer.tsx
  - frontend/components/alerts/AlertsPageClient.tsx
  - frontend/components/alerts/BulkActionBar.tsx
  - frontend/components/alerts/ct/AlertsPagePortedClient.tsx
  - frontend/components/layout/Sidebar.tsx
  - frontend/components/dashboard/RecentAlertsTable.tsx
- Tests supposed to prove behavior in this batch area:
  - frontend/components/layout/AlertsNavItem.test.tsx
  - frontend/components/alerts/AlertsTable.test.tsx
  - frontend/components/alerts/BulkActionBar.test.tsx
  - frontend/components/dashboard/AlertsTable/AlertsTable.test.tsx
  - Supporting contract tests indirectly relevant:
    - frontend/lib/searchParams.test.ts
    - frontend/lib/bff-client.test.ts
    - frontend/app/api/bff-routes.test.ts

### Focused test execution evidence
- Executed in worktree frontend:
  - npx vitest run --pool=threads "components/layout/AlertsNavItem.test.tsx" "components/alerts/AlertsTable.test.tsx" "components/alerts/BulkActionBar.test.tsx" "components/dashboard/AlertsTable/AlertsTable.test.tsx"
- Result:
  - 1 failed, 13 passed.
  - Failing test: frontend/components/dashboard/AlertsTable/AlertsTable.test.tsx
  - Failure reason: expected rule ID text 942100 no longer rendered.

## 2. Files audited

In-scope files audited deeply:
- frontend/components/alerts/AlertDrawer.tsx
- frontend/components/alerts/AlertsPageClient.tsx
- frontend/components/alerts/AlertsTable.tsx
- frontend/components/alerts/BulkActionBar.tsx
- frontend/components/alerts/FilterBar.tsx
- frontend/components/alerts/ct/AlertsPagePortedClient.tsx
- frontend/components/layout/AlertsNavItem.tsx
- frontend/components/layout/Sidebar.tsx
- frontend/components/layout/TopBar.tsx
- frontend/components/dashboard/AlertsTable/AlertsTable.tsx
- frontend/components/dashboard/RecentAlertsTable.tsx
- frontend/components/dashboard/StatCard.tsx
- frontend/app/(dashboard)/dashboard/page.tsx

Supporting evidence files consulted for semantic verification:
- frontend/lib/searchParams.ts
- frontend/features/alerts/queries.ts
- frontend/features/stats/types.ts
- frontend/features/stats/queries.ts
- frontend/lib/bff-client.ts
- frontend/components/ui/TriageBadge.tsx
- frontend/components/layout/SidebarNavItem.tsx
- frontend/app/(dashboard)/alerts/page.tsx

## 3. Findings

### Critical

1. High Alerts card is semantically miswired and compares unlike metrics.
- Files:
  - frontend/app/(dashboard)/dashboard/page.tsx
- Details:
  - Card label is High alerts.
  - Card value uses stats.actionable_alerts.
  - Delta baseline uses stats.prev_high_alert_count.
- Risk:
  - This compares current actionable alerts against previous high alerts, which are not guaranteed to represent the same definition.
  - Analyst decision-making can be wrong because trend arrows and deltas imply a like-for-like metric.
- Evidence:
  - actionable_alerts and high_alert_count are distinct fields in frontend/features/stats/types.ts and are populated separately in frontend/lib/bff-client.ts.

2. Dashboard Alerts table evidence context was removed without updating proving tests.
- Files:
  - frontend/components/dashboard/AlertsTable/AlertsTable.tsx
  - frontend/components/dashboard/AlertsTable/AlertsTable.test.tsx
- Details:
  - Rule IDs column/rendering removed from table.
  - Existing test still asserts rule ID visibility and fails.
- Risk:
  - Merge-blocking test failure in targeted batch evidence.
  - Also removes user-visible WAF evidence detail from a surface previously expected to include it.
- Evidence:
  - Focused run produced a failing test on missing 942100.

### High

3. Top bar NEW and IN REVIEW counters are global totals while nearby table totals are filtered/page-scoped, with no explicit scope labeling.
- Files:
  - frontend/components/layout/TopBar.tsx
  - frontend/components/alerts/AlertsTable.tsx
  - frontend/components/alerts/FilterBar.tsx
- Details:
  - NEW/IN REVIEW counts come from useAlertsFromFilters queries filtered only by triage status, not by current alerts page filter/search/window.
  - Alerts table footer uses filtered total for current query.
  - FilterBar and table present local filtering context, but top bar counters do not disclose they are global.
- Risk:
  - Nearby numbers imply same scope when they are different.
  - Users may infer filter malfunction or stale data.

4. Sidebar Alerts badge is a default global total, likely conflicting with alerts page counters and filter context.
- Files:
  - frontend/components/layout/AlertsNavItem.tsx
  - frontend/lib/searchParams.ts
  - frontend/components/layout/TopBar.tsx
- Details:
  - Badge uses DEFAULT_ALERT_FILTERS only (page 1, pageSize 20, sort timestamp desc), relying on data.total.
  - No explicit label indicates scope (global all-triage/all-status).
- Risk:
  - Nav badge can disagree with NEW/IN REVIEW or filtered table totals, reinforcing mixed-meaning number confusion.

5. Row click auto-triage changes status counts as a side effect of opening an alert.
- Files:
  - frontend/components/alerts/AlertsTable.tsx
  - frontend/components/layout/TopBar.tsx
  - frontend/features/alerts/queries.ts
- Details:
  - Clicking a row with triage new/null triggers triage mutation to in_review before user explicitly triages.
  - Mutation optimistically updates all alert query caches.
- Risk:
  - NEW and IN REVIEW counters can change immediately due to navigation behavior, not analyst decision.
  - This is a count semantics hazard and can make labels look unstable.

### Medium

6. StatCard delta color logic regresses to positive coloring for non-zero deltas when no explicit valueColor is supplied.
- Files:
  - frontend/components/dashboard/StatCard.tsx
- Details:
  - The non-flash branch resolves delta-present path to text-emerald-400 regardless of delta direction when valueColor is absent.
- Risk:
  - Trend color semantics can communicate good movement when movement is actually bad.
  - For count cards, this is directly user-visible interpretation risk.

7. Dashboard Alerts table footer says Showing N loaded records, which can be read as total count.
- Files:
  - frontend/components/dashboard/AlertsTable/AlertsTable.tsx
- Details:
  - Footer shows alerts.length only, not full dataset total.
- Risk:
  - On paged/filtered data, users may interpret N as total alerts.
  - This is a count-label clarity issue.

8. FilterBar confidence semantics changed from multi-select confidence_level to single severity selector labeled Confidence.
- Files:
  - frontend/components/alerts/FilterBar.tsx
  - frontend/components/alerts/AlertsTable.tsx
- Details:
  - Prior confidence pill behavior removed; now single select writes severity.
  - Label says Confidence while query key is severity.
- Risk:
  - Potentially acceptable if severity is strictly confidence band, but semantics are less explicit and changed interaction model.
  - Nearby counts can look inconsistent if users expect multi-level inclusion logic.

9. Recent alerts table uses selectable checkboxes without corresponding selection count or action affordance.
- Files:
  - frontend/components/dashboard/RecentAlertsTable.tsx
- Details:
  - Table renders row/select-all checkboxes in preview surface but no selected count, no bulk action, and no persisted state.
- Risk:
  - Encourages a selection mental model without count feedback or effect.
  - Not a direct data bug, but a layout semantics confusion vector.

### Low

10. Empty placeholder file introduced in batch.
- Files:
  - frontend/components/alerts/ct/AlertsPagePortedClient.tsx
- Details:
  - File exists but is empty.
- Risk:
  - Increases ambiguity about intended ownership/path for alerts page implementation.

### Per-file observations (completeness)
- frontend/components/alerts/AlertDrawer.tsx
  - No direct count-total computation issues found.
  - Triage/action labels map consistently to status/action states.
- frontend/components/alerts/AlertsPageClient.tsx
  - Selection and active alert wiring are coherent.
- frontend/components/alerts/BulkActionBar.tsx
  - Selected count semantics are correct for current selection set.
  - Summary string is operation count, not dataset count (acceptable).
- frontend/components/layout/Sidebar.tsx
  - Layout changes mainly logout modal; no direct count computation change.

## 4. High-risk files in this batch

- frontend/app/(dashboard)/dashboard/page.tsx
  - High Alerts card metric mismatch (actionable_alerts vs prev_high_alert_count).
- frontend/components/layout/TopBar.tsx
  - NEW/IN REVIEW global counters presented adjacent to local filtered context.
- frontend/components/layout/AlertsNavItem.tsx
  - Sidebar badge global total with no scope clarification.
- frontend/components/alerts/AlertsTable.tsx
  - Auto-triage side effect on click can shift count labels immediately.
- frontend/components/dashboard/AlertsTable/AlertsTable.tsx
  - Removed rule ID signal; test coverage indicates behavioral regression.

## 5. Files that appear disciplined

- frontend/components/alerts/AlertDrawer.tsx
  - Clear status/action label mapping and optimistic rollback handling.
- frontend/components/alerts/AlertsPageClient.tsx
  - Selection state and drawer state responsibilities are separated cleanly.
- frontend/components/alerts/BulkActionBar.tsx
  - Concurrency-limited batching and deterministic success/fail summary logic.
- frontend/components/layout/Sidebar.tsx
  - No new count logic; nav composition remains straightforward.

## 6. Questions or ambiguities needing cross-batch verification

1. Should High alerts display stats.high_alert_count (not stats.actionable_alerts), and should its delta compare to prev_high_alert_count only?
2. Should NEW/IN REVIEW in top bar follow current alerts page filters/search/window, or are they intended to remain global backlog indicators?
3. Should sidebar Alerts badge represent global all-alerts total, filtered total, or actionable backlog only?
4. Is auto-transition new/null -> in_review on row open intentional product behavior, or should status change require explicit analyst action?
5. Is removal of dashboard rule IDs intentional despite existing test expectation and potential loss of at-a-glance evidence context?
6. Is severity intended to be synonymous with confidence bands on alerts page after removing confidence_level multi-select?
7. Should Recent alerts preview include selection controls if no selected-count or bulk action semantics are provided?

## 7. Batch verdict

Fail (merge-blocking for this batch).

Reasons:
- Semantic mismatch in dashboard High alerts metric/delta pairing.
- Verified failing batch-related test in dashboard alerts table.
- Multiple high-risk mixed-scope count surfaces (top bar, nav badge, table totals) without explicit scope signaling.
- Side-effect triage transition on row click that can silently alter visible status counts.
