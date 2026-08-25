# CyberTrace Frontend Remediation Ledger

**Status:** Final audit recorded; explicit environment-bound deferrals documented
**Branch:** `codex/ml-health-admin-mfa-remediation`
**Baseline HEAD:** `d1e3a6587990833201a663a868abf5468b2acdd6`
**Current implementation HEAD:** `7a01746` (`fix(ml-model): make unavailable state actionable`)
**Governing specification:** User-provided “CyberTrace Frontend Redesign — Autonomous Product-Design and Engineering Master Prompt” in the task attachment. This ledger is the concise execution contract; it does not replace the master prompt.

## Reopened screenshot-critique remediation pass — 2026-08-25

**Status:** Implementation complete; final validation and ledger update are in progress.
**Reason reopened:** A fresh browser comparison against the user-provided screenshot critique found meaningful presentation and workflow defects that remained after the first remediation pass. This section is the active working memory for the pass and preserves the earlier ledger below.
**Baseline:** HEAD `289d9c3a13ea7665580510fe9cf14089f2c1e77b`; branch `codex/ml-health-admin-mfa-remediation`; requested worktree `C:\Users\froi\.config\superpowers\worktrees\injection-alert-system\codex\ml-health-admin-mfa-remediation`; unrelated untracked `output/` evidence is preserved.

### Reopened execution contract

CyberTrace is a calm, dense security and ML-operations console. Neutral surfaces and typography carry hierarchy; amber is a restrained identity/action accent; green, yellow, red, and blue communicate semantic state. Structure should be felt through alignment, spacing, and grouping rather than repeated borders and cards. Every page must make the operator's next decision easier without fabricating data or capabilities.

The working cycle remains:

`inspect rendered app → confirm source/contract → research → decide → test behavior first → implement one finding group → run focused checks → browser verify at desktop and narrow widths → critique/refine → document → focused commit → continue`

Preserve `Browser → Next.js route handler/BFF → FastAPI`, existing authorization and security state machines, truthful ML evidence, and the observational ML Health / controlling Model Operations boundary. Prefer native HTML semantics, progressive disclosure for rare mutations, concise sentence-case labels, and explicit status language over color-only or implementation-oriented wording.

### Research decisions for this pass

- W3C APG's [modal dialog pattern](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/) requires a visible close path, contained focus, and a title/label that names the dialog. The account drawer keeps Radix focus handling but will reduce visual obstruction and put inspection before mutations.
- [GOV.UK summary-list guidance](https://design-system.service.gov.uk/components/summary-list/) supports description lists for key facts and says not to use them as tables. This supports a compact lifecycle summary in the account drawer and removing low-value columns from the table.
- [Carbon data-table guidance](https://carbondesignsystem.com/components/data-table/usage/) recommends short sentence-case headers, a table toolbar for search/utilities, and expandable/progressive disclosure for dense row detail. This supports one contextual row action rather than repeated outlined buttons and full-width ML evidence sections.
- [GOV.UK error-message guidance](https://design-system.service.gov.uk/components/error-message/) says to keep failing form values, associate errors with their fields, and tell users how to recover. This supports preserving recoverable MFA input, returning focus/selecting the value, and repairing the bare password-recovery forms.
- [OWASP Authentication guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) supports generic password-recovery responses and careful MFA/re-authentication friction. No account-existence signal or unsupported recovery behavior will be added.
- Supplementary practitioner evidence consistently warns that dashboards become unreadable when every metric has equal visual weight; it is treated as a design signal rather than a normative standard. The implementation keeps secondary evidence available while moving it behind clear diagnostics or disclosure boundaries.

### Reopened prioritized backlog

| ID | Priority | Finding | Evidence to resolve | Status |
| --- | --- | --- | --- | --- |
| CRIT-SHELL-001 | P1 | TopBar repeats the page title already present in page content; the shell also applies inconsistent title/width/spacing patterns across Dashboard, Alerts, ML Health, Model Operations, and User Management. | Remove redundant hierarchy at the shared primitive, then browser-audit all dashboard routes at desktop and narrow widths. | Resolved |
| CRIT-TYPE-002 | P1 | Typography scale, helper contrast, uppercase eyebrows, control height, and spacing rhythm are inconsistent; small tracked labels carry too much hierarchy. | Recheck shared tokens/primitives and representative pages after every shared change. | Resolved for audited surfaces |
| CRIT-SURFACE-003 | P1 | Borders/cards/nested surfaces and orange accents compete with content; disabled controls and semantic status colors lack a consistent visual language. | Establish a restrained token adjustment and remove redundant framing in affected page owners. | Resolved for audited surfaces |
| CRIT-AUTH-004 | P1 | Authentication is not one coherent CyberTrace flow: Forgot Password and Reset Password are visually regressed, while setup, verification, recovery, and step-up routes do not share the login/MFA shell. | Create a small shared auth surface without changing BFF/security flow; validate every reachable auth route. | Resolved |
| CRIT-MFA-005 | P1 | MFA verification still has oversized code-entry treatment, redundant second-factor labeling, and a weak disabled state even though retry logic is correct. | Preserve one logical OTP input, paste/autofill/mobile semantics, and recoverable focus/select behavior while tightening the transaction UI. | Resolved; live challenge proof deferred |
| CRIT-ML-006 | P1 | ML Health repeats Healthy/monitoring/model information, gives Refresh too much prominence, uses implementation language, and frames the page as nested cards rather than an operator decision sequence. | Recompose Overview around serving → monitoring → evidence with one primary status and honest absence states. | Resolved |
| CRIT-ML-007 | P1 | Diagnostics has weak information architecture: dense evidence competes horizontally; Drift mixes production monitoring with offline evaluation; Calibration renders empty Not reported tables; raw source fields leak into default UI. | Reorganize into Performance, Monitoring, Evaluation, and Policy; stack dense evidence and use compact no-evidence states. | Resolved |
| CRIT-UMG-008 | P1 | User Management presents an unclear lifecycle, low-value Created column, repetitive View details buttons, ambiguous Security/Active wording, and a mutation-heavy drawer with always-visible MFA/email forms and overprominent disable action. | Make lifecycle facts primary, reduce table columns, use contextual row entry, and progressively disclose role/reset/email/disable workflows. | Resolved |
| CRIT-CROSS-009 | P2 | Dashboard, Alerts, Model Operations, and shared shell still need a fresh visual consistency pass after the shared changes. | Compare typography, density, states, table treatment, focus, and narrow behavior across all required routes. | Resolved for audited surfaces |
| CRIT-VALID-010 | P1 | Earlier evidence does not prove the reopened final branch state. | Capture current screenshots, inspect console/runtime, run full practical checks, review diff, and record focused commits. | Resolved for local validation scope |

### Non-goals and explicit safeguards

- No new ML telemetry, timestamps, model states, recovery mechanisms, or admin guarantees will be invented to complete a visual matrix.
- No production model write/promotion, database schema/function change, destructive account mutation, CI/deployment change, or new dependency is in scope.
- Existing P0/P1 security and accessibility behavior is preserved unless a focused regression test proves the presentation change needs an adjustment.

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
- Branch is `codex/ml-health-admin-mfa-remediation`, 27 commits ahead of `origin/master` at the final source HEAD above. Existing source changes and `output/` evidence are preserved and are not treated as disposable scaffolding.
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

This was the required open responsive/information-density finding at baseline, not proof that every table currently overflowed. It was resolved in `aa2b4ee` after researching mature dashboard/table recomposition patterns: expanded evidence disclosures now stack vertically so dense tables receive the available reading width, while native narrow overflow remains available.

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
| MFA-001 | Verification still uses a separate, wordy security-marketing composition instead of a compact second-factor transaction. | MFA / hierarchy, copy, product specificity | Resolved | The split marketing-style frame was replaced with a compact single CyberTrace surface: identity, `2 of 2`, second-factor label, six-digit code, precise feedback, submit, and truthful terminal restart only. The existing logical OTP input and state semantics remain intact. |
| MFA-002 | Recoverable wrong-code handling preserves the logical value but does not explicitly return focus or make replacement easy after the error. | MFA / recovery, keyboard, accessibility | Resolved | The input retains the six digits after `INVALID_CODE`; an effect returns focus and selects the value for immediate replacement. Paste/autofill/mobile numeric attributes remain unchanged. |
| MFA-003 | MFA state-machine coverage is incomplete at the rendered surface for wrong code, expired, exhausted/locked, service failure, abandoned, refresh, Back/Forward, and duplicate submit. | MFA / auth state machine | Deferred: controlled browser harness required | Backend `INVALID_CODE`, `EXPIRED`, and `LOCKED` semantics are preserved at the BFF; terminal states clear the pre-auth cookie, duplicate submits are guarded, and component/route tests cover recoverable and terminal branches. Full browser proof needs a controlled challenge harness; the current live session has no valid pre-auth challenge and no TOTP attempt was consumed. |
| MFA-004 | Terminal challenge states need a truthful safe exit/restart action if the current protocol supports one; a visual Back link must not be added with incorrect security semantics. | MFA / security UX | Resolved | Expired/locked responses clear the pre-auth handle and render a `Return to sign in` link to `/login`; no unsupported recovery or generic Back action was added. |
| UMG-001 | Account lifecycle is reconstructed from separate `Enabled`, email verification, and MFA fields rather than showing the actual access/setup state clearly. | User Management / lifecycle IA | Resolved for current contract | The server derives non-sensitive `setup_status` from `password_set_at`; the table and drawer now show setup pending/complete alongside enabled, verified, MFA, and pending-email state. |
| UMG-002 | `Resend setup email` is rendered for every account, including active accounts where setup is complete. | User Management / eligibility, security UX | Resolved | Setup resend is shown only for enabled accounts with authoritative `setup_status: pending`; active completed accounts show setup complete without an inapplicable action. |
| UMG-003 | Role changes are applied immediately from a select without explicit edit/save/cancel or a consequence review. | User Management / mutation safety | Resolved | Role selection is a local draft with Save/Cancel, a consequence explanation, and an explicit confirmation before the existing protected PATCH route is called. |
| UMG-004 | Security-sensitive account actions do not visibly encode self/last-usable-admin protections or session consequences. | User Management / authorization UX | Deferred: backend gap | The page now receives the current account id and disables self role/status controls. The current database function rejects self changes but does not enforce a last-enabled-ADMIN invariant; adding that guarantee requires an approved database-function change, so the UI does not pretend to provide it. |
| UMG-005 | MFA reset and email-change workflows need complete eligibility, consequence, pending, success, failure, correction, and cancellation semantics. | User Management / recovery, security UX | Resolved for current contract | The protected MFA-reset route accepts any distinct target and requires a bounded reason plus recent TOTP; the UI now exposes it for another protected ADMIN/ANALYST account, hides it for self and MFA-not-required accounts, and preserves explicit reason/disabled-submit semantics. Pending email replacement remains explicit; live mutations were not submitted. |

### P2 — information architecture, density, coherence, maintainability

| ID | Finding | Surface/category | Status | Evidence and next decision |
| --- | --- | --- | --- | --- |
| MLH-001 | Expanded evaluation evidence and confidence policy are side-by-side dense sections that compete for horizontal width. | ML Health / tables, responsive density | Resolved | Reproduced at 1440×900: two ~538px regions and ~502px tables. The evidence disclosures now stack vertically so each table receives the available content width; narrow overflow remains available. |
| MLH-002 | ML Health still carries a repeated eyebrow/section-label recipe and repeated explanatory copy that weakens hierarchy. | ML Health / visual restraint, content density | Resolved for current page | Replaced generic labels with purposeful `Monitoring`, `Runtime`, and `Evidence` labels, removed duplicated distribution/calibration explanation from Overview, and kept provenance/interpretation copy only where it changes a decision. Cross-product typography/chrome review remains under FOUND-001/003. |
| MLH-003 | Overview presents `Load state` and `Fallback` as “Not reported by endpoint,” although these fields have no operational meaning in the current contract. | ML Health / truthfulness, content | Resolved | Removed both unsupported fields. The page retains the authoritative active model version and serving status instead of exposing guessed load/fallback metadata. |
| MLH-004 | Evaluation/calibration evidence lacks enough visible applicability/provenance to establish that it describes the active model. | ML Health / evidence semantics | Resolved for current contract | Overview and Diagnostics state that evaluation fields come from the active model health response, while explicitly showing that evaluation run identity/timestamp are not supplied. Missing fields remain `not reported`; the UI does not claim the model was unevaluated or that artifact evidence is temporally current. |
| MLH-005 | Freshness semantics distinguish neither reported-at nor retrieved-at in the visible snapshot. | ML Health / observability semantics | Resolved for current contract | The BFF adds an ISO `retrieved_at` instant for the response it served. The UI labels it `Retrieved` and separately says `Source monitoring timestamp not reported`; no source freshness or stale judgment is invented. |
| MLH-006 | Overview evidence disclosure architecture creates card/border density and may duplicate Diagnostics rather than serving as a concise attention-to-investigation bridge. | ML Health / IA, component boundaries | Resolved | Overview now gives the evidence summary and a direct pointer to Diagnostics; detailed per-class, distribution, and calibration tables render only in the relevant Diagnostics sections. Confidence policy remains available as an Overview disclosure and Diagnostics tab. |
| MLH-007 | Diagnostics tables and tabs need a full width/keyboard/responsive audit, including performance/serving, drift, calibration, policy, model identity, and unavailable/empty states. | ML Health / accessibility, tables, responsive | Resolved for current surface | Diagnostics preserves four tab categories, adds the full distribution table under Drift, keeps native tables with narrow overflow, applies roving focus and Arrow/Home/End activation, and was exercised at desktop and 575px width. Live real-model evidence shows evaluation/distribution present and drift/calibration unavailable; no fake degraded backend state was created. |
| MLH-008 | Model Operations and ML Health boundaries need a cross-link/audit so observation does not duplicate activation, rollback, retraining, or policy control. | ML Health + Model Operations / IA | Resolved for current surface | Added an `Open Model Operations` link. ML Health remains observational; activation, rollback, retraining, and other control actions stay on `/ml-model`, whose unavailable state remains truthful. |
| MLH-009 | Legacy ML Health chart/header components may be dead source and should be removed only after a final repository-wide reference audit. | ML Health / maintainability | Resolved by audit | Repository-wide search on the final branch found only the active `MLHealthWorkspace`, Overview, Diagnostics, view-model, widget, loading, error, query, and type modules. No six-component legacy set or unreferenced ML Health component was found; no deletion was justified. |
| UMG-006 | User summary KPIs may spend prime visual space on counts that do not answer a useful administrative decision for a two-account population. | User Management / density | Resolved | Replaced the large KPI rail with a compact semantic summary line: Accounts, Enabled, and MFA required. The account table remains the primary workspace and still exposes the same derived counts. |
| UMG-007 | Mutation feedback is generic (`Role updated`, `Account disabled`, etc.) and does not consistently identify target or consequence. | User Management / feedback | Resolved | Success and failure notices now name the target and action; mutation notices are also rendered inside the open drawer so Radix modal isolation does not hide the feedback from assistive technology. |
| UMG-008 | Empty account state is not distinguished from filtered-empty state, and search scope/zero-result wording needs verification. | User Management / empty/search | Resolved | Zero-account state explains how to begin; a non-empty list with no matches quotes the search term and exposes a Clear account search action. |
| UMG-009 | Email-change display needs explicit pending/proposed/verified semantics and only supported correction/cancellation actions. | User Management / lifecycle | Resolved for current contract | The table and drawer label pending email changes explicitly. The existing database function revokes the previous pending token when a new address is submitted, so the UI explains that replacement rather than inventing a cancellation flow. |
| UMG-010 | Admin drawer uses a border/card stack and immediate control changes whose hierarchy should be audited against productive density and dangerous-action placement. | User Management / visual hierarchy | Resolved by audit | The drawer is a single focused side panel with a description-list access summary, separated security/email action groups, Radix focus containment, and one explicitly dangerous disable region. No extra card layer or competing action menu was found in the rendered desktop/narrow states; retain the pattern rather than adding more navigation or decoration. |
| FOUND-001 | Shared typography and page composition are not yet a single intentional product language. | Cross-product / foundations | Resolved for audited surfaces | Dashboard, Alerts, ML Health, Model Operations, User Management, login, and MFA now use the shared Inter/JetBrains token language for body, forms, tables, and operational metadata. Orbitron remains only for the persistent CyberTrace sidebar wordmark; the auth mini-brand was removed. |
| FOUND-002 | Semantic roles for warm accent, selection, primary action, warning, and degraded states need a rendered cross-product audit. | Cross-product / color, status | Resolved by audit | The rendered audit found the warm accent used for actions/identity, status colors used for health/triage outcomes, analytic blue used for telemetry/paths, and explicit unavailable/not-reported copy on ML Health/Model Operations. No token consolidation was justified without a demonstrated collision. |
| FOUND-003 | Borders, cards, uppercase labels, badges, icons, and explanatory copy are applied inconsistently across mature and newly redesigned surfaces. | Cross-product / visual restraint | Resolved for current scope | Dashboard and Alerts retain bordered panels where they contain decision-bearing metrics, charts, filters, or tables; ML Health evidence panels, User Management's table-first summary, and auth surfaces use reduced chrome. The login/MFA marketing copy, duplicate ML evidence, and oversized admin summary were removed. A full Dashboard/Alerts visual rewrite would be a separate product scope, not a remaining P1/P2 defect in the affected flows. |
| FOUND-004 | Responsive transformations, focus visibility, text scaling, dialogs/drawers, tables, and mobile navigation need a deliberate cross-product audit rather than desktop stacking assumptions. | Cross-product / responsive accessibility | Resolved for audited surfaces | Desktop and 575px browser evidence covers Dashboard, Alerts, ML Health, Model Operations, User Management, login, and MFA route boundary. Native tables retain explicit horizontal-scroll guidance; User Management and auth stack; Sidebar becomes a navigation dialog; changed ML tabs, MFA input, and admin drawer semantics have focused keyboard/accessibility tests. |
| FOUND-005 | The login surface remains visually and semantically separate from the current MFA shell, including background image, logo/icon density, placeholder-led fields, and button semantics. | Auth / coherence, accessibility | Resolved | `/login` now uses the shared CyberTrace shell, visible semantic labels, a native form submit path, shared tokens, explicit `aria-busy`/error association, and a compact password-plus-identifier transaction. No new recovery capability was added. |
| FOUND-006 | Loading, stale, empty, unavailable, degraded, permission, pending, success, and error states need a route-by-route inventory and browser proof. | Cross-product / states | Resolved for available local states | Final browser evidence covers Dashboard empty traffic, Alerts populated list/detail, ML Health healthy with missing drift/calibration, Model Operations unavailable, User Management default/empty/search/refresh/error test branches and safe confirmations, login empty, MFA no-preauth redirect, and MFA component wrong/terminal branches. Unsupported live service/rate-limit/exhaustion transitions remain test-only and are explicitly not claimed as browser captures. |
| FOUND-007 | Browser/runtime validation must include network, console, duplicate requests, layout shift, and interaction latency for affected surfaces. | Cross-product / performance | Resolved for local validation scope | In-app browser console review after the final routes found no warnings or errors (only Fast Refresh/React development info). Focused tests cover single-flight MFA and independent admin action pending states; route/BFF tests cover request contracts. The in-app browser surface does not expose a network HAR or layout-shift metric, so those measurements are recorded as unavailable rather than fabricated. |

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
- **Commit:** `5e66bc6` — `fix(admin): clarify account lifecycle actions`.
- **Follow-up findings:** UMG-004 last-enabled-ADMIN protection needs an approved database-function change. UMG-005/006/010 were resolved or bounded in the focused follow-up below; live mutation delivery remains intentionally unsubmitted.

### UMG-005/006/010 — Align account action eligibility and table-first density

- **Status:** UMG-005 resolved for the current route/contract and safe render states; UMG-006 resolved; UMG-010 resolved by audit with no additional structural change required
- **Priority:** P1 for MFA-reset eligibility; P2 for density and drawer hierarchy
- **Affected page/component:** `/user-management`; `frontend/features/user-management/UserManagementWorkspace.tsx`; `AccountActionsDialog.tsx`; protected admin-user routes and password-recovery boundary
- **Category:** Admin recovery eligibility, action safety, information density, side-panel hierarchy, responsive behavior
- **User job and domain state:** An administrator needs to identify account lifecycle state in a small list, open one account without losing table context, and see only actions that are meaningful for that target. MFA reset is a distinct-target recovery action with an explicit reason and recent-TOTP authorization; email changes remain pending until verification.
- **Current rendered/source evidence:** The protected route and `resetManagedAccountMfa` boundary reject self-targets, require a non-empty bounded reason, and call the protected `admin_reset_mfa` RPC. The prior UI incorrectly hid MFA reset for every `ADMIN` target and could show it for a `VIEWER` whose `mfa_status` was `not_required`. The prior page devoted a large horizontal rail to three counts even when the table contained only two accounts. The existing drawer rendered as one right-side focused panel with an access description list, security actions, and email verification actions.
- **Why it mattered / impact:** Hiding an eligible admin recovery action creates a false capability boundary; exposing an inapplicable reset control creates an unsafe-looking action. Oversized summary blocks also made the page feel like a generic dashboard instead of an account list. A compact fact line preserves the useful counts while keeping the table and target-specific action drawer primary.
- **Research questions:** Which facts deserve summary treatment when the collection is small? When is a description list preferable to a table or card? Does a side panel preserve enough list context for an administrative detail task, and how should dangerous actions be separated without turning the drawer into a stack of cards?
- **Research summary and sources:** `[HIGH]` [GOV.UK Summary list](https://design-system.service.gov.uk/components/summary-list/) recommends key/value description lists for facts and says not to use summary cards when only a small amount of related information is needed. `[HIGH]` [Carbon Data table usage](https://carbondesignsystem.com/components/data-table/usage/) recommends giving dense data its required width and using a side panel when expanded detail or tasks feel cramped. `[HIGH]` [Atlassian Drawer usage](https://atlassian.design/components/drawer/usage/) defines the side-panel pattern and cautions teams to use the newer modal approach where appropriate; this workspace already uses Radix Dialog for focus containment. `[SUPPLEMENTARY]` practitioner discussion on [side panels for data-heavy tables](https://www.reddit.com/r/UXDesign/comments/1adq08w) supports preserving table context for frequent administrative review while warning that the panel should not obscure critical table work; it is treated as experience evidence, not authority.
- **Decision and rejected alternatives:** Keep the right-side drawer and its semantic access summary; do not add tabs, a second dialog, or a new card hierarchy. Make the MFA reset condition `target is not self AND mfa_status is not_required`; preserve reason-required submission and existing backend guards. Replace the KPI rail with a compact `dl` fact line. Rejected exposing an ADMIN-only visual prohibition unsupported by the route, showing reset for MFA-not-required accounts, removing useful lifecycle counts altogether, and shrinking the table into dashboard cards.
- **Implementation summary:** Changed the summary to a compact table-first fact line; aligned MFA-reset visibility with the safe account contract; added regression coverage for another protected ADMIN target and an MFA-not-required VIEWER; kept the existing side-panel structure and dangerous-action confirmation unchanged.
- **Tests and exact results:** `npx vitest run --pool=threads features/user-management/UserManagementWorkspace.test.tsx features/user-management/contract.test.ts app/api/admin-users.test.ts lib/server/db/account-management.test.ts lib/server/db/password-recovery.test.ts app/api/password-recovery.test.ts` — **PASS**, 6 files / 39 tests. The intentionally red pre-fix run failed the protected-ADMIN reset eligibility test; the corrected run passed. `git diff --check` — **PASS**.
- **Browser observations and evidence:** In-app browser at 1440×900 shows the compact `Accounts 2`, `Enabled 2`, `MFA required 2` line above the table. The protected SOC Admin drawer now exposes `Reset MFA` with a reason field, while the current-user drawer still shows self-protection and no reset action. At 575×912, the summary remains a single readable line, the table retains the explicit horizontal-scroll guidance, and the mobile navigation collapses to the menu button. No role, status, MFA, email, or account-creation mutation was submitted.
- **Commit:** `f23c6b6` — `fix(admin): align account action eligibility`.
- **Follow-up findings:** UMG-004 still needs an approved database-function last-enabled-admin invariant; UMG-005 live success/failure delivery and email verification terminal states remain unsubmitted and therefore are not claimed as browser-proven. FOUND-001/002/003/004/006/007 remain for the final cross-product audit.

### MFA-002/MFA-003/MFA-004 — Preserve recoverable retry context and expose terminal restart

- **Status:** MFA-002 and MFA-004 resolved; MFA-003 defensibly deferred pending a controlled browser challenge harness
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
- **Browser observations and evidence:** No live invalid TOTP was submitted, to avoid consuming challenge attempts. The in-app browser visit to `/mfa/verify` without a valid pre-auth challenge redirects to `/login`; component tests cover recoverable and terminal render branches without mutating an account. Terminal and exhausted/rate-limit browser screenshots are deferred because the current environment does not provide a safe controlled challenge harness.
- **Commit:** `58516b0` — `fix(auth): preserve MFA retry and terminal states`.
- **Follow-up findings:** MFA-003 is deferred until a controlled challenge harness can safely exercise Back/Forward, refresh, abandoned challenge, rate-limit/service-unavailable rendering, and terminal screenshots. MFA-001 was resolved in the focused visual follow-up below.

### MFA-001 — Replace the security-marketing split frame with a compact transaction surface

- **Status:** Resolved for the current component and route contract; full lifecycle browser proof remains under MFA-003
- **Priority:** P1
- **Affected page/component:** `/mfa/verify`; `frontend/features/user-management/MfaVerifyForm.tsx`; `frontend/features/user-management/MfaVerifyForm.module.css`
- **Category:** Authentication hierarchy, content density, product coherence, responsive layout
- **User job and domain state:** A user who has passed the password step needs to finish a valid pre-authenticated sign-in with one current authenticator code. The screen should support that transaction quickly and make retry versus terminal challenge state unambiguous.
- **Current rendered/source evidence:** The prior component used a 920px two-column frame, oversized “quiet checkpoint” copy, repeated password/session explanation, a grid background, and multiple uppercase labels. The user-provided dark-mode evidence is preserved at `output/playwright/evidence/mfa-verification/user-provided/mfa-verify-dark-mode-user-provided.png`. Direct browser navigation to `/mfa/verify` without a valid pre-auth challenge correctly redirects to `/login`, so a live valid-challenge screenshot was not fabricated or forced by mutating an account.
- **Why it mattered / impact:** The old composition spent the visual budget on a second auth mini-brand and left the actual code transaction competing with decorative context. This weakened hierarchy and increased the distance between error recovery and the input. A compact form makes the required action, current step, and truthful exit path immediately legible on desktop and narrow screens.
- **Research questions:** What information must remain visible for a second-factor transaction? How should a compact auth form preserve OTP semantics without turning into six separate inputs? Which error and restart behaviors are truthful for authenticator-app challenges?
- **Research summary and sources:** `[HIGH]` [W3C Tabs and form guidance](https://www.w3.org/WAI/WCAG22/Understanding/error-identification) supports explicit error identification and programmatic association. `[HIGH]` [MDN one-time passwords](https://developer.mozilla.org/en-US/docs/Web/Security/Authentication/OTP) supports a single logical one-time-code field with numeric input hints and autofill semantics. `[HIGH]` [GOV.UK confirm-a-phone-number pattern](https://design-system.service.gov.uk/patterns/confirm-a-phone-number/) demonstrates a restrained verification transaction with clear task hierarchy. `[HIGH]` [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) supports minimizing unnecessary authentication friction without inventing unsafe recovery. The user-provided screenshot was used as visual evidence of the previous rendered state, not as an implementation specification.
- **Decision and rejected alternatives:** Replace the split frame with a 520px single-surface shell. Keep only CyberTrace identity, `2 of 2`, `Second factor`, the authenticator heading, concise six-digit instruction, the existing label/help/error association, submit, and terminal restart. Keep the logical OTP input and existing state-machine behavior. Rejected preserving the decorative grid, oversized workspace copy, separate context panel, six individual code boxes, a resend/backup-code action, and a generic Back link.
- **Implementation summary:** Removed the context aside and security-marketing copy; added the compact header and responsive single-column layout; preserved paste/autofill/numeric constraints, recoverable wrong-code focus/select behavior, terminal challenge branch, and single-flight `aria-busy` state.
- **Tests and exact results:** `npx vitest run --pool=threads features/user-management/MfaVerifyForm.test.tsx` — **PASS**, 1 file / 7 tests. `npm run typecheck` — **PASS**. `npm run lint` — **PASS**. `git diff --check` — **PASS**.
- **Browser observations and evidence:** In-app browser navigation to `/mfa/verify` without a valid challenge redirects to `/login`, confirming the safe route boundary. The valid, invalid, and terminal component branches were exercised by the focused tests without consuming live TOTP attempts. The preserved user-provided dark-mode image is the evidence artifact for the prior valid-code surface; no fabricated current valid-challenge screenshot is claimed.
- **Commit:** `879cc71` — `fix(auth): simplify MFA verification surface`.
- **Follow-up findings:** MFA-003 remains open for full browser lifecycle proof and supported service/rate-limit/abandoned states. FOUND-005 remains a bounded cross-product login/MFA coherence audit; no unrelated login redesign was pulled into this focused change.

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

### MLH-002/003/004/005/006/007/008 — Make ML Health evidence truthful, navigable, and investigation-oriented

- **Status:** MLH-002/003/004/005/006/008 resolved for the current page and contract; MLH-007 resolved for the current surface, with final cross-product state/a11y audit still required.
- **Priority:** P2
- **Affected page/component:** `/ml-health`; `frontend/components/ml-health/MLHealthWorkspace.tsx`; `MLHealthWorkspaceViewModel.ts`; `MLHealthOverviewSection.tsx`; `MLHealthDiagnosticsSection.tsx`; `frontend/app/api/ml-health/route.ts`; ML Health type and tests.
- **Category:** Observability semantics, information architecture, evidence provenance, keyboard accessibility, responsive tables, navigation boundaries.
- **User job and domain state:** An operator needs the active model identity and serving answer first, then wants to inspect the exact evidence available for runtime performance, drift, evaluation, calibration, prediction mix, and confidence policy. The current real endpoint reports the staged DistilBERT version, healthy serving, evaluation/per-class/distribution fields, and no drift/calibration result; the UI must not turn missing provenance or source freshness into a judgment.
- **Current rendered/source evidence:** The backend `MLHealthResponse` has no source `reported_at`, evaluation run id, evaluation timestamp, or evaluation-model linkage. The view previously rendered unsupported `Load state`/`Fallback` values, repeated distribution/calibration content in Overview, and used click-only tab buttons. The live endpoint response was rechecked from the running branch and reported `distilbert_v3_907k_cleaned_20260312_133755` with `HEALTHY` serving.
- **Why it mattered / impact:** Unsupported fields create false precision; duplicated tables make the Overview compete with the evidence workspace; and click-only tab widgets make keyboard inspection slower and less predictable. Operators need readable tables and a clear boundary between retrieved-at, source freshness, evaluation applicability, and policy configuration.
- **Research questions:** How should an observability surface compose summary versus drill-down evidence? Which freshness instant is safe to expose when the source does not provide one? What keyboard behavior is expected for an automatically activated tablist? When should dense comparative data remain in a table instead of becoming compressed cards?
- **Research summary and sources:** `[HIGH]` [WAI-ARIA Tabs Pattern](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/) defines active-tab focus, Arrow navigation, optional Home/End, tab/tabpanel relationships, and automatic activation when panels are readily available. `[HIGH]` [Grafana dashboard best practices](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/) recommends dashboards answer a focused question, reduce cognitive load, use meaningful hierarchy/drill-down links, and avoid uncontrolled panel sprawl. `[HIGH]` [Carbon Data table usage](https://v10.carbondesignsystem.com/components/data-table/usage/) keeps dense comparison in tables, supports progressive row expansion, and gives tables a primary content area rather than squeezing them into decorative cards. The endpoint and artifact loader were also inspected directly; no unsupported evaluation provenance was inferred from a folder name.
- **Decision and rejected alternatives:** Keep Overview as the serving answer plus a concise evidence bridge; render full per-class, prediction-distribution, and calibration tables in Diagnostics. Add the actual BFF retrieval instant but label source monitoring freshness as not reported. Remove unsupported load/fallback fields rather than exposing technical-sounding placeholders. Add one safe link to Model Operations without duplicating its controls. Use native buttons with WAI-ARIA tab semantics, roving `tabIndex`, and automatic Arrow/Home/End activation. Rejected fake source timestamps, inferred evaluation applicability, synthetic degraded data, compressed evidence cards, and a new shared tab abstraction for two local owners.
- **Implementation summary:** Added optional `retrieved_at` to the BFF response and display model; added explicit evaluation provenance/unknown-state copy; removed load/fallback identity facts; simplified Overview evidence and moved detailed distribution into Drift Diagnostics; added the Model Operations cross-link; and added keyboard navigation/focus management for top-level and diagnostic tabs. The real-model response remains unchanged at the FastAPI boundary.
- **Tests and exact results:** Failing tests first captured missing retrieval/provenance output, unsupported fields, absent tab focus behavior, and missing route retrieval metadata. Green run: `npx vitest run --pool=threads components/ml-health/MLHealthWorkspaceViewModel.test.ts components/ml-health/MLHealthDiagnosticsSection.test.tsx components/ml-health/MLHealthWorkspace.test.tsx "app/(dashboard)/ml-health/page.test.tsx" app/api/bff-routes.test.ts` — **PASS**, 5 files / 64 tests. `npm run typecheck` — **PASS**. `npm run lint` — **PASS**. `git diff --check` — **PASS**.
- **Browser observations and evidence:** In-app browser at 1440×900 showed the real staged model identity, `HEALTHY` serving, `Source monitoring timestamp not reported`, and an actual BFF retrieval time. Diagnostics Performance, Drift, Calibration, and Policy tabs were opened; ArrowRight moved Performance to Drift; Drift showed real per-class F1 and prediction counts while drift remained not reported; Calibration showed an honest unavailable state; Policy showed the configured threshold bands and the Normal exception. At 575×912, the two-column diagnostic tablist becomes a readable 2×2 layout and table overflow remains available. No backend state was fabricated or mutated.
- **Commit:** `7f1165b` — `fix(ml-health): clarify evidence and navigation`.
- **Follow-up findings:** Final cross-product typography/chrome/state audit remains under FOUND-001/003/004/006/007. MLH-009 remains a separate repository-wide dead-source audit.

### FOUND-001/002/003/004/005/006/007 + MLH-009 — Final cross-product audit

- **Status:** Resolved for the audited local scope; UMG-004 remains deferred for the backend invariant gap and MFA-003 remains deferred for the controlled browser challenge gap.
- **Priority:** P1/P2 cross-product coherence, accessibility, state coverage, and maintainability.
- **Affected page/component:** `/login`, `/mfa/verify`, `/dashboard`, `/alerts`, `/ml-health`, `/ml-model`, `/user-management`, shared shell/sidebar, and active ML Health module references.
- **Category:** Product language, semantic status, density, responsive behavior, authentication UX, state coverage, runtime validation, and repository hygiene.
- **User job and domain state:** An analyst or administrator must move between authentication, workload, triage, model observation, model operations, and account administration without relearning visual semantics or being shown unsupported certainty.
- **Current rendered/source evidence:** The final in-app-browser pass used dark-mode 1440×900 and 575×912 captures across all affected routes. Dashboard showed honest no-traffic state; Alerts showed the populated triage table and a read-only detail drawer; ML Health showed the real staged model, healthy serving, missing source monitoring timestamp, expanded evidence, all four diagnostics tabs, and truthful missing drift/calibration; Model Operations showed its unavailable state; User Management showed compact summary, protected-admin MFA eligibility, safe confirmation/create states, search/empty behavior, and narrow table/drawer behavior; login and the MFA route boundary were captured at both widths. Repository search found no separate unreferenced legacy ML Health component set.
- **Why it matters / impact:** These checks distinguish a coherent operational product from a collection of visually similar pages, and prevent the redesign from manufacturing telemetry, recovery, lifecycle guarantees, or browser proof that the local environment cannot provide.
- **Research questions:** How should dense tables recompose; how should tabs, drawers, auth errors, OTP retry, status semantics, and admin confirmations behave; and which visual chrome is decision-bearing rather than decorative?
- **Research summary and sources:** Decisions were grounded in [WAI-ARIA Tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/), [WCAG error identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification), [Carbon data-table guidance](https://carbondesignsystem.com/components/data-table/usage/), [GOV.UK summary lists](https://design-system.service.gov.uk/components/summary-list/), [GOV.UK phone confirmation](https://design-system.service.gov.uk/patterns/confirm-a-phone-number/), [Atlassian Drawer guidance](https://atlassian.design/components/drawer/usage/), [OWASP Authentication guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [MDN OTP guidance](https://developer.mozilla.org/en-US/docs/Web/Security/Authentication/OTP), and [Grafana dashboard best practices](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/best-practices/). Practitioner discussion was treated as supplementary, including the recorded UX side-panel discussion, not as a substitute for standards or product evidence.
- **Decision and rejected alternatives:** Keep mature Dashboard/Alerts panels where they carry metrics, charts, filters, or tables; reduce auth chrome; keep ML Health observational; keep native tables and explicit overflow; keep one account drawer; retain truthful unavailable/not-reported language; and do not add invented disabled/locked/recovery/telemetry states merely to complete a screenshot matrix.
- **Implementation summary:** Added the compact shared login shell; retained MFA retry value with focus/selection and terminal restart; clarified ML Health evidence provenance, retrieval semantics, diagnostics navigation, and full-width evidence; aligned User Management summary density and action eligibility; and recorded the final evidence index without submitting destructive or externally meaningful mutations.
- **Tests and exact results:** Final focused run: `npx vitest run --pool=threads features/user-management/UserManagementWorkspace.test.tsx features/user-management/contract.test.ts features/user-management/MfaVerifyForm.test.tsx components/ml-health/MLHealthWorkspaceViewModel.test.ts components/ml-health/MLHealthDiagnosticsSection.test.tsx components/ml-health/MLHealthWorkspace.test.tsx app/(dashboard)/ml-health/page.test.tsx app/api/admin-users.test.ts app/api/mfa-verify.test.ts app/api/bff-routes.test.ts lib/server/db/account-management.test.ts lib/server/db/password-recovery.test.ts app/api/password-recovery.test.ts app/(auth)/login/page.test.tsx` — **PASS**, 14 files / 118 tests. `npm run lint` — **PASS**. `npm run typecheck` — **PASS**. `npm run build` — **PASS**, Next.js optimized build generated all routes. `git diff --check` — **PASS**. Backend `/health` — **PASS**, `healthy`; unauthenticated direct `/api/ml-health` — **401 Unauthorized**, which confirms the protected route boundary rather than a model failure. Authenticated BFF/browser evidence reports the real model separately.
- **Browser observations and evidence:** `output/playwright/evidence/final-branch/` is the current authoritative set, indexed by `output/playwright/evidence/README.md`. The final console review showed no browser errors or warnings; the in-app browser does not expose a HAR or layout-shift metric, so network-count/layout-shift/interaction-latency measurements are recorded as unavailable rather than inferred. No destructive account, role, status, email, MFA, alert-triage, or model-control action was submitted.
- **Commit:** `8eb2f8c` — `fix(auth): align login with CyberTrace shell`; documentation/evidence ledger update follows this record.
- **Follow-up findings:** UMG-004 is deferred until an approved database-function change enforces the last-enabled-ADMIN invariant. MFA-003 is deferred until a safe controlled pre-auth challenge harness can exercise live lifecycle transitions. These are explicit environment/contract boundaries, not claims that the missing proof exists.

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
| `5e66bc6` | UMG-001/002/003/004/007/008/009 account lifecycle and mutation UX | 4 focused test files / 29 tests PASS; typecheck PASS; lint PASS; browser desktop/self/draft review | UMG-001/002/003/007/008/009 resolved; UMG-004 deferred for backend gap |
| `7f1165b` | MLH-002/003/004/005/006/007/008 evidence semantics, Overview density, tab navigation, and Model Operations link | 5 focused files / 64 tests PASS; typecheck PASS; lint PASS; desktop/narrow/keyboard browser review; `git diff --check` | Resolved for current ML Health surface/contract; final cross-product audit remains |
| `879cc71` | MFA-001 compact verification surface | 7 focused tests PASS; typecheck PASS; lint PASS; direct route boundary checked in the in-app browser; `git diff --check` | Resolved for current MFA component; lifecycle browser proof remains under MFA-003 |
| `f23c6b6` | UMG-005/006/010 action eligibility, compact summary, and drawer audit | 6 focused files / 39 tests PASS; desktop/narrow/protected-admin browser review; `git diff --check` | UMG-005/006 resolved; UMG-010 resolved by audit |
| `8eb2f8c` | FOUND-005 login/MFA shell coherence and native login semantics | Login tests PASS; final lint/typecheck/build/browser review; `git diff --check` | Resolved |
| `8e973d5` | Final cross-product audit, evidence index, and explicit deferral record | 14 files / 118 tests PASS; lint/typecheck/build/backend health/browser desktop+narrow+console review; `git diff --check` | Recorded |

## Previous final gate (superseded by reopened screenshot-critique pass)

The previous audit is retained for historical traceability. It is not the completion state for the reopened screenshot-critique pass.

## Reopened pass work log

The following records are the current implementation state for the screenshot-critique pass. Earlier records above remain historical evidence; they are not overwritten because they explain the original contracts and deferred security boundaries.

### CRIT-AUTH-004 / CRIT-MFA-005 / CRIT-SHELL-001 — unify authentication and remove duplicate page hierarchy

- **Status:** Resolved for the current route and shell contracts; live MFA lifecycle proof remains deferred under MFA-003.
- **Priority:** P1.
- **Affected page/component:** `AuthShell`, auth route layout, sign-in/password-recovery/setup/reset/enroll/recover/step-up/verify forms, and `TopBar`.
- **Before → problem:** Forgot Password and Reset Password had bare or inconsistent route presentation; MFA carried an oversized transaction/input treatment; ML Health and User Management repeated their page title in both the shell and page body.
- **Research/principle:** W3C error identification and dialog guidance support semantic labels, explicit error association, and a clear transaction surface. OWASP supports generic recovery responses and avoiding unsupported recovery controls. The governing product principle is one restrained CyberTrace auth language rather than several route-specific templates.
- **Change:** Added one shared dark AuthShell and auth layout; centralized control sizing/focus/disabled treatment; repaired native password-recovery forms; kept one logical OTP field with paste/autofill/numeric semantics; recoverable MFA errors retain, focus, and select the value; terminal errors render a truthful restart; `TopBar.showTitle` removes duplicate page titles on ML Health/User Management.
- **Why better:** The required action is now dominant, every auth route has the same visual grammar, invalid codes can be corrected immediately, terminal challenges cannot look usable, and the shell no longer competes with page-level headings.
- **Validation:** Focused auth tests **PASS**, 6 files / 20 tests; later full suite **PASS**, 98 files / 619 tests; lint/typecheck/diff check **PASS**. Browser inspection covered desktop/narrow auth routes; authenticated `/mfa/verify` safely redirected to `/login` because no valid pre-auth challenge existed.
- **Commit:** `226a61f` — `fix(frontend): unify auth surfaces and shell hierarchy`.
- **Deferral:** MFA-003 remains deferred until a safe controlled challenge harness can exercise live wrong-code, expired, locked/exhausted, refresh, Back/Forward, and service-failure transitions without consuming real attempts.

### CRIT-ML-006 / CRIT-ML-007 — make ML Health an evidence-oriented operator surface

- **Status:** Resolved for the current model-health contract.
- **Priority:** P1.
- **Affected page/component:** `/ml-health`, `MLHealthWorkspace`, Overview, Diagnostics, view model, and module styles.
- **Before → problem:** Overview repeated health/monitoring/model information and exposed low-value source terminology; expanded evaluation and policy evidence competed side by side; Diagnostics mixed operational monitoring with evaluation; missing drift/calibration appeared as empty tables.
- **Research/principle:** Carbon data-table guidance gives dense tables the width they require; Grafana dashboard guidance favors meaningful grouping and deliberate information architecture; WAI-ARIA tabs guidance supports native tab semantics and keyboard movement. Missing telemetry must be represented as not reported, not inferred.
- **Change:** Overview now follows serving status → monitoring coverage → runtime snapshot → evidence. Diagnostics uses `Performance`, `Monitoring`, `Evaluation`, and `Policy`; evidence tables stack vertically; drift/calibration use explicit empty states; raw source-field tags/columns and redundant table-scroll copy were removed; the policy table keeps only configured bands and the Normal exception; the Model Operations link remains a separate control boundary.
- **Why better:** Operators can distinguish serving health from monitoring coverage and offline quality evidence at a glance, dense tables remain readable, absence is honest, and implementation details no longer receive equal prominence with operational facts.
- **Validation:** Focused ML tests **PASS**, 3 files / 16 tests; page assertion alignment **PASS**, 3 tests; later full suite **PASS**, 98 files / 619 tests; lint/typecheck/diff check **PASS**. Browser inspection opened Overview plus all four Diagnostics tabs at desktop and narrow widths and confirmed the real staged model identity and truthful not-reported states.
- **Commit:** `21ff300` — `fix(ml-health): simplify diagnostic evidence`; `5bbb2e6` — `test(ml-health): align page assertions`.

### CRIT-UMG-008 — make User Management lifecycle-first and progressively disclose mutations

- **Status:** Resolved for the current UI/route contract; the last-enabled-admin database invariant remains deferred under UMG-004.
- **Priority:** P1.
- **Affected page/component:** `/user-management`, `UserManagementWorkspace`, and `AccountActionsDialog`.
- **Before → problem:** The table spent space on Created and repeated row actions; lifecycle state and MFA wording were ambiguous; the drawer exposed role, MFA, email, and danger mutations simultaneously.
- **Research/principle:** GOV.UK summary-list guidance supports compact key/value facts for a small account set; Carbon data-table guidance supports contextual row entry and progressive detail; WAI-ARIA dialog guidance requires a visible close path and focus containment.
- **Change:** The table now contains Account, Role, Lifecycle, and MFA; account identity opens details; lifecycle combines enabled/setup/email state; the summary is compact and table-first; role editing, MFA reset/reason, email replacement, and the danger zone open only when requested; the drawer uses a lighter scrim and an explicit close button; labels use `Enrolled`, `Not required`, and `Enrollment required`.
- **Why better:** Administrators can scan access state first, preserve list context, and see only actions relevant to the selected account. Destructive and security-sensitive controls are no longer visually equal to routine inspection.
- **Validation:** Focused User Management tests **PASS**, 7 files / 31 tests; lint/typecheck/diff check **PASS**. Browser desktop/narrow review covered search, empty/search semantics, drawer facts, progressive action entry points, and safe invite/confirmation rendering; no destructive or security mutation was submitted.
- **Commit:** `e1e0fa4` — `fix(user-management): focus lifecycle and safe actions`.
- **Deferral:** UMG-004 remains deferred because the existing database function does not enforce the last-enabled-ADMIN invariant; adding that guarantee would require an approved database-function change.

### CRIT-CROSS-009 — reduce shared dashboard and alert chrome

- **Status:** Resolved for the audited Dashboard and Alerts surfaces.
- **Priority:** P2.
- **Affected page/component:** Dashboard stat/distribution composition, Alerts filter bar, Alerts table headers and mobile overflow region.
- **Before → problem:** Dashboard presented each metric and distribution as its own bordered card, included decorative response-policy chrome, and used tiny tracked labels. Alerts added a redundant mobile scroll banner and nested the filter controls inside another card.
- **Research/principle:** Mature dashboard/table guidance favors grouping by operator task, readable sentence-case labels, and giving dense data the width it needs. The product principle is to use borders for real work surfaces, not for every content fragment.
- **Change:** Dashboard metrics share one divided summary strip; distribution content shares one divided surface; headers are sentence case; decorative response-policy ornament was removed. Alerts filters are an unframed control rail, table headers are readable sentence case, and the accessible scroll region remains the table’s structural affordance without a redundant banner.
- **Why better:** The pages now have clearer visual grouping, less card noise, and more room for the actual metrics/alerts while preserving existing filters, sorting, selection, pagination, and drawer behavior.
- **Validation:** Dashboard tests **PASS**, 7 files / 35 tests; Alerts tests **PASS**, 6 files / 47 tests; lint/typecheck/diff check **PASS**. Browser desktop/narrow review confirmed the summary strip, filter rail, populated table, and narrow horizontal table behavior.
- **Commit:** `b9acce5` — `fix(dashboard): reduce summary chrome`; `2c28c30` — `fix(alerts): simplify table guidance`.

### CRIT-CROSS-009 / CRIT-VALID-010 — make unavailable Model Operations truthful and actionable

- **Status:** Resolved for the available local state.
- **Priority:** P1/P2.
- **Affected page/component:** `/ml-model`, `MLModelWorkspace`, and `MLModelWorkspace.module.css`.
- **Before → problem:** The 503/unavailable route rendered a sparse centered message with no domain framing or adjacent safe next step.
- **Research/principle:** Error-state guidance favors explaining the current boundary, preserving a clear retry action, and offering a relevant route without fabricating data. The Model Operations control boundary must remain separate from observational ML Health.
- **Change:** The unavailable branch now has a lifecycle status marker, semantic heading, honest explanation, retry action, and a `Review ML Health` link. It remains a 503/unavailable state; no run, model, or control status was invented. The shell composes as a bordered work surface on desktop and a stacked panel at 390px.
- **Why better:** Operators understand what is unavailable and what they can do next without mistaking an empty page for a successful no-run state.
- **Validation:** Model Operations tests **PASS**, 1 file / 13 tests; full suite **PASS**, 98 files / 619 tests; lint/typecheck/build/diff check **PASS**. Browser desktop/narrow review confirmed the heading, retry button, health link, and responsive stacking.
- **Commit:** `7a01746` — `fix(ml-model): make unavailable state actionable`.

### Final validation record

- **Branch/worktree:** `codex/ml-health-admin-mfa-remediation` in the requested worktree; current source HEAD after the documentation commit is recorded in the header above. Existing untracked `output/` evidence was preserved and never staged.
- **Full checks:** `npm test -- --run --pool=threads` **PASS**, 98 files / 619 tests; `npm run lint` **PASS**; `npm run typecheck` **PASS**; `npm run build` **PASS** with Next.js 16.2.11 and all application routes generated; `git diff --check` **PASS**.
- **Runtime:** Backend `GET /health` returned `{"status":"healthy","database":"connected","notification_worker":"healthy"}`. Authenticated browser ML Health showed the real staged model `distilbert_v3_907k_cleaned_20260312_133755` and healthy serving. The in-app browser route inspection did not expose a HAR or layout-shift metric, so those remain unavailable rather than inferred.
- **Browser coverage:** Desktop and narrow states were inspected for Dashboard, Alerts, ML Health, Model Operations, User Management, Sign In, Forgot Password, Reset Password, MFA enrollment/recovery/step-up, and the safe no-preauth MFA verification redirect. User Management and alert/model controls were inspected without submitting destructive or externally meaningful mutations.
- **Remaining meaningful deferrals:** UMG-004 (last-enabled-admin database invariant) and MFA-003 (controlled live challenge lifecycle harness) remain explicit. Remaining concerns are P3 taste, unsupported live states, or work outside this thesis/capstone scope.

### Reopened pass commit log

| Commit | Finding group | Validation | Status |
| --- | --- | --- | --- |
| `226a61f` | Shared auth surface, auth controls, MFA sizing, and page-title de-duplication | 6 files / 20 focused tests PASS; lint/typecheck/diff check PASS; browser desktop/narrow auth review | Resolved; MFA-003 deferred |
| `21ff300` | ML Health Overview/Diagnostics evidence hierarchy and table composition | 3 focused files / 16 tests PASS; lint/typecheck PASS; browser desktop/narrow tabs and states | Resolved |
| `e1e0fa4` | User lifecycle table, drawer hierarchy, progressive safe actions | 7 focused files / 31 tests PASS; lint/typecheck PASS; browser desktop/narrow review | Resolved; UMG-004 deferred |
| `b9acce5` | Dashboard summary and distribution chrome | 7 files / 35 tests PASS; lint/typecheck/diff check PASS; browser desktop/narrow review | Resolved |
| `2c28c30` | Alerts filter/table chrome and mobile guidance | 6 files / 47 tests PASS; lint/typecheck/diff check PASS; browser desktop/narrow review | Resolved |
| `7a01746` | Model Operations unavailable state | 1 file / 13 focused tests PASS; lint/typecheck/build PASS; browser desktop/narrow review | Resolved |
| `5bbb2e6` | ML Health page tests aligned to the final tab vocabulary | 3 page tests PASS; included in full suite | Resolved |
| `8e7a431` | MFA retry-selection assertion waits for the documented focus effect | 7 MFA tests PASS; included in full suite | Resolved |
| `1b05227` | Current remediation ledger and final validation record | Full suite 98 files / 619 tests PASS; lint/typecheck/build/backend health/browser review | Recorded |

## Completion state

The reopened screenshot-critique implementation is complete for the local branch scope. All meaningful in-scope P0/P1/P2 findings are resolved or explicitly deferred with a concrete contract/environment reason. The final browser review covered the required pages at desktop and narrow widths, preserved truthful backend/security behavior, and did not fabricate unsupported ML, MFA, or administrative states. Remaining work is limited to the two explicit boundary deferrals, P3 taste, unsupported live-state harness coverage, or unrelated enterprise/architecture expansion.

## Reopened screenshot review pass (primary critique)

**Status:** In progress. This section reopens the prior completion claim against the new screenshot critique. The first pasted review, `C:\Users\froi\.codex\attachments\0fb75f24-cabc-4412-8cb9-c46994594267\pasted-text.txt`, is the governing source. The supporting review, `C:\Users\froi\.codex\attachments\66147f2d-f0d9-4144-a329-6a30ed636a89\pasted-text.txt`, is used to corroborate findings and expose regressions, but cannot lower the primary review's priority.

### Execution contract

Re-inspect the actual rendered branch, trace each issue to its shared or local owner, research the relevant accessibility/design-system/security pattern, write a focused failing behavioral test where behavior changes, implement the smallest structural fix, validate with tests and the real browser, critique the rendered result again, and commit the coherent finding group. Preserve existing BFF/data/security contracts and represent missing telemetry or unavailable controls honestly. Do not use decorative UI, fabricated data, raw backend field names, or generic account/error copy to fill visual space.

### Reopened prioritized backlog

| ID | Priority | Scope | Acceptance contract |
| --- | --- | --- | --- |
| SHELL-011 | P1 | Shared utility bar, page headers, widths, typography, status/color semantics | Every dashboard route has one populated global utility bar and one page-level heading; page widths follow task density; status domains and semantic colors are distinguishable; no redundant title/count chrome. |
| DASH-013 | P1 | Dashboard zero-traffic composition | Empty traffic is neutral, compact, and useful; time range is stated once; empty charts have no decorative legend/placeholder; lower analytics do not dominate a no-data view; policy detail is not duplicated. |
| ALERT-014 | P1 | Alert table formatting and drawer hierarchy | Relative timestamps are readable; confidence/CRS precision is intentional; workflow and enforcement statuses are distinct; drawer is wider, sentence-case, evidence-first, and progressively discloses training/system mutations. |
| MLH-014 | P1 | ML Health Overview and Diagnostics | Serving health is visually primary; monitoring/evaluation absence is concise and truthful; runtime/evidence tables get required width; diagnostics tabs are compact and interpreted; no duplicate model/status/source-field language. |
| UMG-011 | P1 | User lifecycle and account drawer | Active/Pending setup/Disabled is explicit; account entry is an obvious control; list density is task-oriented; self-account restrictions are neutral inline guidance; mutation sections remain progressive. |
| AUTH-012 | P1 | Auth shell, Sign In, Forgot Password | Auth pages use one compact CyberTrace composition; form width and hierarchy are consistent; recovery copy is direct and enumeration-safe; no premature validation or oversized framing. |
| MFA-006 | P1 | MFA proportions and safe recovery path | Step 2 placement, input/control sizing, disabled/focus/error semantics are coherent; retry preserves recoverable input; terminal states remain terminal; a safe restart/recovery path is visible without weakening the challenge. |
| RESP-004 | P2 | Intermediate and narrow layouts | 1024/768 tabs and tables remain usable; narrow alert/account drawers are anchored within the viewport; dense evidence and tables reflow instead of being squeezed into competing columns. |
| DOC-006 | P2 | Evidence and implementation record | Research, decisions, validation, focused commits, remaining P0/P1/P2 findings, and exact browser evidence are recorded without presenting historical claims as current proof. |
| UMG-004 | P1 | Last-enabled-admin invariant | Preserve as an explicit deferral until an approved database-function change is authorized; UI self-protection must not be described as complete backend enforcement. |
| MFA-003 | P1 | Full live challenge lifecycle harness | Preserve as an explicit deferral if no safe controlled challenge exists for wrong-code, expired, locked/exhausted, refresh/back-forward, abandoned, and service-failure transitions; do not consume real attempts. |

### Research log for this pass

- WAI-ARIA Tabs recommends one active panel at a time with native tab/list/panel semantics and predictable keyboard movement; this supports compact Diagnostics navigation rather than four oversized cards. [W3C APG Tabs](https://www.w3.org/WAI/ARIA/apg/patterns/tabs/)
- WAI-ARIA Dialog recommends a contained focus path, Escape handling, an accessible name, and a visible close/cancel path; this informs the account and alert drawer composition. [W3C APG Dialog](https://www.w3.org/WAI/ARIA/apg/patterns/dialog-modal/)
- Carbon's empty-state guidance says an empty state replaces the ordinary content element and should not retain meaningless table headers or repeated placeholders; this informs dashboard, monitoring, drift, and calibration absence states. [Carbon empty states](https://carbondesignsystem.com/patterns/empty-states-pattern/)
- Grafana's dashboard guidance supports showing or hiding panels based on query results so zero-data views do not reserve a large dashboard area for panels with no operational value. [Grafana dashboards](https://grafana.com/docs/grafana/latest/visualizations/dashboards/build-dashboards/create-dashboard/)
- GOV.UK's Summary List guidance supports compact key/value facts for small record summaries, while its error-message guidance requires explaining what went wrong and how to recover while associating the message with the relevant field. [Summary list](https://design-system.service.gov.uk/components/summary-list/), [Error message](https://design-system.service.gov.uk/components/error-message/)
- Primer's state-label and color guidance supports consistent semantic status labeling, 4.5:1 contrast, 320px reflow, and functional color roles instead of assigning the same accent to navigation, focus, warning, and enforcement. [State label accessibility](https://primer.style/product/components/state-label/accessibility/), [Color usage](https://primer.style/product/getting-started/foundations/color-usage/)
- OWASP and NIST guidance support generic account-recovery responses, clear but non-enumerating authentication errors, and recovery/expiry behavior consistent with the assurance level of the authenticator. [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html), [OWASP MFA Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Multifactor_Authentication_Cheat_Sheet.html), [NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html)

### Pass tracking

The implementation will append a dated entry for each focused group below with the before/problem, research principle, changed files/components, browser-visible result, tests, commit, and any remaining uncertainty. Historical entries above remain historical; they are not reused as proof that the reopened screenshot findings are resolved.

### 2026-08-26 — MLH-014 snapshot evidence hierarchy

- **Status:** Implemented; authenticated visual verification remains unavailable in this checkout because the current in-app browser session redirects protected routes to `/login`.
- **Before → problem:** ML Health repeated model/status context, used oversized diagnostic tabs, exposed source/endpoint wording, treated unavailable latency as a measured-looking value, and kept baseline/change columns even when no baseline existed. Expanded evidence could also force wide content into competing horizontal columns.
- **Research/principle:** WAI-ARIA APG tabs supports a compact roving-focus tab list with one active panel; Carbon empty-state guidance supports replacing meaningless empty table content with an honest state; Grafana dashboard guidance supports giving useful data the space it requires and reducing empty panels. The product decision was to prioritize operator conclusions over backend provenance vocabulary.
- **Implementation:** `MLHealthWorkspace` now uses the shared `PageHeader`, keeps one model identity and one compact freshness line, and removes the redundant `View` label and diagnostic model identity. `MLHealthWorkspaceViewModel` now exposes `hasTraffic` and `distributionHasBaseline`, uses concise unavailable/provenance text, applies the backend’s low/high/critical threshold semantics with readable ranges, and orders known prediction classes (`Normal`, `SQL Injection`, `Code Injection`, `Other Attacks`) before unknown classes. `MLHealthOverviewSection` removes redundant evidence eyebrow labels, uses sentence-case availability states, and avoids monospace styling for unavailable values. `MLHealthDiagnosticsSection` uses flat tabs, stacks evidence, hides baseline/change columns without a baseline, and gives zero-traffic performance a direct explanation. Module CSS reduces status-hero/tab/table density and improves helper-text contrast while preserving visible focus states.
- **Tests:** Focused ML suite **PASS**, 4 files / 20 tests; `npm run lint` **PASS**; `npm run typecheck` **PASS**; `git diff --check` **PASS**.
- **Browser evidence:** Direct protected-route inspection attempted at `/ml-health`; it redirected to `/login` because no valid authenticated session was available. No authenticated screenshot is claimed for this pass.
- **Commit:** `902ca23` — `fix(ml-health): clarify snapshot evidence hierarchy`.
- **Follow-up:** Recheck the authenticated Overview and all four Diagnostics tabs at desktop and narrow widths when a safe session is available; confirm the real staged model identity and no horizontal competition between stacked evidence tables.
