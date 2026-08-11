# Dashboard Responsive Layout and Attack-Type View Toggle Design

**Date:** 2026-08-12
**Base:** `master`
**Reference:** `panel-review` is used only as a read-only source for the existing pie-chart implementation.

## Goal

Make the current master dashboard usable at medium and narrow widths and add a local control that switches the attack-type visualization between the existing bar view and the pie-chart view from `panel-review`, without duplicating query or business logic.

## Confirmed repository facts

- `master` is the current default branch and its active `AttackTypePanel` is a horizontal-bar visualization.
- `panel-review` contains the previously implemented Recharts pie visualization.
- The active dashboard already derives attack counts from one `useAlerts` result.
- The dashboard currently retains six metric columns and four distribution columns too far into reduced widths.
- The shell retains a 250px sidebar and a fixed-width top-bar search field.
- The recent-alert table has no local horizontal overflow boundary.
- Existing dependencies include Recharts, TanStack Query, Tailwind CSS v4, Radix Dialog, and the existing testing stack.

## Design

### Responsive shell and content

Keep the existing desktop shell and visual language. At narrower widths, the sidebar becomes a Radix Dialog-based navigation surface with an explicit open button; the desktop sidebar remains unchanged for large screens. The top bar keeps search and theme controls but gives the title/status group and search field shrinkable responsive space.

The dashboard content changes layout modes before intrinsic content becomes unusably narrow:

- metrics: one column by default, three columns at medium widths, six at wide desktop;
- distribution cards: one column by default, two at medium widths, four at wide desktop;
- chart/list rows use shrinkable grid tracks rather than fixed minimums that exceed the card width;
- pie geometry uses responsive radii inside the existing definite-height chart parent;
- the table owns horizontal overflow and retains native table semantics.

### Attack-type visualization toggle

`AttackTypePanel` remains the ownership boundary. It builds one ordered list of `{ label, count }` entries from `countsByLabel`. A local `view` state selects either:

- `bar`, the current master default; or
- `pie`, the panel-review Recharts implementation.

Both views consume the same entries, legend values, ordering, and color map. Switching views does not alter query keys, request parameters, or backend contracts. The control uses text labels, native buttons, selected-state semantics, and visible focus.

### State and accessibility corrections in scope

Only dashboard surfaces touched by this work receive focused state/accessibility improvements:

- query failures remain distinguishable from empty data;
- empty table results have an explanatory row;
- section/table headings use meaningful native elements;
- time-window controls expose selected state and use `type="button"`;
- chart legends and status messages remain understandable without color alone;
- loading dimensions remain stable where practical.

## Alternatives rejected

- A new chart abstraction: existing component ownership is sufficient.
- A global store, URL state, or persisted view preference: the preference is local to one card.
- A new chart library: Recharts already supports both views.
- A full dashboard redesign: the defect is responsive ownership and intrinsic sizing, not the overall visual language.
- Removing important dashboard data on mobile: narrow layouts will stack, scroll, or expose the same information through an accessible navigation path.

## Validation design

- Component tests cover toggle default/selection, shared data, loading/empty states, table empty state, and responsive-shell controls where testable.
- Frontend lint and typecheck run for each implementation slice.
- Focused Vitest runs precede broader frontend checks.
- Browser validation covers 1440px, 1280px, 1024px, 900px, 768px, and 390–430px, plus keyboard focus, zoom, loading, error, empty, zero-value, and many-category states.
- No backend, API, database, dependency, or deployment changes are expected.

## Decision record

**Decision:** Implement on `master`; use `panel-review` only for the pie-chart source.

**Status:** CONFIRMED by user on 2026-08-12.

**Reason:** The current active master visualization is the bar view that the user wants to pair with the previously built pie view.

**Impact:** PRs target `master` in dependency order. The panel-review branch is not modified.
