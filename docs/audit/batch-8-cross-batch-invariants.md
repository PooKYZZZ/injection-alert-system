# Batch 8 Cross-Batch Invariant Audit

## 1. Batch summary

### What this batch is supposed to do
Batch 8 is a final cross-batch consistency gate. It should verify that the full path `Browser -> Next.js BFF route -> BFF client -> FastAPI route -> use case -> repository` remains behaviorally consistent after all prior batch edits, with no contract drift between backend, frontend, and tests.

### Why this is risky
This is high risk because this branch introduced cross-layer contract changes (new `action_taken` mutation path, triage semantics around `new`, ML health presentation/view-model extraction, and auth/error mapping changes). Any mismatch here can pass local tests while still breaking runtime behavior or producing misleading UX.

### Main files (contract-critical)
- `web_app/presentation/api/routes.py`
- `web_app/presentation/schemas/schemas.py`
- `web_app/domain/interfaces.py`
- `frontend/app/api/alerts/[id]/action/route.ts`
- `frontend/lib/bff-client.ts`
- `frontend/features/alerts/queries.ts`

### Supporting files (integration/UX/test evidence)
- `frontend/components/ui/ActionLabel.tsx`
- `frontend/components/layout/AlertsNavItem.tsx`
- `frontend/components/layout/Sidebar.tsx`
- `frontend/components/layout/TopBar.tsx`
- `frontend/auth.ts`
- `frontend/app/(auth)/login/page.tsx`
- `frontend/components/ml-health/MLHealthWorkspace.tsx`
- `frontend/components/ml-health/MLHealthWorkspaceViewModel.ts`
- `tests/integration/test_api.py`
- `frontend/app/api/bff-routes.test.ts`
- `frontend/lib/bff-client.test.ts`

### Prior batches this depends on
- Depends on Batches 1-7 (all prior branch changes), especially:
  - Backend route/schema/interface additions for alert action updates.
  - BFF normalization and upstream error mapping behavior.
  - Frontend mutation/query behavior and auth UX.
  - ML Health UI/view-model extraction and truthfulness constraints.
  - Test-suite updates intended to lock those contracts.

## 2. Files audited
- `web_app/presentation/api/routes.py`
- `web_app/presentation/schemas/schemas.py`
- `web_app/domain/interfaces.py`
- `frontend/app/api/alerts/[id]/action/route.ts`
- `frontend/lib/bff-client.ts`
- `frontend/features/alerts/queries.ts`
- `frontend/components/ui/ActionLabel.tsx`
- `frontend/components/layout/AlertsNavItem.tsx`
- `frontend/components/layout/Sidebar.tsx`
- `frontend/components/layout/TopBar.tsx`
- `frontend/auth.ts`
- `frontend/app/(auth)/login/page.tsx`
- `frontend/components/ml-health/MLHealthWorkspace.tsx`
- `frontend/components/ml-health/MLHealthWorkspaceViewModel.ts`
- `tests/integration/test_api.py`
- `frontend/app/api/bff-routes.test.ts`
- `frontend/lib/bff-client.test.ts`

## 3. Findings

### F1 (HIGH): Test contract contradicts BFF auth-failure contract (triage path)
- Evidence:
  - `frontend/lib/bff-client.ts:734` and `frontend/lib/bff-client.ts:737` map upstream `401/403` to status `500` with `INTERNAL_SERVICE_AUTH_FAILED`.
  - `frontend/app/api/bff-routes.test.ts:553` and `frontend/app/api/bff-routes.test.ts:557` assert triage path behavior for status `401` + `INTERNAL_SERVICE_AUTH_FAILED`.
- Why this is a cross-batch contradiction:
  - The centralized BFF contract says internal service auth failures are server faults (`500`), but route-suite expectations still encode a `401` shape in at least one path.
  - This weakens branch-wide auth invariants and can hide regressions by validating impossible combinations.

### F2 (HIGH): ML-health truthfulness rule contradicted by route test fixture
- Evidence:
  - `frontend/lib/bff-client.ts:445`, `frontend/lib/bff-client.ts:454`, and `frontend/lib/bff-client.ts:486` enforce: if `drift_score` is unavailable, `drift_status` must be `null` (not `NORMAL`).
  - `frontend/app/api/bff-routes.test.ts:286` and `frontend/app/api/bff-routes.test.ts:287` use `drift_score: null` together with `drift_status: 'NORMAL'` as accepted route contract fixture.
- Why this is a cross-batch contradiction:
  - One batch codifies truthfulness restraint; another test fixture normalizes a non-truthful state as acceptable. This reintroduces ambiguity around ML health meaning.

### F3 (MEDIUM): Action mutation sign-in guidance only covers browser 401, not internal auth failures
- Evidence:
  - `frontend/features/alerts/queries.ts:169` and `frontend/features/alerts/queries.ts:170` only trigger sign-in toast on HTTP `401`.
  - `frontend/lib/bff-client.ts:829` and `frontend/lib/bff-client.ts:832` map upstream internal auth failures to `500`.
  - `frontend/app/api/alerts/[id]/action/route.ts:69` and `frontend/app/api/alerts/[id]/action/route.ts:74` pass BFF status through to browser.
- Risk:
  - When internal service auth fails, UX falls into generic mutation failure without sign-in affordance. This is not necessarily incorrect, but it creates an auth/retry ambiguity in the operator flow.

### F4 (MEDIUM): Action update tests are sparse relative to newly added contract path
- Evidence:
  - Backend integration coverage for action endpoint is limited to missing-alert 404 (`tests/integration/test_api.py:150`).
  - Route suite covers action success/invalid input/auth checks but omits upstream error propagation cases (`frontend/app/api/bff-routes.test.ts:624` onward).
  - BFF-client tests include action 404 and schema-failure cases (`frontend/lib/bff-client.test.ts:247`, `frontend/lib/bff-client.test.ts:263`) but no action-path internal-auth mapping assertion analogous to existing stats assertions.
- Risk:
  - Cross-layer behavior exists, but parity coverage is not robust enough for merge-blocking confidence on this new path.

## 4. Cross-batch contradictions
- Contradiction A: `INTERNAL_SERVICE_AUTH_FAILED` status semantics are inconsistent across BFF contract and triage route tests.
  - BFF contract: server-side/internal fault (`500`).
  - Route test fixture: upstream-like unauthorized (`401`).
- Contradiction B: ML-health drift truthfulness rule (`drift_score null => drift_status null`) conflicts with route test fixture (`drift_status 'NORMAL'` with null score).
- Contradiction C (soft): auth UX path is split.
  - Browser unauthorized session (`401`) drives sign-in toast.
  - Internal service auth failures are mapped to `500` and do not surface sign-in guidance, producing operator-visible inconsistency in failure handling.

## 5. High-risk files in this batch
- `frontend/app/api/bff-routes.test.ts`
- `frontend/lib/bff-client.ts`
- `frontend/features/alerts/queries.ts`
- `frontend/app/api/alerts/[id]/action/route.ts`

## 6. Files that appear disciplined
- `web_app/presentation/api/routes.py`
- `web_app/presentation/schemas/schemas.py`
- `web_app/domain/interfaces.py`
- `frontend/components/ui/ActionLabel.tsx`
- `frontend/components/layout/AlertsNavItem.tsx`
- `frontend/components/layout/TopBar.tsx`
- `frontend/components/ml-health/MLHealthWorkspace.tsx`
- `frontend/components/ml-health/MLHealthWorkspaceViewModel.ts`

Notes on disciplined alignment:
- Backend action endpoint wiring (`route -> request schema -> use case`) is internally coherent.
- Frontend action transport values are consistently derived from centralized contract constants.
- Alert-count labels are explicit (`NEW`, `IN REVIEW`) and tied to explicit triage filters.

## 7. Batch verdict
**Batch 8 verdict: FAIL (merge-blocking for consistency pass).**

Rationale:
- Two high-severity cross-batch contradictions remain in tests versus normalized behavior (auth-status semantics and ML-health truthfulness semantics).
- Additional medium-risk coverage/UX consistency gaps remain on the new action mutation path.

This is an audit-only verdict for Batch 8 consistency, not the final branch merge verdict.
