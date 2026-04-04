# Bezzy Audit Correction Pass Status (2026-04-04)

## Scope

This note records the correction-pass status against blockers in:
- `docs/audit/final-merge-verdict.md`

## Fixed Findings

1. Test and contract proof trustworthiness
- `frontend/app/(auth)/login/page.test.tsx` now passes with durable accessible targeting.
- `frontend/components/SignInToast.test.tsx` now covers CTA visibility, popup-blocked fallback, close behavior, and no retry replay.
- `frontend/app/api/bff-routes.test.ts` internal-service-auth expectation now aligns with client contract (`500 INTERNAL_SERVICE_AUTH_FAILED`).
- `tests/unit/test_eval_metadata.py` vacuous assertions were replaced with explicit checks.
- `tests/integration/test_api.py` now includes explicit alert-action route proof for missing alert (404), invalid action (422), and valid update path (200).

2. Runtime duplication in model loading boundary
- Removed duplicate runtime file: `distillbert/services/model_service.py`.
- Runtime source remains `web_app/services/model_service.py`.

3. Setup/runtime boundary guidance drift
- `.env.example` now points `MODEL_PATH` / `MODEL_REGISTRY_PATH` to `ml_model/model_registry` with explicit supported patterns.
- `ml_model/model_registry/staging/README.md` now documents `MODEL_REGISTRY_PATH` usage aligned with runtime behavior.

4. Operator-facing semantics honesty
- Dashboard comparison now uses a consistent metric pair (`high_alert_count` vs `prev_high_alert_count`).
- ML health wording no longer claims traffic-volume derivation for policy bands.
- ML health/topbar copy was softened from live-overclaim wording to latest-snapshot phrasing.

## Overstated Or Context-Dependent Findings

- Sidebar/topbar count-scope differences remain a product decision concern, but were not required to unblock correctness for this pass.
- Broader branch-noise observations (assets/CSS churn/script quality) remain valid context but were out of this targeted correction scope.

## Remaining Non-Blocking Follow-Up

- `frontend` typecheck still fails on pre-existing readonly/mutable typing in `components/dashboard/AlertsTable/AlertsTable.tsx`:
  - line 350
  - line 363
  - line 558

These were not introduced by this correction pass and are unchanged in behavior scope.

## Verification Executed

- Frontend focused suite:
  - `npx vitest run --pool=threads app/api/bff-routes.test.ts lib/bff-client.test.ts "app/(auth)/login/page.test.tsx" "components/SignInToast.test.tsx" "app/(dashboard)/ml-health/page.test.tsx" "components/layout/AlertsNavItem.test.tsx"`
  - Result: pass
- Backend focused suite:
  - `python -m pytest -q tests/integration/test_api.py tests/unit/test_update_alert_action_use_case.py tests/unit/test_model_service.py tests/unit/test_eval_metadata.py`
  - Result: pass
- Frontend typecheck:
  - `npm run typecheck`
  - Result: fails only on pre-existing `AlertsTable.tsx` readonly assignment errors listed above.
