# CyberTrace Frontend Remediation Ledger

**Status:** Active execution ledger  
**Branch:** `codex/ml-health-admin-mfa-remediation`  
**Baseline HEAD:** `d1e3a6587990833201a663a868abf5468b2acdd6`  
**Governing specification:** User-provided “CyberTrace Frontend Redesign — Autonomous Product-Design and Engineering Master Prompt” in the task attachment. This ledger is the concise execution contract; it does not replace the master prompt.

## Execution contract

CyberTrace is an academic security and analyst-triage product. The redesign must improve correctness, coherence, and product specificity together. Work in focused finding-sized groups:

`inspect → understand the job/state → confirm the problem → research → decide → test-first where behavior changes → implement → run focused checks → inspect the real browser → critique/refine → document → review diff → focused commit`

The browser remains `Browser → Next.js route handler/BFF → FastAPI`; no browser-to-FastAPI calls, secret exposure, production model writes, hosted account mutations, fake telemetry, invented recovery, or enterprise IAM expansion are allowed. ML Health observes; Model Operations controls. Tables remain tables when comparison matters. Native HTML semantics are preferred over custom ARIA widgets. Status color must not substitute for status meaning. Unavailable, stale, not-evaluated, and no-traffic states must remain truthful.

Priority definitions:

- **P0:** blocks safe/correct use or creates a severe security/accessibility/product-flow failure.
- **P1:** important usability, security UX, accessibility, information-architecture, or correctness defect.
- **P2:** meaningful coherence, maintainability, density, consistency, or product-quality defect.
- **P3:** subjective polish or low-impact preference; do not iterate endlessly.

## Baseline evidence

### Repository and runtime

- Worktree is the requested existing worktree: `C:\Users\froi\.config\superpowers\worktrees\injection-alert-system\codex\ml-health-admin-mfa-remediation`.
- Branch is `codex/ml-health-admin-mfa-remediation`, 13 commits ahead of `origin/master`, at the baseline HEAD above. Existing source changes and `output/` evidence are preserved and are not treated as disposable scaffolding.
- Backend is running from this branch on port 8000 with the staged real model `distilbert_v3_907k_cleaned_20260312_133755`; frontend is running on port 3000. ML Health reports the real model and `HEALTHY` serving status.
- The staged artifact remains under `model_registry/staging`; promotion status is not changed by this work.

### Rendered application baseline

Authenticated in-app browser checks at the current runtime:

- `/dashboard`: mature dense operational layout, but the fresh view showed several loading placeholders while data was resolving.
- `/alerts`: native table with filters, sorting, row selection, detail actions, and honest five-row data; narrow guidance says to scroll horizontally.
- `/ml-health`: active real model identity, healthy serving, monitoring drift/calibration not reported, no traffic yet, and expandable evaluation/policy evidence.
- `/ml-model`: explicit unavailable state when local retraining control returns 503, with a retry action.
- `/user-management`: two enabled, verified ADMIN accounts; table plus account-details drawer; search and refresh are present.
- `/mfa/verify`: a fully authenticated visit redirects to `/login`, so no invalid login-MFA form is exposed for a session that cannot submit it.

### Required ML evidence-width reproduction

At 1440×900, with both Overview evidence sections expanded:

- `.disclosureGrid` uses two columns of approximately `537.5px`.
- Each expanded evidence region is approximately `538px` wide.
- The contained three-column tables are approximately `502px` wide.
- The evaluation table and confidence-policy table therefore compete side by side for horizontal reading width even though both contain dense comparative information. At a 575px narrow viewport the grid changes to one column, but the desktop information-density problem remains reproducible.

This is an open responsive/information-density finding, not proof that every table currently overflows. The implementation must research mature dashboard/table recomposition patterns and then give dense evidence the width it needs, likely by stacking or otherwise clearly sequencing the expanded sections.

### Existing evidence files

The prior visual evidence set is under [`output/playwright/evidence/`](../output/playwright/evidence/README.md). It includes the user-provided MFA image and earlier browser captures. New captures must be identified as current-state evidence and must not be confused with the earlier mock/degraded runtime captures.

## Initial product model

| Surface | User job | Primary objects and transitions | Dangerous or recoverable states |
| --- | --- | --- | --- |
| Dashboard | Understand current security workload and decide where to investigate | request → policy/action → recent alert workload | loading, no traffic, stale data, unavailable telemetry |
| Alerts | Compare and triage requests using WAF evidence, ML prediction, confidence, policy, and action | request → WAF evidence → prediction → confidence → action → analyst state | filters, empty/filtered-empty, stale refresh, detail drawer, mutation feedback |
| ML Health | Determine serving usability, monitoring freshness, applicable evaluation evidence, and active model identity | active model → serving evidence → monitoring evidence → evaluation evidence | healthy/degraded/down, unavailable, stale, not evaluated, no traffic |
| Model Operations | Inspect candidate/evaluation/run evidence and perform explicit safe controls | candidate → evaluated → approved → activated/rolled back | capability unavailable, pending, retryable failure, destructive confirmation |
| User Management | Decide whether an account can access CyberTrace and safely perform allowed administration | invited/pending setup → active → role/security mutation → disabled/re-enabled | pending setup, role consequence, self/last-admin protection, stale refresh, action failure |
| MFA | Complete the second authentication step safely and quickly | password accepted → valid pre-auth challenge → TOTP → authenticated | wrong-code retry, expired/no challenge, rate limit/exhaustion, service failure, duplicate submit |

## Prioritized backlog

Each item retains the original granular concern even when current evidence shows it is already resolved. `Open` means confirmed or still requiring implementation/research; `Investigate` means the source/runtime question must be settled before a decision; `Verified resolved` means the original concern is preserved with current evidence.

### P1 — correctness, recovery, security UX, accessibility

| ID | Finding | Surface/category | Status | Evidence and next decision |
| --- | --- | --- | --- | --- |
| MFA-001 | Verification still uses a separate, wordy security-marketing composition instead of a compact second-factor transaction. | MFA / hierarchy, copy, product specificity | Open | Source: `features/user-management/MfaVerifyForm.tsx`, `MfaVerifyForm.module.css`. Recompose around identity, explicit code label, submit, precise feedback, and truthful restart guidance without inventing recovery. |
| MFA-002 | Recoverable wrong-code handling preserves the logical value but does not explicitly return focus or make replacement easy after the error. | MFA / recovery, keyboard, accessibility | Resolved | The input retains the six digits after `INVALID_CODE`; an effect returns focus and selects the value for immediate replacement. Paste/autofill/mobile numeric attributes remain unchanged. |
| MFA-003 | MFA state-machine coverage is incomplete at the rendered surface for wrong code, expired, exhausted/locked, service failure, abandoned, refresh, Back/Forward, and duplicate submit. | MFA / auth state machine | In progress | Backend `INVALID_CODE`, `EXPIRED`, and `LOCKED` semantics are now preserved at the BFF; terminal states clear the pre-auth cookie, and duplicate submits are guarded. Full browser coverage for every lifecycle transition remains open. |
| MFA-004 | Terminal challenge states need a truthful safe exit/restart action if the current protocol supports one; a visual Back link must not be added with incorrect security semantics. | MFA / security UX | Resolved | Expired/locked responses clear the pre-auth handle and render a `Return to sign in` link to `/login`; no unsupported recovery or generic Back action was added. |
| UMG-001 | Account lifecycle is reconstructed from separate `Enabled`, email verification, and MFA fields rather than showing the actual access/setup state clearly. | User Management / lifecycle IA | Resolved for current contract | The server derives non-sensitive `setup_status` from `password_set_at`; the table and drawer now show setup pending/complete alongside enabled, verified, MFA, and pending-email state. |
| UMG-002 | `Resend setup email` is rendered for every account, including active accounts where setup is complete. | User Management / eligibility, security UX | Resolved | Setup resend is shown only for enabled accounts with authoritative `setup_status: pending`; active completed accounts show setup complete without an inapplicable action. |
| UMG-003 | Role changes are applied immediately from a select without explicit edit/save/cancel or a consequence review. | User Management / mutation safety | Resolved | Role selection is a local draft with Save/Cancel, a consequence explanation, and an explicit confirmation before the existing protected PATCH route is called. |
| UMG-004 | Security-sensitive account actions do not visibly encode self/last-usable-admin protections or session consequences. | User Management / authorization UX | Deferred: backend gap | The page now receives the current account id and disables self role/status controls. The current database function rejects self changes but does not enforce a last-enabled-ADMIN invariant; adding that guarantee requires an approved database-function change, so the UI does not pretend to provide it. |
| UMG-005 | MFA reset and email-change workflows need complete eligibility, consequence, pending, success, failure, correction, and cancellation semantics. | User Management / recovery, security UX | Investigate | Existing actions are present, but the contract does not yet prove all lifecycle transitions. Inspect route handlers and safe non-mutating render states; never mutate hosted accounts for evidence. |

### P2 — information architecture, density, coherence, maintainability

| ID | Finding | Surface/category | Status | Evidence and next decision |
| --- | --- | --- | --- | --- |
| MLH-001 | Expanded evaluation evidence and confidence policy are side-by-side dense sections that compete for horizontal width. | ML Health / tables, responsive density | Resolved | Reproduced at 1440×900: two ~538px regions and ~502px tables. The evidence disclosures now stack vertically so each table receives the available content width; narrow overflow remains available. |
| MLH-002 | ML Health still carries a repeated eyebrow/section-label recipe and repeated explanatory copy that weakens hierarchy. | ML Health / visual restraint, content density | Open | Current text includes `Model observability`, `Serving answer`, `What is known now`, `Current snapshot`, `Progressive detail`, and source restatements. Remove only copy that does not add interpretation, recovery, or provenance. |
| MLH-003 | Overview presents `Load state` and `Fallback` as “Not reported by endpoint,” although these fields have no operational meaning in the current contract. | ML Health / truthfulness, content | Open | Current browser confirms both fields. Remove/demote unsupported fields or expose them only as a clearly technical unavailable detail; do not fabricate load/fallback state. |
| MLH-004 | Evaluation/calibration evidence lacks enough visible applicability/provenance to establish that it describes the active model. | ML Health / evidence semantics | Investigate | Current evidence lists per-class F1 and four classes but no evaluation model/run/timestamp. Inspect backend contract/artifact metadata; prefer “no applicable evaluation” or provenance-unclear over inference. |
| MLH-005 | Freshness semantics distinguish neither reported-at nor retrieved-at in the visible snapshot. | ML Health / observability semantics | Investigate | Browser says “No report timestamp supplied.” Confirm available fields and label only what the endpoint actually reports; represent stale/unavailable/not-evaluated separately. |
| MLH-006 | Overview evidence disclosure architecture creates card/border density and may duplicate Diagnostics rather than serving as a concise attention-to-investigation bridge. | ML Health / IA, component boundaries | Open | Compare Overview and Diagnostics content. Keep Overview focused on “what needs attention?” and link/open evidence without repeating full datasets. |
| MLH-007 | Diagnostics tables and tabs need a full width/keyboard/responsive audit, including performance/serving, drift, calibration, policy, model identity, and unavailable/empty states. | ML Health / accessibility, tables, responsive | Open | Source has four diagnostic tabs and horizontal-scroll hint. Verify tab keyboard behavior, focus, table scan order, and truthful absent-state composition at desktop and narrow widths. |
| MLH-008 | Model Operations and ML Health boundaries need a cross-link/audit so observation does not duplicate activation, rollback, retraining, or policy control. | ML Health + Model Operations / IA | Investigate | `/ml-model` currently shows a truthful unavailable state. Inspect links and control surfaces before adding or removing navigation. |
| MLH-009 | Legacy ML Health chart/header components may be dead source and should be removed only after a final repository-wide reference audit. | ML Health / maintainability | Investigate | Existing design identifies six candidate unreferenced components. Search imports, dynamic references, tests, exports, CSS, and build config before any deletion; make cleanup a separate commit. |
| UMG-006 | User summary KPIs may spend prime visual space on counts that do not answer a useful administrative decision for a two-account population. | User Management / density | Open | Browser shows three large summary values. Compare compact summary, table-first, and lifecycle-oriented alternatives against actual admin job and data volume. |
| UMG-007 | Mutation feedback is generic (`Role updated`, `Account disabled`, etc.) and does not consistently identify target or consequence. | User Management / feedback | Resolved | Success and failure notices now name the target and action; mutation notices are also rendered inside the open drawer so Radix modal isolation does not hide the feedback from assistive technology. |
| UMG-008 | Empty account state is not distinguished from filtered-empty state, and search scope/zero-result wording needs verification. | User Management / empty/search | Resolved | Zero-account state explains how to begin; a non-empty list with no matches quotes the search term and exposes a Clear account search action. |
| UMG-009 | Email-change display needs explicit pending/proposed/verified semantics and only supported correction/cancellation actions. | User Management / lifecycle | Resolved for current contract | The table and drawer label pending email changes explicitly. The existing database function revokes the previous pending token when a new address is submitted, so the UI explains that replacement rather than inventing a cancellation flow. |
| UMG-010 | Admin drawer uses a border/card stack and immediate control changes whose hierarchy should be audited against productive density and dangerous-action placement. | User Management / visual hierarchy | Open | Current drawer has multiple bordered sections and a danger region. Refine only after action eligibility/consequence work is settled. |
| FOUND-001 | Shared typography and page composition are not yet a single intentional product language. | Cross-product / foundations | Open | `globals.css` defines Inter plus Orbitron/IBM utility families; login uses Orbitron and a separate background/card treatment while dashboard surfaces use a different shell. Audit Dashboard, Alerts, ML Health, Model Operations, User Management, and auth together before changing tokens. |
| FOUND-002 | Semantic roles for warm accent, selection, primary action, warning, and degraded states need a rendered cross-product audit. | Cross-product / color, status | Investigate | Tokens distinguish action/warning, but ML Health uses accent action for state labels and multiple legacy aliases remain. Confirm visible collisions before consolidating. |
| FOUND-003 | Borders, cards, uppercase labels, badges, icons, and explanatory copy are applied inconsistently across mature and newly redesigned surfaces. | Cross-product / visual restraint | Open | Use Dashboard/Alerts as references but do not preserve inconsistencies merely because they are older. Apply smallest shared-token/primitive change only after repeated reuse is proven. |
| FOUND-004 | Responsive transformations, focus visibility, text scaling, dialogs/drawers, tables, and mobile navigation need a deliberate cross-product audit rather than desktop stacking assumptions. | Cross-product / responsive accessibility | Open | Existing Alerts and User Management use horizontal table guidance; Sidebar uses a mobile dialog. Inspect at desktop, narrow desktop/tablet, and mobile widths with keyboard/focus checks. |
| FOUND-005 | The login surface remains visually and semantically separate from the current MFA shell, including background image, logo/icon density, placeholder-led fields, and button semantics. | Auth / coherence, accessibility | Open | `/login` is a full-screen image/card composition with sr-only labels and a click handler rather than a semantic form. Decide whether a focused auth-foundation slice is required for MFA coherence without expanding into unrelated auth redesign. |
| FOUND-006 | Loading, stale, empty, unavailable, degraded, permission, pending, success, and error states need a route-by-route inventory and browser proof. | Cross-product / states | Open | Current ML Health and Model Operations have explicit unavailable/no-traffic states; Dashboard was observed loading. Complete the inventory and fix only meaningful gaps. |
| FOUND-007 | Browser/runtime validation must include network, console, duplicate requests, layout shift, and interaction latency for affected surfaces. | Cross-product / performance | Open | Establish clean console/network baseline and compare after each focused group. Do not optimize unobservable micro-costs. |

## Completed finding records

### UMG-001/002/003/004/007/008/009 — Make account state and administrative mutations explicit

- **Status:** UMG-001/002/003/007/008/009 resolved for the current contract; UMG-004 self guard implemented with last-admin protection deferred
- **Priority:** P1 for lifecycle/mutation safety; P2 for feedback and empty/search states
- **Affected page/component:** `/user-management`; `frontend/features/user-management/UserManagementWorkspace.tsx`; `AccountActionsDialog.tsx`; `frontend/features/user-management/contract.ts`; `frontend/lib/server/db/account-management.ts`; server user-management page
- **Category:** Admin lifecycle, authorization UX, mutation safety, feedback, empty/search semantics, responsive drawer content
- **User job and domain state:** An administrator needs to scan which accounts can sign in, whether password setup is complete, whether identity/MFA state is current, and safely request a role/status/email/security change. The browser must express what the server actually knows and must not offer actions that the target account cannot satisfy.
- **Current rendered/source evidence:** The prior safe account contract exposed `enabled`, email verification, MFA, and `pending_email`, but not setup completion. The drawer always rendered `Resend setup email`; role `select` `onChange` called the protected PATCH immediately; notices such as `Role updated.` did not name the target and were hidden behind the modal’s `aria-hidden` background during an open drawer. The database rejects self role/status changes, derives `mfa_required` from role, and uses `password_set_at`/password-setup eligibility internally; it has no last-admin guard.
- **Why it mattered / impact:** Admins otherwise reconstruct lifecycle state from separate fields, can choose an action that the server will reject for an active account, and can unintentionally trigger privilege changes without reviewing MFA consequences. WAI-ARIA’s modal pattern requires focus to stay within the dialog and recommends a visible close control; feedback rendered only behind a modal is not a useful accessible status. Mature organization-management patterns expose membership state/role separately and make role changes explicit rather than conflating an invitation or active membership with a single label.
- **Research questions:** Which account lifecycle states are authoritative without exposing secrets? How should role changes communicate role-derived MFA consequences and session freshness? Which protections belong in the UI versus the database? How should a small list distinguish no accounts from no search matches?
- **Research summary and sources:** `[HIGH]` [WAI-ARIA Dialog Modal Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) requires modal focus containment, a labelled dialog, and a visible close control; the drawer already uses Radix Dialog, and the notice was moved into the dialog while it is open. `[HIGH]` [GitHub organization membership API guidance](https://docs.github.com/en/rest/orgs/members) separates membership state from role and documents that changing roles is an explicit owner action; it also distinguishes pending invitations from active membership. `[HIGH]` [Cloudflare account roles](https://developers.cloudflare.com/fundamentals/manage-members/roles/) treats administrative roles as distinct capability boundaries. Practitioner/admin-product reports were used as supplementary evidence for draft/save/cancel and target-specific feedback, not as authority for security invariants.
- **Decision and rejected alternatives:** Add a derived `setup_status` using the non-sensitive `password_set_at` timestamp; never select or return `password_hash`. Show setup resend only for enabled pending accounts. Keep the role select but make it a draft, add Save/Cancel, show role-to-MFA consequence text, and require a confirmation step before the existing server mutation. Pass the current session account id to disable self role/status controls, while documenting last-admin protection as a backend gap. Keep the existing drawer instead of adding a second modal for ordinary edits; retain the existing destructive disable confirmation. Rejected client-only last-admin enforcement, unconditional setup resend, immediate role mutation, fake email cancellation, and global notices hidden behind an open modal.
- **Implementation summary:** Added `setup_status` to the strict safe account contract and server mapping from `password_set_at`; added lifecycle labels to the table/drawer; gated setup resend; added explicit role draft/save/cancel/consequence/confirmation flow; passed current account identity to self guards; moved open-drawer mutation status into the dialog; made notices target-specific; added true-empty and filtered-empty search states; and labelled pending email replacement semantics.
- **Tests and exact results:** `npx vitest run --pool=threads features/user-management/contract.test.ts features/user-management/UserManagementWorkspace.test.tsx app/api/admin-users.test.ts lib/server/db/account-management.test.ts` — **PASS**, 4 files / 29 tests. `npm run typecheck` — **PASS**. Earlier red tests intentionally captured unconditional setup resend, immediate role mutation, missing setup/empty/pending-email semantics before implementation.
- **Browser observations and evidence:** In-app browser `/user-management` at desktop with the current real authenticated session shows two accounts with `Setup complete`; an active account drawer has no setup resend; the current session account has disabled role/status controls with explicit self-protection copy; a different account’s role draft shows the MFA consequence and Save/Cancel controls. No role/status/email/MFA mutation was submitted during browser review.
- **Commit:** Pending source commit; documentation hash will be recorded in the follow-up docs commit.
- **Follow-up findings:** UMG-004 last-enabled-ADMIN protection needs an approved database-function change; UMG-005 still needs a complete MFA reset/email mutation audit; UMG-006/010 remain visual-density/summary decisions.

### MFA-002/MFA-003/MFA-004 — Preserve recoverable retry context and expose terminal restart

- **Status:** MFA-002 and MFA-004 resolved; MFA-003 remains in progress for the broader lifecycle audit
- **Priority:** P1
- **Affected page/component:** `/mfa/verify`; `frontend/features/user-management/MfaVerifyForm.tsx`; `frontend/app/api/auth/mfa/verify/route.ts`; `frontend/lib/server/db/account-route-response.ts`
- **Category:** Authentication state machine, error recovery, accessibility, security UX
- **User job and domain state:** A user with a valid password-level, purpose-bound pre-auth challenge must submit one current TOTP code. A wrong code is recoverable; an expired or exhausted challenge is terminal and must not leave an apparently usable OTP form tied to stale temporary state.
- **Current rendered/source evidence:** `verifyMfaLogin()` already distinguishes `INVALID_CODE`, `LOCKED`, and `EXPIRED`, but `totpErrorResponse()` collapsed `LOCKED` and `EXPIRED` to `INVALID_CODE`. The client preserved the value but did not return focus or select it, and duplicate form submissions were not explicitly guarded.
- **Why it mattered / impact:** Users should be able to correct a rejected code without reconstructing context, while terminal challenges need a truthful next action. Leaving a terminal challenge-looking form available can encourage repeated submissions against expired or exhausted state. W3C error guidance requires the error to be identified and described and supports programmatic invalid/error association; MDN documents the single logical `one-time-code` input, numeric mobile hints, and six-digit TOTP behavior.
- **Research questions:** What retry behavior preserves context without making correction harder? Which backend states are terminal, and what restart action is actually supported by the pre-auth protocol? Is any recovery or resend action truthful for authenticator-app TOTP?
- **Research summary and sources:** `[HIGH]` [W3C WCAG 2.2 Error Identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification) supports explicit error identification/description and focus/error association. `[HIGH]` [MDN one-time passwords](https://developer.mozilla.org/en-US/docs/Web/Security/Authentication/OTP) supports one logical input with `autocomplete="one-time-code"`, `inputmode="numeric"`, `maxlength`, and pattern constraints. `[HIGH]` [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) describes the balance between useful authentication feedback and minimizing information leakage/friction. The repository’s challenge adapter is the authoritative state source: invalid is retryable; expired/locked are terminal.
- **Decision and rejected alternatives:** Preserve the rejected six-digit value for `INVALID_CODE`, return focus, and select the full value so the next keystroke or paste replaces it. Keep one logical input; do not add six boxes or a `Resend code` action. Preserve terminal codes as explicit safe client codes, clear the pre-auth cookie, and render `Return to sign in` to the existing login route. Rejected leaving terminal errors in the editable form, adding unsupported backup/recovery controls, and adding a generic Back link.
- **Implementation summary:** Added structured terminal TOTP response codes (`MFA_CHALLENGE_EXPIRED` and `MFA_CHALLENGE_LOCKED`), terminal pre-auth cleanup in the verify route, focus/select retry behavior, terminal restart rendering, and an explicit single-flight ref guard. Input semantics and error association remain intact.
- **Tests and exact results:** Added route-response, route cleanup, retry focus/selection, terminal rendering, and duplicate-submit regression tests. `npx vitest run --pool=threads lib/server/db/account-route-response.test.ts app/api/mfa-verify.test.ts features/user-management/MfaVerifyForm.test.tsx` — **PASS**, 3 files / 11 tests. `npx vitest run --pool=threads features/user-management/MfaVerifyForm.test.tsx` — **PASS**, 1 file / 7 tests.
- **Browser observations and evidence:** No live invalid TOTP was submitted, to avoid consuming challenge attempts. Existing in-app browser verification of authenticated/direct `/mfa/verify` behavior still redirects to `/login`; component tests cover recoverable and terminal render branches without mutating an account. A fresh terminal-state screenshot remains part of the broader MFA browser audit once a safe controlled harness is available.
- **Commit:** `58516b0` — `fix(auth): preserve MFA retry and terminal states`.
- **Follow-up findings:** MFA-003 remains open for browser Back/Forward/refresh, abandoned challenge, rate-limit/service-unavailable rendering, and an end-to-end terminal screenshot. MFA-001 remains open for compact visual composition.

### MLH-001 — Give expanded ML evidence the width it requires

- **Status:** Resolved
- **Priority:** P2
- **Affected page/component:** `/ml-health`; `frontend/components/ml-health/MLHealthWorkspace.module.css`
- **Category:** Information density, responsive composition, tables
- **User job and domain state:** An operator compares reported evaluation evidence and the active confidence policy while investigating the current model. Both are evidence datasets, not decorative summary cards.
- **Current rendered/source evidence:** Before the fix, `.disclosureGrid` used two desktop columns. At 1440×900, both expanded disclosures measured approximately 538px wide and their tables approximately 502px wide. Narrow mode stacked them, but desktop still made two detailed datasets compete for horizontal reading width.
- **Why it mattered / impact:** Carbon recommends placing data tables in the main content area with plenty of space and warns against cramped containers; dense comparative data needs readable columns. Grafana’s dashboard guidance uses rows/tabs and minimum sizing to keep observability sections legible. Primer’s table guidance treats horizontal scroll as a valid fallback only when the table remains available and keyboard-accessible. The CyberTrace evidence sections were not independent objects that benefited from side-by-side comparison, so the grid added compression without adding a useful comparison.
- **Research questions:** Should both disclosures remain side by side, become a vertical evidence sequence, or move to a separate page/modal? When is horizontal table scrolling acceptable, and how should it remain discoverable and keyboard-usable?
- **Research summary and sources:** `[HIGH]` [Carbon Data table usage](https://v10.carbondesignsystem.com/components/data-table/usage/) gives dense tables the main content width and recommends a dedicated page/modal when expanded detail feels cramped. `[HIGH]` [Grafana dashboard best practices](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/) recommends an explicit observability strategy, meaningful grouping, and cross-referenceable sections rather than uncontrolled panel growth. `[HIGH]` [Primer DataTable accessibility](https://primer-docs-preview.github.com/product/components/data-table/accessibility/) preserves table content with width options or horizontal scrolling and requires keyboard access to a scrollable table. `[MEDIUM]` the [Carbon horizontal-scroll issue](https://github.com/carbon-design-system/carbon/issues/4748) and practitioner discussions show that retaining full tables is often preferable to hiding or shrinking columns, but the appropriate choice depends on the comparison task.
- **Decision and rejected alternatives:** Stack the two native `<details>` disclosures vertically at all widths. Keep the existing table semantics and narrow-screen overflow fallback. Rejected keeping two columns because it preserves a card/grid composition at the cost of dense evidence width; rejected converting evidence to mobile-only cards because the content is comparative and should remain tabular; rejected adding a new route/modal because this is a small local composition defect and no separate navigation is needed.
- **Implementation summary:** Changed `.disclosureGrid` from two equal desktop columns to one `minmax(0, 1fr)` column. No API, view-model, component, or contract change.
- **Tests and exact results:** `npx vitest run --pool=threads "components/ml-health/MLHealthWorkspace.test.tsx" "components/ml-health/MLHealthDiagnosticsSection.test.tsx" "app/(dashboard)/ml-health/page.test.tsx"` — **PASS**, 3 files / 7 tests.
- **Browser observations and evidence:** In-app browser after hot reload, 1440×900: one grid column, each expanded region approximately 1087px wide, each table approximately 1051px wide. At 575×912: one column, each region approximately 506px wide, existing table containers remain available at 470px. Browser was restored to `/alerts` and temporary viewport override was reset.
- **Commit:** `aa2b4ee` — `fix(frontend): give ML evidence tables full width`.
- **Follow-up findings:** `MLH-007` remains open for explicit keyboard focus/scroll behavior and complete diagnostics state coverage.

### Verified resolved findings retained for completeness

| ID | Original concern | Current evidence |
| --- | --- | --- |
| RES-001 | Relative ML Health loading could fall back to `mock-model-service`. | Current branch backend was relaunched with the staged real artifact; authenticated `/ml-health` reports `distilbert_v3_907k_cleaned_20260312_133755` and `HEALTHY`. |
| RES-002 | ML Health hardcoded a mismatched drift threshold. | Current `buildPolicyBands` derives ranges from the response thresholds; do not change backend thresholds. Re-check whether the endpoint’s threshold is active configuration or theoretical display. |
| RES-003 | ML Health zero traffic could display zero latency as a measured value. | Current view model renders `Not measured` when `traffic_processed` is zero. Keep this contract. |
| RES-004 | ML/Model Operations query cancellation and deliberate 503 retry behavior. | Current query functions accept `AbortSignal` and stop retrying `RetrainingQueryError`; verify rendered/manual retry behavior remains correct. |
| RES-005 | User account data was rendered without a safe schema boundary. | `managedAccountsResponseSchema` is parsed before rendering and rejects unexpected sensitive fields. Keep contract tests. |
| RES-006 | User refresh errors were silently ignored and actions lacked independent pending state. | Current workspace preserves last data with an explicit refresh error and tracks per-action pending keys. Re-check browser behavior and feedback quality. |
| RES-007 | Account creation/managed dates could hydrate differently by locale. | Current table uses `formatStableDateTime` with an explicit UTC rendering path. Confirm formatter tests and browser output; do not reintroduce locale-dependent server rendering. |
| RES-008 | MFA form lacked semantic submit/OTP attributes/error association. | Current form uses `<form>`, `one-time-code`, numeric input mode, pattern, labels, and `aria-describedby`; recoverable wrong-code focus/selection and single-flight submission are now covered. |
| RES-009 | Fully authenticated users could see an unusable login-MFA form. | Current `/mfa/verify` page checks the pre-auth handle and password-level challenge; authenticated browser visit redirected to `/login`. |

## Master-prompt coverage map

This map prevents broad-theme synthesis from silently dropping granular requirements.

| Master area | Ledger coverage |
| --- | --- |
| Product jobs, domain objects, transitions, conventional controls | Initial product model; MFA-003/004; MLH-004/008; UMG-001/003/004/005 |
| Remediation system of record, priorities, evidence, research, decisions, commits | This document and per-finding fields below |
| Hierarchy, cards, borders, color, signatures, icons, badges, content density, typography, uppercase, spacing | FOUND-001/002/003; MLH-002/006; UMG-006/010; final audit |
| Tables, metrics, charts, evidence width, responsive recomposition | MLH-001/007; UMG-008; FOUND-004; final audit |
| First-class loading/empty/stale/unavailable/degraded/permission/pending/success/error states | FOUND-006; MLH-003/004/005/007; UMG-008/009; MFA-003/004 |
| Native accessibility, focus, keyboard, dialog/tab/drawer/form semantics, reduced motion, scaling | MFA-002/003; MLH-007; FOUND-004; per-group browser checks |
| MFA compact transaction, single logical OTP, paste/autofill/mobile, safe retry, terminal/restart, no fake recovery | MFA-001–004; RES-008/009 |
| ML serving/monitoring/evaluation/active-model separation, freshness, applicability, policy boundaries | MLH-001–009; RES-001–004 |
| User lifecycle, invitations, roles, unsafe admin states, session consequences, email/MFA flows, feedback, empty/search/refresh | UMG-001–010; RES-005–007 |
| Model Operations observation/control boundary | MLH-008; FOUND-006 |
| Dashboard/Alerts as references without blind preservation | Baseline evidence; FOUND-001–004; final audit |
| Authoritative research plus mature products plus practitioner experience | Research log per completed finding; no implementation claim before evidence is recorded |
| Test-first behavior, browser desktop/mobile/keyboard/network/console/performance checks | Validation protocol below and per-finding records |
| Focused commits, continued discovery, thesis scope, no fabricated sophistication | Execution contract; commit log; deferred findings |
| Final cross-product audit and report | Final audit section and completion gate |

## Research and validation protocol

For each Open/Investigate P0/P1/P2 group, record sources that directly answer the problem. Prioritize WCAG 2.2, WAI-ARIA APG, native HTML semantics, OWASP/NIST authentication guidance, Next.js/TanStack contracts, HCI/security-usability research, and mature patterns from GitHub Primer, Atlassian, Fluent, Carbon, GOV.UK, Cloudflare, Grafana, AWS, Evidently, WhyLabs, and comparable products. Use practitioner/community reports as supplementary practical evidence, not as sole authority.

Behavioral changes use a focused failing regression test first, then the smallest implementation and green check. Pure visual/IA exploration may be validated through rendered browser evidence first, but any deterministic behavior discovered during that exploration gets a regression test before production code is changed.

Minimum browser checks for each affected group: desktop and narrow/mobile viewport; visible focus and keyboard path; relevant loading/empty/error/stale/degraded/pending/terminal state; no unexpected console errors; network request count/status; and no misleading data. Capture current-state evidence under `output/playwright/evidence/` only when it is non-duplicative and clearly named.

## Finding record template

For every completed, deferred, or newly discovered meaningful finding, append/update:

```markdown
### <ID> — <title>
- Status: Open | In progress | Resolved | Verified resolved | Deferred
- Priority: P0 | P1 | P2 | P3
- Affected page/component:
- Category:
- User job and domain state:
- Current rendered/source evidence:
- Why it matters / impact:
- Research questions:
- Research summary and sources:
- Decision and rejected alternatives:
- Implementation summary:
- Tests and exact results:
- Browser observations and evidence files:
- Commit:
- Follow-up findings:
- Deferral reason (if applicable):
```

## Commit and completion log

| Commit | Finding group | Validation | Status |
| --- | --- | --- | --- |
| `d1e3a658` | Prior ML Health/admin/MFA design-plan baseline | Existing branch history; current runtime rechecked | Baseline |
| `ec29240` | Remediation ledger | `git diff --check`, document review | Baseline recorded |
| `aa2b4ee` | MLH-001 evidence-width recompose | 7 focused tests; desktop/narrow browser measurement; `git diff --check` | Resolved |
| `58516b0` | MFA-002/003/004 retry, terminal-state, and single-flight behavior | 3 focused test files / 11 tests PASS; `git diff --check` | MFA-002/004 resolved; MFA-003 remains in progress |
| pending | UMG-001/002/003/004/007/008/009 account lifecycle and mutation UX | 4 focused test files / 29 tests PASS; typecheck PASS; browser desktop/self/draft review | Source changes ready for commit |

## Final gate

Do not call the redesign complete until all meaningful in-scope P0/P1/P2 findings are resolved or defensibly deferred, the fresh Dashboard/Alerts/MFA/ML Health/Model Operations/User Management audit is recorded, and the relevant frontend tests, BFF tests, lint, typecheck, build, browser desktop/narrow/keyboard/state/network/console checks, backend checks for any changed contracts, and `git diff --check` have fresh evidence. Remaining issues must be P3 taste, speculative future capability, or unrelated scope.
