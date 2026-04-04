# Batch 1 Audit: Alert Action Path End-to-End and Transport/Schema Contracts

## 1. Batch summary

### Pre-audit restatement
- What this batch is supposed to do:
  - Ensure the alert action update flow is contract-safe from frontend route handler to BFF client to backend route, use case, repository, and schema/domain boundaries.
  - Keep transport action values exactly `BLOCKED`, `THROTTLED`, `ALLOWED`.
  - Keep route handlers thin and ownership disciplined.
- Why this batch is risky:
  - It crosses multiple ownership boundaries (frontend route, BFF transport, backend presentation/use-case/infrastructure).
  - Small contract drift can silently break behavior or produce misleading UI labels.
  - Validation duplication and split ownership can create inconsistent error behavior.
- Main files (primary behavior path):
  - `frontend/app/api/alerts/[id]/action/route.ts`
  - `frontend/lib/bff-client.ts`
  - `web_app/presentation/api/routes.py`
  - `web_app/application/update_alert_action_use_case.py`
  - `web_app/infrastructure/repositories/traffic_log_repository.py`
- Supporting files (contract/UI/interface boundaries):
  - `web_app/presentation/schemas/schemas.py`
  - `web_app/domain/interfaces.py`
  - `frontend/components/ui/ActionLabel.tsx`
- Tests that are supposed to prove behavior:
  - `frontend/app/api/bff-routes.test.ts` (frontend route validation/auth path)
  - `frontend/lib/bff-client.test.ts` (BFF upstream mapping + schema validation path)
  - `tests/unit/test_update_alert_action_use_case.py` (use-case action validation and not-found)
  - `tests/integration/test_api.py` (backend API wiring; currently only missing-alert 404 is covered for this route)

### Quick risk readout
- Transport value consistency check (`BLOCKED`, `THROTTLED`, `ALLOWED`): PASS across audited files.
- Route thinness and ownership discipline: MOSTLY PASS, with one layering concern and one split-validation concern.
- Generic patch-helper drift: NO EVIDENCE of over-generalized patch helper introduction in this batch.

## 2. Files audited

- `frontend/app/api/alerts/[id]/action/route.ts`
- `frontend/lib/bff-client.ts`
- `web_app/presentation/api/routes.py`
- `web_app/application/update_alert_action_use_case.py`
- `web_app/infrastructure/repositories/traffic_log_repository.py`
- `web_app/presentation/schemas/schemas.py`
- `web_app/domain/interfaces.py`
- `frontend/components/ui/ActionLabel.tsx`

Related proof tests reviewed:
- `frontend/app/api/bff-routes.test.ts`
- `frontend/lib/bff-client.test.ts`
- `tests/unit/test_update_alert_action_use_case.py`
- `tests/integration/test_api.py`

## 3. Findings

### Finding 1
- severity: high
- file path: `tests/integration/test_api.py`
- approximate line or area: around lines 150-157 (`test_update_alert_action_returns_404_for_missing_alert`)
- issue type: missing critical integration coverage
- what is wrong:
  - Backend route integration coverage for `PATCH /api/alerts/{alert_id}/action` only asserts the 404 path.
  - No integration assertion exists for:
    - success path (`200` + updated payload contract)
    - invalid action request rejection path (`422` from schema boundary and/or `400` from use-case boundary behavior)
- why it matters:
  - This is an end-to-end contract path. Without positive and invalid-input integration checks, route/use-case/schema coupling regressions can ship undetected.
- what should be rechecked or challenged:
  - Add/verify integration tests for success and invalid action payload behavior for this route.
  - Confirm expected status semantics for invalid action values (schema-level vs use-case-level) and lock it with tests.

### Finding 2
- severity: medium
- file path: `web_app/presentation/schemas/schemas.py`
- approximate line or area: line 7 import and line 16 alias (`AlertAction` import from application layer)
- issue type: ownership/layer coupling drift
- what is wrong:
  - Presentation schema now imports `AlertAction` from `web_app.application.update_alert_action_use_case`.
  - This creates schema-level coupling to a specific use-case module for a transport contract value set.
- why it matters:
  - Coupling presentation contracts to a single use-case implementation increases hidden change blast radius and makes contract ownership ambiguous.
  - A future refactor in application modules can ripple into schema import stability.
- what should be rechecked or challenged:
  - Confirm intended ownership of action value constants/types (domain/presentation contract module vs use-case module).
  - Challenge whether this dependency direction is intentional and stable long-term.

### Finding 3
- severity: medium
- file path: `frontend/app/api/alerts/[id]/action/route.ts` and `frontend/lib/bff-client.ts`
- approximate line or area:
  - frontend route: lines 25-26 (`Number` + `Number.isInteger` validation)
  - BFF client: lines 193-196 (`parseAlertId` regex `^[1-9]\d*$`)
- issue type: duplicated/split validation semantics
- what is wrong:
  - ID validation semantics are split and not equivalent:
    - route accepts any integer-like value via numeric coercion
    - BFF rejects non-positive and non-canonical numeric strings
  - Route passes raw `id` string downstream (`updateAlertAction(id, ...)`) after weaker validation.
- why it matters:
  - Error behavior ownership is blurred: route appears to validate, but stricter rejection happens later in BFF.
  - This can produce inconsistent expectations and harder-to-debug validation regressions.
- what should be rechecked or challenged:
  - Decide single owner for strict ID validation in this flow.
  - If route validates, align with BFF strictness; if BFF owns it, keep route guard intentionally minimal and documented.

### Finding 4
- severity: medium
- file path: `frontend/lib/bff-client.ts`
- approximate line or area: lines 818-842 (`updateAlertAction` non-OK branch)
- issue type: weak fallback / contract parity gap
- what is wrong:
  - `updateAlertAction` non-OK mapping does not preserve `Retry-After`, unlike shared `fetchUpstream` handling (lines 556+ in the same file).
  - Action update path is manually mapped and diverges from existing retry-aware behavior.
- why it matters:
  - Retry semantics are lost for retryable upstream failures on this endpoint, reducing client backoff signal fidelity.
  - Divergent error mapping paths increase long-term regression risk.
- what should be rechecked or challenged:
  - Confirm whether this endpoint should intentionally ignore retry hints.
  - If not intentional, align mapping behavior with existing retry-aware path conventions.

### Finding 5
- severity: low
- file path: `web_app/application/update_alert_action_use_case.py`
- approximate line or area: line 44 (`sorted(VALID_ALERT_ACTIONS)` in error text)
- issue type: contract messaging inconsistency
- what is wrong:
  - Error message order is generated by sort, not canonical transport order.
  - Current sorted output is likely `ALLOWED, BLOCKED, THROTTLED`, while canonical transport/list order is `BLOCKED, THROTTLED, ALLOWED`.
- why it matters:
  - Low direct runtime impact, but it increases confusion during debugging and can imply a different canonical ordering than shared contracts.
- what should be rechecked or challenged:
  - Keep diagnostic messaging aligned with canonical transport value order.

### Finding 6
- severity: low
- file path: `frontend/components/ui/ActionLabel.tsx`
- approximate line or area: lines 27-31 (`null` => `Unavailable`)
- issue type: potentially misleading UI fallback + missing focused test
- what is wrong:
  - `null` action is rendered as `Unavailable`, which may conflate "not yet set" with "data unavailable".
  - No focused unit test in this batch verifies label semantics for each action and null fallback.
- why it matters:
  - Analyst-facing UI wording can influence incident interpretation.
  - Without focused coverage, wording regressions are easy to miss.
- what should be rechecked or challenged:
  - Confirm product semantics for null action (unknown/unset/unavailable).
  - Add focused UI test to lock intended wording and aliases.

## 4. High-risk files in this batch

- `frontend/lib/bff-client.ts`
  - Central transport/error mapping boundary; manual branch logic diverges from shared retry-aware behavior.
- `web_app/presentation/schemas/schemas.py`
  - Contract schema now coupled to application use-case module for action typing.
- `frontend/app/api/alerts/[id]/action/route.ts`
  - Validation boundary split with BFF strictness; ownership can drift.

## 5. Files that appear disciplined

- `web_app/presentation/api/routes.py`
  - Action route remains thin and delegates business logic to use case.
- `web_app/application/update_alert_action_use_case.py`
  - Clear action validation and repository orchestration; no route/business leakage.
- `web_app/infrastructure/repositories/traffic_log_repository.py`
  - Repository update method stays simple and infrastructure-scoped.
- `web_app/domain/interfaces.py`
  - Interface remains clear for update operation contract shape.

## 6. Questions or ambiguities needing cross-batch verification

1. Is the intended canonical owner of action value types/constants the application use-case module, or should this live in a domain/presentation-neutral contract module?
2. Should `PATCH /api/alerts/{id}/action` preserve `Retry-After` metadata like other upstream mapping paths?
3. Is `null` action in UI truly "Unavailable", or should it represent "Unset/Not yet decided"?
4. Should strict alert ID validation be owned by frontend route handlers, BFF client, or both with identical semantics?
5. Are there cross-batch plans to introduce repository-level tests for `update_action_taken` parity with existing triage update behavior?

## 7. Batch verdict

Batch verdict: CONDITIONAL FAIL (merge-blocking for this batch until Findings 1-4 are explicitly resolved or risk-accepted).

- This is not a final branch verdict.
- Transport literals remained intact and generic patch-helper drift was not observed, but contract ownership and coverage depth are not yet defensible for a hostile audit standard.
