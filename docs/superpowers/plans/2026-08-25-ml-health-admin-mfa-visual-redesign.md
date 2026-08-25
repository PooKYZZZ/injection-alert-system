# ML Health, User Management, and MFA visual redesign

Date: 2026-08-25

## Objective

Give the three pages a visibly new, intentional CyberTrace interface while preserving the functional and security remediation already present on this branch. The redesign is limited to presentation, interaction composition, and local client behavior unless a current contract prevents a truthful UI. No new model metrics, authentication factors, account-management capabilities, or backend schema fields will be invented.

## Current evidence

- ML Health currently renders a status banner, four equal KPI cards, two dense table panels, and a distribution table. The browser view makes healthy serving and unavailable monitoring look like peers in one dense grid. The page has useful truthfulness copy, but the first-glance question—whether the deployed model needs attention—is not visually dominant.
- User Management currently puts account creation inline above a wide table and places role selection, status actions, setup resend, an email input, and email verification in every row. The browser view clips the create button at common laptop widths and requires horizontal scrolling for the action-heavy table.
- MFA verification is correctly protected by the pre-auth/session guard. An unauthenticated browser request redirects to `/login`, so the visual route cannot be inspected without a legitimate challenge session. The isolated form is currently a small unbranded text form and can be tested through its existing component tests until a real challenge session is available.

## Research-derived decisions

### ML Health

1. Use a status-led hero: serving state, model identity, a plain-language explanation, and an explicit refresh affordance come before diagnostics.
2. Show three operational signal rows/cards—serving, drift monitoring, and calibration—with separate states for healthy, warning/critical, and not reported. Missing monitoring data must never read as healthy or failed.
3. Keep only directly operational values in the overview: traffic processed, measured latency, and latency trend. Put evaluation evidence and confidence policy behind named progressive-disclosure sections.
4. Keep the existing evidence boundaries: reported evaluation, current prediction distribution, and policy thresholds remain labeled as distinct sources. No timeline, baseline, threshold, or deployment freshness will be fabricated.
5. Retain a dedicated Diagnostics view, but present each diagnostic domain as a focused evidence panel rather than a wall of equally weighted tables. Tables remain for inherently tabular evidence and gain clear source/availability copy.

### User Management

1. Use an admin-console hierarchy: page summary and security counts, a primary “Create account” action, then a compact account list.
2. Make the list scan identity, role, security state, enabled state, and created date. Move role changes, resend setup, email-change request, account enable/disable, and MFA reset into one account-management dialog.
3. Keep sensitive actions deliberate. Disabling an account and resetting MFA require an explicit in-dialog confirmation; MFA reset keeps a required reason. Existing server authorization and recent-TOTP requirements remain unchanged.
4. Make the responsive list useful at narrow widths. The desktop table keeps semantic headers; the narrow presentation becomes stacked account records so an operator does not need to discover a seven-column horizontal scroll before finding a user.
5. Do not add unsupported last-login, invitation, audit, tenant, group, bulk, or advanced RBAC information. The only timestamp shown remains the supported `created_at` value.

### MFA verification

1. Use a branded, focused authentication shell with a small CyberTrace context panel and a clear “second factor” card. It should feel like the same product without becoming another dashboard.
2. Keep one real six-digit text input, styled as a prominent code field. This preserves label semantics, keyboard editing, paste, autofill, and screen-reader behavior. Do not create six independent inputs merely for visual fashion.
3. Keep the supported flow exactly as-is: current authenticator code, explicit error text, pending state, and redirect to `/dashboard`. Do not add recovery methods, remembered devices, backup codes, or alternate factors.

## Component and ownership approach

- Keep ML Health feature-specific rendering in `frontend/components/ml-health/`. The workspace remains the container; overview and diagnostics remain local presentational boundaries because they already have distinct responsibilities and tests. Helpers stay local unless a second owner proves reuse.
- Add one local interactive `AccountActionsDialog` boundary under `frontend/features/user-management/`. It owns the management surface and confirmation UI; the workspace remains responsible for fetched account state and API orchestration. Store the selected account ID, not a stale account snapshot, so refreshes are reflected in the open dialog.
- Keep MFA behavior in `MfaVerifyForm` and move its visual shell into a colocated CSS module. A new shared auth shell is intentionally deferred: the request is for MFA, and changing every auth route would widen the visual blast radius without being needed to make the MFA challenge coherent.
- Replace the existing ML Health CSS module styles in place rather than introducing a new design-system layer. Use the existing CyberTrace tokens and Lucide icons; do not add dependencies.

## Implementation groups and tests

### Commit 1 — Redesign ML Health hierarchy

Files:

- `frontend/components/ml-health/MLHealthWorkspace.tsx`
- `frontend/components/ml-health/MLHealthOverviewSection.tsx`
- `frontend/components/ml-health/MLHealthDiagnosticsSection.tsx`
- `frontend/components/ml-health/MLHealthWorkspace.module.css`
- `frontend/components/ml-health/MLHealthWorkspaceViewModel.ts` (only where display states need named copy)
- the colocated ML Health tests

Tests:

- healthy, degraded, critical, and unavailable-monitoring copy remains truthful;
- refresh exposes a pending state without hiding the last successful snapshot;
- overview/diagnostics selection remains keyboard and screen-reader understandable;
- evaluation/policy evidence remains available and source-separated;
- narrow layout has no required content clipped by the page shell.

Validation: focused Vitest tests, lint, typecheck, production build, and browser screenshots/DOM review at the existing desktop width plus narrow static layout checks.

### Commit 2 — Redesign User Management workflow

Files:

- `frontend/features/user-management/UserManagementWorkspace.tsx`
- new local `frontend/features/user-management/AccountActionsDialog.tsx`
- new/updated user-management styles if needed
- `UserManagementWorkspace.test.tsx` and focused dialog tests if extracted

Tests:

- create-account payload remains exactly email/display name/role;
- summary counts derive from the supplied accounts;
- account actions remain independently pending;
- role/status/setup/email/MFA actions preserve endpoint payloads;
- disable and MFA reset require the explicit confirmation path;
- dialog content uses the refreshed account record and remains accessible;
- empty, refresh-error, and narrow-list states are understandable.

Validation: focused Vitest tests, existing BFF/admin route tests, lint, typecheck, production build, and browser review of the account list and dialog.

### Commit 3 — Redesign MFA verification

Files:

- `frontend/features/user-management/MfaVerifyForm.tsx`
- new `frontend/features/user-management/MfaVerifyForm.module.css`
- `MfaVerifyForm.test.tsx`

Tests:

- one labelled six-digit input retains `one-time-code`, numeric input mode, exact validation, and paste-compatible native text behavior;
- invalid/expired responses remain associated with the field;
- pending state prevents duplicate submission;
- successful verification still assigns `/dashboard`;
- the visual shell exposes a clear second-factor heading and security context without unsupported recovery claims.

Validation: focused form tests, MFA BFF/route tests, lint, typecheck, production build, and browser route/redirect review. The authenticated rendered MFA screenshot remains conditional on a real challenge session.

### Commit 4 — Fresh senior review and cleanup

After the three redesigns, inspect the pages as a new reviewer. Remove only code made genuinely unused by the redesign after `rg` reference checks, test imports, route loading, and build verification. Do not remove active ML Health evidence components or unrelated auth forms merely because they look older.

Validation: full frontend Vitest suite, lint, typecheck, build, browser console/network review, and final diff/status review.

## Research references

Authoritative and primary references used for the design decisions:

- [Amazon SageMaker Model Dashboard](https://docs.aws.amazon.com/sagemaker/latest/dg/model-dashboard.html) — model identity, endpoint context, monitor state, and drill-down details are presented together; absent monitors are not equivalent to failed monitors.
- [Amazon SageMaker Model Monitor](https://docs.aws.amazon.com/sagemaker/latest/dg/model-monitor.html) — monitoring compares live observations with a baseline and reports violations rather than implying that every metric is always available.
- [SageMaker AI Insights dashboard](https://docs.aws.amazon.com/sagemaker/latest/dg/monitoring-detailed-observability-dashboard.html) — operational monitoring is grouped into performance, capacity, and reliability views for progressive investigation.
- [Arize quickstart](https://arize.com/resource/arize-quickstart-guide/) and [Arize dashboards](https://arize.com/docs/ax/machine-learning/machine-learning/how-to-ml/dashboards) — model overview pages lead with key health metrics and trends, while dashboards support deeper, purpose-specific analysis.
- [Azure Machine Learning online endpoint monitoring](https://learn.microsoft.com/en-us/azure/machine-learning/how-to-monitor-online-endpoints?view=azureml-api-2) — performance metrics can be viewed at overview and drilled-down levels; the interface should not claim metrics that the service does not supply.
- [Auth0 dashboard access by role](https://auth0.com/docs/get-started/manage-dashboard-access/feature-access-by-role) and [Auth0 dashboard MFA](https://dev.auth0.com/docs/get-started/manage-dashboard-access/add-change-remove-mfa) — user administration is permission-scoped and exposes MFA state as a compact management signal.
- [Microsoft Entra user-management enhancements](https://learn.microsoft.com/en-us/entra/identity/users/users-search-enhanced) — admin lists prioritize configurable scan fields while detailed user profiles hold the fuller management surface.
- [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [Error Identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification), and [Labels or Instructions](https://www.w3.org/WAI/WCAG22/Understanding/labels-or-instructions) — visible instructions, text errors, focus, and semantic controls are part of the interaction design, not after-the-fact decoration.
- [NIST SP 800-63B](https://pages.nist.gov/800-63-3/sp800-63b.html) — OTP entry needs enough time for users to read and manually enter the changing authenticator output.
- [input-otp rationale](https://github.com/guilhermerodz/input-otp) — supplementary practitioner evidence that one real text input preserves autofill, paste, undo, keyboard behavior, and a single screen-reader control better than hand-wired segmented fields.

## Explicit non-goals

- No API/schema/database changes.
- No new confidence/severity/system-confidence concepts.
- No fabricated monitoring freshness, baselines, threshold values, model deployment metadata, last-login timestamps, or authentication recovery options.
- No new dependency or global design-system rewrite.
- No unrelated page redesign.
