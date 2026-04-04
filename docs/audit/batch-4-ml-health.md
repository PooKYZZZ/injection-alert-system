# Batch 4 Audit - ML Health Rewrite, Page Composition, and View-Model Split

## 1. Batch summary

### Pre-audit restatement

What this batch is supposed to do:
- Replace the monolithic ML Health page with a composed workspace structure.
- Split UI into overview and diagnostics sections.
- Move derivation/formatting logic into a dedicated view-model helper.
- Remove previously simulated/fake-looking ML health elements and keep labels grounded to snapshot data.
- Keep supporting dashboard visual components coherent with confidence/status semantics.

Why this batch is risky:
- It is a UX-trust surface: ML health claims can mislead operators if labels imply live, real-time, or backend-grounded values that are actually derived/fabricated.
- It mixes broad UI decomposition with global styling changes, creating non-local blast radius.
- Refactor theater risk is high: complexity can be moved from one giant page into giant CSS and helper modules without real simplification.
- The view-model can become a pseudo-domain layer with policy semantics hardcoded in frontend.

Main files in this batch:
- frontend/app/(dashboard)/ml-health/page.tsx
- frontend/components/ml-health/MLHealthWorkspace.tsx
- frontend/components/ml-health/MLHealthWorkspaceViewModel.ts
- frontend/components/ml-health/MLHealthOverviewSection.tsx
- frontend/components/ml-health/MLHealthDiagnosticsSection.tsx

Supporting files in this batch:
- frontend/components/ml-health/MLHealthWorkspace.module.css
- frontend/components/dashboard/MLConfidenceBands.tsx
- frontend/components/dashboard/TimelineChart.tsx
- frontend/app/globals.css

Tests supposed to prove behavior:
- frontend/app/(dashboard)/ml-health/page.test.tsx
- frontend/components/ml-health/MLHealthWorkspaceViewModel.test.ts
- frontend/components/dashboard/TimelineChart.test.tsx

### Scope and change shape (vs master)
- Changed in this batch: page wrapper, workspace, workspace CSS, page test, timeline chart, confidence band color token, global CSS.
- Not changed in this batch but audited as in-scope dependencies: MLHealthOverviewSection, MLHealthDiagnosticsSection, MLHealthWorkspaceViewModel.

## 2. Files audited

- frontend/app/(dashboard)/ml-health/page.tsx
- frontend/components/ml-health/MLHealthWorkspace.tsx
- frontend/components/ml-health/MLHealthWorkspace.module.css
- frontend/components/ml-health/MLHealthDiagnosticsSection.tsx
- frontend/components/ml-health/MLHealthOverviewSection.tsx
- frontend/components/ml-health/MLHealthWorkspaceViewModel.ts
- frontend/components/dashboard/MLConfidenceBands.tsx
- frontend/components/dashboard/TimelineChart.tsx
- frontend/app/globals.css
- frontend/app/(dashboard)/ml-health/page.test.tsx
- frontend/components/ml-health/MLHealthWorkspaceViewModel.test.ts
- frontend/components/dashboard/TimelineChart.test.tsx

## 3. Findings

### High

1. Misleading derivation claim: UI says policy bands are derived from traffic volume, but implementation does not use traffic volume at all.
- Evidence:
  - frontend/components/ml-health/MLHealthOverviewSection.tsx:122
  - frontend/components/ml-health/MLHealthDiagnosticsSection.tsx:242
  - frontend/components/ml-health/MLHealthWorkspaceViewModel.ts:118-137
- Detail:
  - Both sections render: "Derived from configured thresholds and current traffic volume."
  - `buildPolicyBands` only computes static ranges from `thresholds.low` and `thresholds.high`; no use of `traffic_processed`.
- Risk:
  - Operator-facing provenance is incorrect; it overstates real-time coupling and can distort trust in ML policy posture.

2. "Live Serving" badge is a strong real-time claim backed only by a snapshot status field.
- Evidence:
  - frontend/components/ml-health/MLHealthOverviewSection.tsx:52-54
  - frontend/components/ml-health/MLHealthWorkspaceViewModel.ts:210-211
- Detail:
  - UI emits "● Live Serving" and "Derived from current health snapshot" while window/granularity are hardcoded (`Reported window`, `Snapshot-based`).
  - No freshness timestamp, heartbeat age, or staleness guard from backend is shown in this surface.
- Risk:
  - This is exactly the kind of health UI overclaim that can hide stale data.

### Medium

3. Refactor theater signal: decomposition reduced page file size, but style complexity remains bloated and largely dead.
- Evidence:
  - frontend/components/ml-health/MLHealthWorkspace.module.css:1-896
  - Unused selector examples still present for removed UI: search and icon controls at lines 80, 107; old secondary/risk/activity/calibration layouts around 280, 407, 426-447, 712.
  - Static analysis in this audit found 140 class selectors, 62 referenced by current ML health TSX, 78 unused.
- Detail:
  - Major chunks of CSS survive from removed fake sections (risk tables, activity logs, search controls, policy bars, old calibration cards).
- Risk:
  - Maintains cognitive load and encourages accidental resurrection of misleading UI fragments.

4. View-model contains hidden policy/quality thresholds that are frontend-owned and weakly disclosed.
- Evidence:
  - frontend/components/ml-health/MLHealthWorkspaceViewModel.ts:147 (`isElevated: value < 0.89`)
  - frontend/components/ml-health/MLHealthWorkspaceViewModel.ts:191-198 (ECE preferred range hardcoded at 0.050)
  - frontend/components/ml-health/MLHealthOverviewSection.tsx:74 (drift threshold text hardcoded 0.050)
- Detail:
  - These constants drive status language (`review/stable`, calibration assessment) but are not sourced from backend metadata.
- Risk:
  - Drift between backend policy and frontend presentation can silently create contradictory operator guidance.

5. Global CSS scope creep inside an ML-health-focused batch raises cross-page regression risk.
- Evidence:
  - frontend/app/globals.css:6-55, 86-131
- Detail:
  - Broad theme token shifts and global scrollbar styling are introduced here, plus `zoom: 1` on body.
- Risk:
  - Non-local UI regressions become possible outside ML health; this is not tightly scoped to the batch objective.

### Low

6. Policy band model ignores `medium` threshold for range construction, yet UI presents low/medium/high threshold labels.
- Evidence:
  - frontend/components/ml-health/MLHealthWorkspaceViewModel.ts:118-137 (bands only use low/high)
  - frontend/components/ml-health/MLHealthWorkspaceViewModel.ts:220-223 (all three threshold labels exposed)
  - frontend/components/ml-health/MLHealthDiagnosticsSection.tsx:243 (renders low/medium/high labels)
- Detail:
  - The rendered footnote implies three-threshold semantics, but range construction is effectively two-cutoff.
- Risk:
  - Potential semantic mismatch if backend meaning of `medium` diverges from simple interpolation.

7. Test strategy favors copy-level assertions and omission checks, not truthfulness guarantees.
- Evidence:
  - frontend/app/(dashboard)/ml-health/page.test.tsx:84-92
- Detail:
  - The page test strongly validates that old widgets are gone, but does not assert provenance correctness for "Live Serving" or policy derivation language.
- Risk:
  - Merge can pass while still shipping misleading health claims.

## 4. High-risk files in this batch

- frontend/components/ml-health/MLHealthOverviewSection.tsx
- frontend/components/ml-health/MLHealthDiagnosticsSection.tsx
- frontend/components/ml-health/MLHealthWorkspaceViewModel.ts
- frontend/components/ml-health/MLHealthWorkspace.module.css
- frontend/app/globals.css

## 5. Files that appear disciplined

- frontend/app/(dashboard)/ml-health/page.tsx
  - Clean composition boundary; thin page wrapper with no in-page orchestration theater.
- frontend/components/ml-health/MLHealthWorkspace.tsx
  - Keeps fetch/error/loading orchestration localized and simple.
- frontend/components/dashboard/TimelineChart.tsx
  - Recent y-axis/reference-line changes are backed by explicit tests in frontend/components/dashboard/TimelineChart.test.tsx.
- frontend/components/dashboard/MLConfidenceBands.tsx
  - Token change aligns high band color with severity semantics.

## 6. Questions or ambiguities needing cross-batch verification

1. Is there a backend-provided freshness/last-updated field for ML health snapshots that should gate or replace "Live Serving" language?
2. Is `medium` threshold authoritative in backend policy evaluation, or only informational?
3. Are hardcoded frontend constants (`0.89` F1 elevated cutoff, `0.050` ECE/drift messaging) contract-approved anywhere?
4. Was the global theme/scrollbar rewrite intentionally bundled with ML health, or should this be isolated to avoid unrelated regressions?
5. Is there an agreed policy on labeling derived vs backend-grounded values (especially for operator-facing health claims)?

## 7. Batch verdict

Batch 4 is improved structurally but not yet merge-safe for a hostile audit.

Reason:
- The rewrite removes a large amount of obvious synthetic UI, but still contains materially misleading provenance statements and over-assertive health labels.
- Complexity reduction is incomplete; significant dead CSS remains and the view-model still embeds policy-like semantics that are not clearly backend-governed.
- Test coverage is decent for composition and chart rendering, but insufficient for operator-trust assertions and derivation truthfulness.

Current disposition: REJECT for merge in this audit stage (batch-local verdict only; no branch-wide verdict issued).
