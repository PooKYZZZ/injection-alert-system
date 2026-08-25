# ML Health, User Management, and MFA Remediation Design

**Date:** 2026-08-25
**Repository:** CyberTrace / Injection Alert System
**Base:** `origin/master` after Dashboard/Alerts remediation PR #123 was merged
**Status:** Approved for implementation

## Purpose

This design covers the next remediation pass for three related frontend areas:

1. ML Health and Model Operations
2. User Management
3. MFA verification

The work starts from the clean merged base and is kept separate from the earlier Dashboard/Alerts change. The two product domains will remain independently reviewable:

- **PR 1 — ML Health / Model Operations:** operational model health, evaluation provenance, capability-aware loading/error states, request cancellation, and removal of proven-dead ML Health components.
- **PR 2 — User Management / MFA:** deterministic date rendering, typed admin responses, action feedback, explicit MFA challenge semantics, and accessible OTP interaction.

The implementation may use shared date/validation helpers only when the ownership is genuinely shared and the extraction is smaller and clearer than duplicating behavior.

## Evidence from the current base

### Runtime evidence

- The real staged artifact at `G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755` loads successfully in the isolated local backend.
- The local `/api/ml-health` response reports the real model version, `loaded: true`, `status: healthy`, evaluation metrics, and a prediction distribution.
- Runtime traffic processed and inference latency are both zero in a fresh local process. A zero latency value is therefore not a measured performance result.
- Drift is not evaluated until both baseline and recent samples meet the backend minimum sample requirement. The response correctly contains no drift score in a fresh local database.
- `/api/ml-model/summary` and `/api/ml-model/runs` return HTTP 503 when local retraining control is disabled. The frontend currently retries the requests and presents a prolonged generic loading state before eventually showing an error.
- User Management renders accounts from the configured hosted Supabase account-management path in the authenticated browser. No account mutation will be used as test traffic.
- User Management has a hydration error because `toLocaleDateString()` is called during client-component rendering and the server and browser produce different locale output.
- `/mfa/verify` renders when visited from a fully authenticated session even though the verification API requires a password-level login MFA challenge and a pre-authentication cookie. The page guard is broader than the route’s actual protocol.

### Source evidence

- `frontend/components/ml-health/MLHealthWorkspaceViewModel.ts` labels the page as `Snapshot-based` and `Reported window`, which is appropriate for the current response shape, but the UI can still imply that all metrics are live health signals.
- The ML Health overview hardcodes `threshold 0.050` even though the backend drift decision is based on a relative-confidence-change threshold of `0.10`. This is a display defect, not a reason to change the backend policy.
- The current model response mixes serving health, drift state, evaluation metrics, and prediction counts. It does not provide evaluation provenance or a last-evaluated timestamp, while the model artifact contains both current-looking `eval_report.json` values and older/legacy-labelled summary metadata. The correct response is to label provenance and unknowns rather than infer a single definitive evaluation story.
- `frontend/features/ml-model/queries.ts` does not pass TanStack Query’s cancellation signal to `fetch`, and the default query retry policy is unsuitable for a deliberate local capability-unavailable response.
- `frontend/features/user-management/UserManagementWorkspace.tsx` casts account-list JSON without schema validation, silently ignores failed refreshes, and has no per-row pending state for concurrent actions.
- `frontend/features/user-management/MfaVerifyForm.tsx` has no semantic form submission, OTP autocomplete hint, input mode, accessible error association, or submit behavior for the Enter key.
- The following ML Health components have no imports, dynamic imports, route references, shared exports, or test consumers outside their own definitions/tests: `ConfidenceDriftChart.tsx`, `ConfidenceThresholds.tsx`, `ModelHeader.tsx`, `PerClassF1Chart.tsx`, `PredictionDistribution.tsx`, and `ReliabilityDiagram.tsx`. They are candidates for a separate cleanup commit, subject to a final repository-wide reference check immediately before deletion.

## Design principles

### Honest states over invented precision

The UI must distinguish:

- configured versus unconfigured;
- loaded versus unavailable;
- measured versus not yet measured;
- evaluated versus not evaluated;
- insufficient data versus healthy/no issue;
- current runtime observations versus historical evaluation evidence.

The UI must not turn missing values into zero, display zero latency as a measured benchmark, invent a system-confidence score, or imply a drift result when the backend has not evaluated a sufficiently large sample.

### Separate operational concerns

ML Health answers: “Is the serving system currently usable and are available monitoring signals concerning?”

Model Operations answers: “What safe retraining/evaluation operations are available in this environment, and what evidence exists about prior runs?”

The pages may share visual language, but unavailable retraining controls must not make serving health appear broken, and historical F1/calibration evidence must not be presented as a live runtime measurement.

### Preserve the existing security boundaries

The browser continues to call Next.js route handlers, and route handlers continue to call FastAPI. No browser-to-FastAPI calls, secret exposure, frontend-only authorization, database migration, production-model write, or hosted-account mutation is part of this work.

### Prefer explicit contracts and deterministic presentation

Transport timestamps remain canonical instants. Values are validated at the BFF boundary, and display formatters use an explicit timezone/format where the value could be rendered during server and client phases. User-facing dates must include sufficient calendar context.

## PR 1 design — ML Health and Model Operations

### ML Health status model

Keep the existing backend transport contract unless an additive field is required and directly justified. The frontend view model will use explicit display states derived from existing fields:

- **Healthy:** model loaded, serving status healthy, and no critical reported drift.
- **Attention:** serving is degraded or the backend reports drift above its existing policy.
- **Unavailable:** the response cannot be obtained or is malformed.
- **Not reported:** a metric is validly absent, such as drift before minimum samples or ECE when no calibration value is packaged.
- **No traffic yet:** total processed is zero; latency is shown as “Not measured” rather than `0.0ms`.

The existing backend thresholds and confidence/action mapping remain unchanged. The UI will show the actual drift policy threshold only if it can be obtained from the response or a clearly named existing contract. If the current response cannot expose that value without widening the API contract, the UI will say that the drift score is not reported rather than display a hardcoded mismatched threshold.

### Evaluation provenance

The current artifact metadata warrants an explicit provenance treatment. The UI should show the available model version and evaluation status without claiming that the packaged evaluation is a fresh production-quality benchmark. The first implementation should prefer a small typed provenance status in the BFF/view model, for example:

- `reported` when the response carries packaged evaluation metrics;
- `not_evaluated` when no metrics are supplied;
- `provenance_unclear` when metadata conflicts or is legacy-labelled;
- `unavailable` when the health response cannot be read.

The status should be accompanied by explanatory copy and, where the current API cannot supply enough provenance, “Source metadata not exposed by the runtime response.” This is more defensible than fabricating a new score or silently choosing between conflicting artifact summaries.

If adding a backend field is necessary, it must be additive, validated by backend and BFF contract tests, and populated only from existing artifact metadata. It must not mark a model as promotion-ready because the artifact’s `quality_gates_passed` is false.

### Prediction distribution and evidence tables

The current response’s flat/current distribution is displayed as a reported snapshot. The UI will avoid calling it a baseline comparison unless both baseline and current values are present. Missing counts remain unavailable, not zero. Per-class F1 is labelled as evaluation evidence and includes the available support count; it is not represented as current traffic quality.

### Model Operations unavailable state

When the backend returns HTTP 503 because local retraining is disabled, the frontend will render a compact, explicit unavailable state:

> Model Operations are unavailable in this environment. Local retraining control is disabled.

It will include a manual retry action. The query will not retry a known 503 indefinitely. Other transient failures may retain a bounded retry policy, but the request must be cancellable when the component unmounts or the query becomes obsolete.

No retraining request, export action, database write, model promotion, or production artifact change is part of this pass.

### Request cancellation and query ownership

The existing query functions will accept TanStack Query’s `AbortSignal` and pass it to `fetch`. Query keys remain explicit and stable. Local component state will not duplicate server state. Query behavior will be tested at the query-function boundary and through the unavailable-state component path.

The chosen retry behavior follows the documented TanStack Query model: retries are useful for transient failures, but a deliberate capability response should be surfaced immediately. This is a behavior change in the frontend only; it does not alter the backend capability decision.

### Accessible ML controls and charts

Existing semantic tables will remain the primary machine-readable representation. Overview/Diagnostics view controls and diagnostic sub-tabs will receive selected/pressed semantics and keyboard-visible focus. Chart-like summaries will include text summaries so that the numeric tables are not the only way to understand a visual signal. No charting dependency will be added.

### Legacy cleanup

Before deletion, run repository-wide searches for direct imports, dynamic imports, route-level references, test references, barrel exports, CSS selectors, and build configuration references. Delete only the six unmounted legacy ML Health components and the test that exists solely for a deleted component if the final reference audit remains clean. Make this a separate cleanup commit and run typecheck, lint, tests, and production build afterward.

## PR 2 design — User Management and MFA

### User Management data contract

Add a Zod schema for the safe account-list response and parse the response before rendering. The schema will validate the fields intentionally exposed to the browser and reject malformed records with a user-visible error state. It will not expose passwords, tokens, MFA secrets, or provider internals.

Refresh failures will no longer be silently ignored. The page will preserve the last known list only while clearly showing a refresh/action error, and a manual retry path will be available.

### User Management actions

Per-row pending state will prevent ambiguous duplicate actions and make concurrent actions independent. Buttons will have explicit accessible names including the target account where appropriate. The existing authorization checks remain the source of truth; hiding a button is not treated as authorization.

The email action will use wording that matches the actual behavior (requesting/resenting email verification), not “Verify new email” if the administrator is only sending a verification request. MFA reset remains a protected server action and will not be made automatic.

### Deterministic dates

Account creation dates and model-operation dates will use a shared explicit formatter with a stable timezone/locale or an explicit UTC label. This prevents server/client hydration differences and avoids presenting a time-only value without calendar context. Malformed timestamps will render a safe “Unknown date”/equivalent state rather than throw.

The fix follows Next.js guidance for hydration mismatches: make the initial output deterministic instead of suppressing a mismatch warning. Browser-local conversion remains appropriate only where the UI explicitly promises local operator time; such conversion must happen after hydration or in a deliberately client-only presentation boundary.

### MFA verification

The MFA page will only render its verification form for a password-level session with the expected login-MFA challenge and valid pre-authentication handle. A fully authenticated session visiting the URL will be redirected instead of seeing a form that cannot submit successfully.

The form will use semantic `<form>` submission, six-digit validation, `autocomplete="one-time-code"`, numeric input mode, an appropriate input type, clear label/help text, focus on the code field, and an error message associated with the input. Invalid/expired challenge responses remain safe and generic. Existing backend rate limiting, replay protection, trusted-origin checks, and challenge verification remain unchanged.

The form will not add recovery-code workflows, bypasses, or weaker authentication paths.

## Research basis and decisions

- [Next.js hydration error guidance](https://nextjs.org/docs/messages/react-hydration-error) identifies locale-dependent date rendering as a source of server/client text mismatch and recommends deterministic rendering or a client-only boundary; suppressing the warning is an escape hatch, not the preferred fix.
- [TanStack Query retry guidance](https://tanstack.com/query/latest/docs/framework/react/guides/query-retries) documents default retries and custom retry functions. The Model Operations 503 is a deliberate unavailable capability, so it should be surfaced rather than retried three times before the user receives useful information.
- [Amazon SageMaker Model Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html) and [Model Dashboard](https://docs.aws.amazon.com/en_en/sagemaker/latest/dg/model-dashboard.html) separate serving/monitor status from model-risk and evaluation evidence. CyberTrace will use the same conceptual separation without reproducing enterprise complexity.
- [scikit-learn probability calibration guidance](https://scikit-learn.org/stable/modules/calibration.html) supports treating calibration as an evaluation property that requires appropriate evaluation data, not as a live health score invented from current traffic.
- [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html) supports one-time secret acceptance and rate limiting; the frontend will preserve the backend’s protections.
- [MDN autocomplete guidance](https://developer.mozilla.org/en-US/docs/Web/HTML/Reference/Attributes/autocomplete) defines `one-time-code` for one-time verification codes, and [WCAG 2.2](https://www.w3.org/TR/wcag/) supports programmatic input purpose, explicit error identification, and avoiding color-only meaning.
- Community reports such as [Keycloak issue #41831](https://github.com/keycloak/keycloak/issues/41831) and [TanStack Table issue #647](https://github.com/TanStack/table/issues/647) are supplementary evidence for mobile OTP autofill and wide-table scroll discoverability. They inform practical polish but do not override the repository’s security or accessibility requirements.

## Testing and validation design

### Test-first sequence

For each behavior change:

1. Add the smallest failing regression test.
2. Run it and preserve the expected failure.
3. Implement the minimum production change.
4. Run the focused test green.
5. Refactor only while the focused tests remain green.

### ML Health / Model Operations checks

- BFF schema tests for absent versus present evaluation/distribution values.
- View-model tests for no-traffic latency, unavailable metrics, drift state, and honest labels.
- Query tests for `AbortSignal` propagation and 503 retry behavior.
- Workspace tests for explicit Model Operations unavailable state and manual retry.
- Backend focused tests for any changed additive metadata contract, if needed.
- Browser checks for `/ml-health` and `/ml-model`, including network status, rendered states, and console output.

### User Management / MFA checks

- Shared date formatter tests for deterministic output and malformed values.
- User-management schema tests for valid, malformed, and partial responses.
- Workspace tests for refresh errors, per-row pending actions, and action feedback.
- MFA form tests for semantic submission, OTP attributes, validation, focus/error association, and API failure.
- MFA page/guard tests for password-level login challenge versus fully authenticated access.
- Browser checks for `/user-management` and `/mfa/verify` without mutating hosted accounts or submitting lockout-inducing invalid codes.

### Broad validation

After the focused groups:

- `cd frontend && npx vitest run --pool=threads`
- `cd frontend && npm run lint`
- `cd frontend && npm run typecheck`
- `cd frontend && npm run build`
- relevant backend focused tests, plus the broad backend suite if the changed contract crosses into backend code
- `git diff --check`
- fresh authenticated browser inspection of all three pages, network requests, and console warnings

Known environment failures will be reported separately from regressions introduced by this branch. Local proof will not be presented as hosted or production readiness.

## Deliberately out of scope

- No numeric “System Confidence” formula.
- No new severity model unless a separate domain decision and defensible labelled data support it.
- No change to confidence thresholds or automatic action mapping.
- No automatic triage transition merely because a page or drawer is opened.
- No retraining enablement, model promotion, production registry writes, dataset mutation, database migration, or hosted account mutation.
- No new charting/UI dependency and no enterprise SOC feature expansion.

## Completion criteria

The work is complete when the implementation has:

- explicit and honest ML Health/Model Operations states;
- no hydration mismatch from the touched pages;
- typed user-management data and visible refresh/action failures;
- a protocol-correct, accessible MFA form and page guard;
- proven-dead ML Health legacy components removed in a separate cleanup commit;
- focused and broad frontend validation run with exact results;
- browser verification showing no new route failures, missing styles, broken imports, or actionable console warnings;
- a final report separating implemented, deferred, unavailable, local-only, and unverified claims.
