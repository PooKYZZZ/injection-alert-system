# Batch 5 Test/Contract Audit

## 1. Batch summary

### What this batch is supposed to do
This batch is supposed to prove that cross-layer contracts are stable and enforced across:
- Next.js BFF route handlers
- frontend query/client adapters
- UI contract consumers
- backend integration and unit behaviors

Primary expected proof points:
- auth boundary behavior (`UNAUTHORIZED` for browser session failures, internal auth failure mapping for upstream failures)
- alert/stats/ml-health schema normalization and error propagation
- mutation semantics for triage/action status transitions
- confidence/action contract invariants (`BLOCKED`, `THROTTLED`, `ALLOWED`; threshold semantics)
- backend use-case and model metadata correctness

### Why this batch is risky
This batch is high risk because these tests define and lock transport semantics between browser, BFF, and backend. Weak or incorrect tests here can allow:
- silent contract drift across layers
- wrong status-code semantics in production incidents
- UI behavior regressions while tests still pass
- false confidence from vacuous assertions and over-mocking

### Main files
Main contract-driving files in this batch:
- frontend/app/api/bff-routes.test.ts
- frontend/lib/bff-client.test.ts
- frontend/features/alerts/queries.test.tsx
- tests/integration/test_api.py
- tests/unit/test_eval_metadata.py

### Supporting files
Supporting behavior/consumer tests:
- frontend/app/providers.test.tsx
- frontend/components/alerts/AlertsTable.test.tsx
- frontend/components/dashboard/TimelineChart.test.tsx
- frontend/components/layout/AlertsNavItem.test.tsx
- frontend/components/ml-health/MLHealthWorkspaceViewModel.test.ts
- frontend/components/SignInToast.test.tsx
- tests/unit/test_update_alert_action_use_case.py
- tests/unit/test_model_service.py

### Which tests are supposed to prove behavior
- `bff-routes.test.ts` should prove route-level auth gating, status propagation, and request validation semantics.
- `bff-client.test.ts` should prove transport normalization from FastAPI to frontend contracts.
- `queries.test.tsx` should prove mutation error handling/cache semantics and auth UX behavior.
- `test_api.py` should prove end-to-end API contract behavior for predict/alerts/feedback/action routes.
- `test_eval_metadata.py` and `test_model_service.py` should prove ML metadata and model service invariants.

## 2. Files audited
- frontend/app/api/bff-routes.test.ts
- frontend/app/providers.test.tsx
- frontend/components/alerts/AlertsTable.test.tsx
- frontend/components/dashboard/TimelineChart.test.tsx
- frontend/components/layout/AlertsNavItem.test.tsx
- frontend/components/ml-health/MLHealthWorkspaceViewModel.test.ts
- frontend/components/SignInToast.test.tsx
- frontend/features/alerts/queries.test.tsx
- frontend/lib/bff-client.test.ts
- tests/integration/test_api.py
- tests/unit/test_update_alert_action_use_case.py
- tests/unit/test_eval_metadata.py
- tests/unit/test_model_service.py

## 3. Findings

### Critical
1. `frontend/app/api/bff-routes.test.ts` encodes wrong triage auth-failure HTTP semantics.
- Evidence: `triage PATCH propagates 401 from upstream as INTERNAL_SERVICE_AUTH_FAILED` asserts `response.status === 401`.
- Reference: frontend/app/api/bff-routes.test.ts:553, frontend/app/api/bff-routes.test.ts:575
- Conflict: BFF client maps upstream `401/403` to `500 INTERNAL_SERVICE_AUTH_FAILED` for internal service auth failures.
- Reference: frontend/lib/bff-client.ts:547, frontend/lib/bff-client.ts:734, frontend/lib/bff-client.ts:829
- Risk: Route test can pass while asserting an impossible or undesired status contract, masking true cross-layer semantics.

### High
2. `tests/unit/test_eval_metadata.py` contains vacuous assertions and swallowed failures.
- Evidence: assertions with `or True`, broad `try/except` that `pass` on type/value errors.
- Reference: tests/unit/test_eval_metadata.py:198, tests/unit/test_eval_metadata.py:199, tests/unit/test_eval_metadata.py:200, tests/unit/test_eval_metadata.py:211, tests/unit/test_eval_metadata.py:212, tests/unit/test_eval_metadata.py:213
- Risk: tests pass regardless of meaningful validation failures, providing false confidence for metadata parsing.

3. `tests/integration/test_api.py` includes a conditional integration assertion that can pass without proving behavior.
- Evidence: feedback route assertion guarded by `if alerts:`; no failure when no alerts exist.
- Reference: tests/integration/test_api.py:128
- Risk: test can go green without ever exercising `/api/feedback`, which is merge-blocking blind spot for contract verification.

### Medium
4. `frontend/features/alerts/queries.test.tsx` is too narrow for mutation contract safety.
- Evidence: only one test exists and it covers one `401` path.
- Reference: frontend/features/alerts/queries.test.tsx:31, frontend/features/alerts/queries.test.tsx:42
- Missing proof: optimistic update correctness, rollback on non-401 errors, invalidation behavior on success, handling of `403/5xx`, and duplicate mutation behavior.

5. `frontend/app/api/bff-routes.test.ts` duplicates auth assertions without increasing behavioral coverage.
- Evidence: repeated unauthorized tests under both “applies existing session auth pattern” and “rejects unauthenticated before calling BFF client”.
- Reference: frontend/app/api/bff-routes.test.ts:30, frontend/app/api/bff-routes.test.ts:379, frontend/app/api/bff-routes.test.ts:390, frontend/app/api/bff-routes.test.ts:403
- Risk: larger test surface but limited incremental signal, increasing maintenance noise.

6. ID validation contract is only partially proven across layers.
- Evidence: route tests validate `NaN`, empty, `undefined` but do not assert `0`/negative semantics at route level.
- Reference: frontend/app/api/bff-routes.test.ts:173
- Cross-layer nuance: route accepts any integer (`Number.isInteger`), while client-level parser rejects non-positive IDs.
- Reference: frontend/app/api/alerts/[id]/route.ts:18, frontend/app/api/alerts/[id]/triage/route.ts:18, frontend/app/api/alerts/[id]/action/route.ts:25, frontend/lib/bff-client.ts:193
- Risk: semantics can drift (or break unexpectedly) without direct contract proof.

7. `frontend/app/providers.test.tsx` asserts a historical implementation detail instead of durable behavior.
- Evidence: spying on global `addEventListener` and asserting no `action-retry-success` listener.
- Reference: frontend/app/providers.test.tsx:18, frontend/app/providers.test.tsx:19, frontend/app/providers.test.tsx:30
- Risk: brittle to harmless internal refactors; weak product-value assertion.

8. `frontend/components/layout/AlertsNavItem.test.tsx` sets up unused hook mock path (`useAlerts`) and validates only one happy path.
- Reference: frontend/components/layout/AlertsNavItem.test.tsx:4, frontend/components/layout/AlertsNavItem.test.tsx:19, frontend/components/layout/AlertsNavItem.test.tsx:28
- Risk: dead setup suggests test drift; missing edge cases for undefined totals/loading/error badge behavior.

9. `frontend/components/SignInToast.test.tsx` misses fallback redirect semantics.
- Evidence: test verifies `window.open` success path only.
- Reference: frontend/components/SignInToast.test.tsx:21
- Implementation has fallback `window.location.assign` when `window.open` fails.
- Reference: frontend/components/SignInToast.tsx:51, frontend/components/SignInToast.tsx:53
- Risk: critical auth UX fallback could regress undetected.

10. `frontend/components/alerts/AlertsTable.test.tsx` covers only “new/null -> in_review” transition and query-param normalization.
- Missing proof: non-new triage rows should not mutate; row/checkbox click interaction boundaries; pagination/sort side effects.
- Reference: frontend/components/alerts/AlertsTable.test.tsx:104, frontend/components/alerts/AlertsTable.test.tsx:145

11. `frontend/components/dashboard/TimelineChart.test.tsx` is mostly structural and prop-level with heavy chart mocking.
- Missing proof: `hasEvents` override and `consistencyWarning` branch behavior with real rendered states under realistic data transitions.
- Reference: frontend/components/dashboard/TimelineChart.test.tsx:77

### Low
12. `tests/unit/test_update_alert_action_use_case.py` is clean but minimal.
- Missing proof: enforcement of exact accepted values including explicit `ALLOWED` behavior as product contract sentinel.

13. `tests/unit/test_model_service.py` validates key invariants but omits negative-path metadata failure assertions and inference error propagation checks.

## 4. High-risk files in this batch
- frontend/app/api/bff-routes.test.ts
- tests/unit/test_eval_metadata.py
- tests/integration/test_api.py
- frontend/features/alerts/queries.test.tsx

## 5. Files that appear disciplined
- frontend/lib/bff-client.test.ts: broad transport normalization coverage, meaningful contract-focused assertions, good error-shape checks.
- frontend/components/ml-health/MLHealthWorkspaceViewModel.test.ts: focused on business semantics and fallback behavior, low coupling to implementation details.
- tests/unit/test_model_service.py: enforces confidence-tier and model-path constraints aligned with hard rules.
- tests/unit/test_update_alert_action_use_case.py: direct use-case behavior checks with proper repository interaction assertions.

## 6. Questions or ambiguities needing cross-batch verification
1. Is the canonical browser-facing status for upstream internal auth failure definitively `500` everywhere for triage/action/stats/ml-health, or are there any intentional exceptions?
2. Should route-layer ID validation explicitly reject non-positive integers (`0`, negatives) to align with `parseAlertId`, or is client-layer rejection intentionally authoritative?
3. Is the provider-level prohibition on `action-retry-success` still a product requirement, or legacy behavior from a removed retry mechanism?
4. Should integration tests mandate deterministic fixture setup (no conditional assertions) for `/api/feedback` and alert mutation routes?
5. Is `prediction_distribution` in ML health expected to remain dual-shape tolerant long-term, or should one canonical shape be enforced cross-layer?

## 7. Batch verdict
Fail for merge at current state.

Rationale: This batch contains at least one contract-semantics contradiction (critical), plus vacuous and conditionally non-executing tests in backend contract coverage that materially weaken confidence in merge safety.