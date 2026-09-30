# CyberTrace Implementation Progress

Date: 2026-09-30
Branch: `codex/cybertrace-evidence-stabilization`
Base: `b2deeeb` (feature branch already included alert action semantics and redacted-query detail support)

## Plan requirements and implementation

The implementation plan calls for evidence-based request correlation, recorded
HTTP outcomes, traceable analyst action changes, usable alert detail, and the
additional informational confidence tier. The existing transport states and
enforcement gates must remain unchanged. The confidence bands are exact:
`0 = INFORMATIONAL`, `(0, 0.40) = LOW`, `[0.40, 0.70) = MEDIUM`,
`[0.70, 0.90) = HIGH`, and `[0.90, 1.0] = CRITICAL`. This is an evaluation and
observability change; it does not retrain or promote a model.

Implemented locally and covered by tests:

- Added nullable `request_correlation_id` and `observed_http_status` fields;
  producer transaction IDs remain separate. Invalid correlation values are
  rejected or normalized to unknown, and historical values are not inferred.
- Added evidence relationships (`CORROBORATED`, `ML_ONLY`, `WAF_ONLY`,
  `CONFLICTING`, `INCOMPLETE`) based on recorded source, model output, and CRS
  evidence. A WAF record may carry both model and CRS evidence.
- Added append-only `traffic_log_action_history`; the existing action update
  records the prior/new value, authenticated BFF actor ID, and server time in
  the same transaction as the current action update.
- Alert detail returns model provenance, response status, related evidence,
  relationship, and action history. The BFF validates these fields and the
  drawer displays unknown values as unknown. Transaction IDs alone do not
  establish WAF evidence.
- Centralized confidence-tier mapping and updated serving configuration,
  API/BFF validation, persistence width, filters, statistics, evaluation and
  training helpers, mocks, and dashboard/ML Health displays. Exact zero maps
  to INFORMATIONAL while preserving its prior `ALLOWED`/`MONITOR` behavior.
- Added migration `20260930_000031` for the nullable evidence fields, action
  history table, and tier-column width. Downgrade refuses to truncate stored
  `INFORMATIONAL` values.
- Fixed the bridge image to include the newly imported request-correlation
  module. Fixed triage retry handling so an absent fingerprint does not return
  before independent evidence mismatches are checked.
- Removed the BFF's inferred `medium` threshold midpoint. The backend configures
  low, high, and critical only, so the separate medium value now remains null.

## Repository and runtime findings

- The source used an Alembic remote-target guard. The configured hosted-style
  target was identified as remote, so no hosted migration was attempted.
- The isolated local Compose database is at `20260930_000031`. The backend,
  frontend, ModSecurity, bridge, and local Postgres are in the distinct
  `cybertrace-evidence-local` Compose project.
- A fresh request through `http://127.0.0.1:8088` returned HTTP 403. ModSecurity
  recorded transaction `179074399939.086276`, CRS score 8, and rule IDs
  `920350`, `942100`, and `949110`. The bridge persisted traffic row 2 with
  observed status 403, `CRITICAL`, and `BLOCKED`; the backend detail endpoint
  returned `CORROBORATED` from that row's model and CRS evidence.
- The technical-WAF profile did not emit a response correlation header for this
  request. `request_correlation_id` therefore remains null; the ModSecurity
  transaction ID and observed 403 are retained. No cross-producer correlation
  is claimed for this request.
- Backend `/health` returned healthy with its database connected. The local
  frontend `/login` returned 200; an unauthenticated `/dashboard` request
  redirected to login. The authenticated drawer flow was not browser-verified
  because no disposable authenticated session was available; its BFF and
  component contracts are covered by tests.
- The currently mounted active model has no matching held-out evaluation at
  these exact confidence bands. Re-binning available older three-seed
  benchmark arrays (58,515 predictions) gives LOW 34 (58.8% accuracy), MEDIUM
  518 (58.5%), HIGH 522 (64.8%), CRITICAL 57,441 (99.98%), INFORMATIONAL 0.
  These older checkpoints are diagnostic only and do not establish active-model
  calibration. No retraining or production registry write was performed.

## Research applied

Scikit-learn's [calibration](https://scikit-learn.org/1.4/modules/calibration.html)
and [threshold-tuning](https://scikit-learn.org/stable/modules/classification_threshold.html)
documentation distinguishes probability calibration from decision-threshold
selection. The implementation therefore does not describe tier boundaries as
calibration and does not infer model quality from score bands. The
[calibration survey](https://link.springer.com/article/10.1007/s10994-023-06336-7)
supports requiring held-out evidence before making calibration claims. The
project's numeric boundaries retain the stated
[Security Hub severity bands](https://docs.aws.amazon.com/securityhub/latest/userguide/controls-findings-severity.html)
as a numeric reference only; that is not presented as AWS ML guidance.

## Validation

- Backend full suite with process-local `RETRAINING_ENABLED=false`:
  **1,750 passed, 62 skipped**.
- Frontend full Vitest run after the BFF correction: **694 passed, 2 timed
  out** at the suite's 5-second limit while lint and typecheck ran concurrently.
  Both timed-out files passed in an isolated rerun (**63 passed**). The earlier
  full run before that small correction passed **696 tests**.
- Final BFF client and route regression run: **104 passed**.
- `npm run lint` and `npm run typecheck`: passed.
- Focused bridge/runtime-contract suite: **86 passed, 1 skipped**. Focused
  triage and Docker runtime-contract tests after the final backend patch:
  **66 passed**.
- Local Compose configuration/build and migration head were verified. A fresh
  WAF -> bridge -> backend -> Postgres -> alert-detail API request produced the
  evidence listed above.
- Local browser check confirmed login rendering and the protected-dashboard
  redirect. Authenticated drawer browser interaction remains unverified.

## Migration and remaining limits

Migration `20260930_000031` has been applied to the isolated local database and
tested through the normal migration path. The hosted-style database was not
changed: the safety guard rejects remote targets, and the repository runbook
requires a reviewed staging dry-run and backup before hosted migration work.
That operator step remains outstanding. Historical rows retain null evidence
where the source never captured it. Active-model held-out evaluation and
authenticated browser verification remain unavailable. The branch is not
merged.
