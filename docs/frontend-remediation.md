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
| MFA-002 | Recoverable wrong-code handling preserves the logical value but does not explicitly return focus or make replacement easy after the error. | MFA / recovery, keyboard, accessibility | Open | Current form retains `code` after a failed response and associates the error, but has no error-focus/select behavior. Research accessible OTP retry patterns; add focused regression coverage and preserve paste/autofill/mobile numeric behavior. |
| MFA-003 | MFA state-machine coverage is incomplete at the rendered surface for wrong code, expired, exhausted/locked, service failure, abandoned, refresh, Back/Forward, and duplicate submit. | MFA / auth state machine | Investigate | Route guard correctly rejects fully authenticated access. Inspect backend error codes and existing recovery routes before exposing or changing any terminal/restart UI. Do not add unsupported paths. |
| MFA-004 | Terminal challenge states need a truthful safe exit/restart action if the current protocol supports one; a visual Back link must not be added with incorrect security semantics. | MFA / security UX | Investigate | Inspect login actions, pre-auth cookie lifecycle, `/mfa/recover`, and backend challenge semantics. Implement only a supported “sign in again”/restart equivalent. |
| UMG-001 | Account lifecycle is reconstructed from separate `Enabled`, email verification, and MFA fields rather than showing the actual access/setup state clearly. | User Management / lifecycle IA | Open | Current table shows two enabled verified ADMIN accounts and drawer labels. Confirm backend fields for pending setup/invitation and use concise product-level state only when authoritative. |
| UMG-002 | `Resend setup email` is rendered for every account, including active accounts where setup is complete. | User Management / eligibility, security UX | Open | `AccountActionsDialog.tsx` always renders the action. Confirm setup eligibility field/API behavior; hide or replace the action when setup is no longer incomplete. |
| UMG-003 | Role changes are applied immediately from a select without explicit edit/save/cancel or a consequence review. | User Management / mutation safety | Open | `onChange` calls the mutation directly. Research mature admin role-edit patterns and verify role/MFA consequences and server authorization before implementing a deliberate edit state. |
| UMG-004 | Security-sensitive account actions do not visibly encode self/last-usable-admin protections or session consequences. | User Management / authorization UX | Investigate | Inspect backend authorization and current account identity/session behavior. Implement only protections supported by actual authorization rules; document unsupported immediate session revocation rather than implying it. |
| UMG-005 | MFA reset and email-change workflows need complete eligibility, consequence, pending, success, failure, correction, and cancellation semantics. | User Management / recovery, security UX | Investigate | Existing actions are present, but the contract does not yet prove all lifecycle transitions. Inspect route handlers and safe non-mutating render states; never mutate hosted accounts for evidence. |

### P2 — information architecture, density, coherence, maintainability

| ID | Finding | Surface/category | Status | Evidence and next decision |
| --- | --- | --- | --- | --- |
| MLH-001 | Expanded evaluation evidence and confidence policy are side-by-side dense sections that compete for horizontal width. | ML Health / tables, responsive density | Confirmed | Reproduced at 1440×900: two ~538px regions and ~502px tables. Research mature observability/table patterns; stack or recompose the sections so detailed comparison has readable width. |
| MLH-002 | ML Health still carries a repeated eyebrow/section-label recipe and repeated explanatory copy that weakens hierarchy. | ML Health / visual restraint, content density | Open | Current text includes `Model observability`, `Serving answer`, `What is known now`, `Current snapshot`, `Progressive detail`, and source restatements. Remove only copy that does not add interpretation, recovery, or provenance. |
| MLH-003 | Overview presents `Load state` and `Fallback` as “Not reported by endpoint,” although these fields have no operational meaning in the current contract. | ML Health / truthfulness, content | Open | Current browser confirms both fields. Remove/demote unsupported fields or expose them only as a clearly technical unavailable detail; do not fabricate load/fallback state. |
| MLH-004 | Evaluation/calibration evidence lacks enough visible applicability/provenance to establish that it describes the active model. | ML Health / evidence semantics | Investigate | Current evidence lists per-class F1 and four classes but no evaluation model/run/timestamp. Inspect backend contract/artifact metadata; prefer “no applicable evaluation” or provenance-unclear over inference. |
| MLH-005 | Freshness semantics distinguish neither reported-at nor retrieved-at in the visible snapshot. | ML Health / observability semantics | Investigate | Browser says “No report timestamp supplied.” Confirm available fields and label only what the endpoint actually reports; represent stale/unavailable/not-evaluated separately. |
| MLH-006 | Overview evidence disclosure architecture creates card/border density and may duplicate Diagnostics rather than serving as a concise attention-to-investigation bridge. | ML Health / IA, component boundaries | Open | Compare Overview and Diagnostics content. Keep Overview focused on “what needs attention?” and link/open evidence without repeating full datasets. |
| MLH-007 | Diagnostics tables and tabs need a full width/keyboard/responsive audit, including performance/serving, drift, calibration, policy, model identity, and unavailable/empty states. | ML Health / accessibility, tables, responsive | Open | Source has four diagnostic tabs and horizontal-scroll hint. Verify tab keyboard behavior, focus, table scan order, and truthful absent-state composition at desktop and narrow widths. |
| MLH-008 | Model Operations and ML Health boundaries need a cross-link/audit so observation does not duplicate activation, rollback, retraining, or policy control. | ML Health + Model Operations / IA | Investigate | `/ml-model` currently shows a truthful unavailable state. Inspect links and control surfaces before adding or removing navigation. |
| MLH-009 | Legacy ML Health chart/header components may be dead source and should be removed only after a final repository-wide reference audit. | ML Health / maintainability | Investigate | Existing design identifies six candidate unreferenced components. Search imports, dynamic references, tests, exports, CSS, and build config before any deletion; make cleanup a separate commit. |
| UMG-006 | User summary KPIs may spend prime visual space on counts that do not answer a useful administrative decision for a two-account population. | User Management / density | Open | Browser shows three large summary values. Compare compact summary, table-first, and lifecycle-oriented alternatives against actual admin job and data volume. |
| UMG-007 | Mutation feedback is generic (`Role updated`, `Account disabled`, etc.) and does not consistently identify target or consequence. | User Management / feedback | Open | `UserManagementWorkspace.tsx` notices lack account name/email in several paths. Change messages to specific, truthful target/action/consequence feedback. |
| UMG-008 | Empty account state is not distinguished from filtered-empty state, and search scope/zero-result wording needs verification. | User Management / empty/search | Open | Current workspace always renders “No accounts match this search.” Inspect initial zero-account data path and searched fields; add separate states without fabricating account data. |
| UMG-009 | Email-change display needs explicit pending/proposed/verified semantics and only supported correction/cancellation actions. | User Management / lifecycle | Investigate | Contract exposes `pending_email` but drawer has a request form. Verify route semantics and present the state machine without unsupported controls. |
| UMG-010 | Admin drawer uses a border/card stack and immediate control changes whose hierarchy should be audited against productive density and dangerous-action placement. | User Management / visual hierarchy | Open | Current drawer has multiple bordered sections and a danger region. Refine only after action eligibility/consequence work is settled. |
| FOUND-001 | Shared typography and page composition are not yet a single intentional product language. | Cross-product / foundations | Open | `globals.css` defines Inter plus Orbitron/IBM utility families; login uses Orbitron and a separate background/card treatment while dashboard surfaces use a different shell. Audit Dashboard, Alerts, ML Health, Model Operations, User Management, and auth together before changing tokens. |
| FOUND-002 | Semantic roles for warm accent, selection, primary action, warning, and degraded states need a rendered cross-product audit. | Cross-product / color, status | Investigate | Tokens distinguish action/warning, but ML Health uses accent action for state labels and multiple legacy aliases remain. Confirm visible collisions before consolidating. |
| FOUND-003 | Borders, cards, uppercase labels, badges, icons, and explanatory copy are applied inconsistently across mature and newly redesigned surfaces. | Cross-product / visual restraint | Open | Use Dashboard/Alerts as references but do not preserve inconsistencies merely because they are older. Apply smallest shared-token/primitive change only after repeated reuse is proven. |
| FOUND-004 | Responsive transformations, focus visibility, text scaling, dialogs/drawers, tables, and mobile navigation need a deliberate cross-product audit rather than desktop stacking assumptions. | Cross-product / responsive accessibility | Open | Existing Alerts and User Management use horizontal table guidance; Sidebar uses a mobile dialog. Inspect at desktop, narrow desktop/tablet, and mobile widths with keyboard/focus checks. |
| FOUND-005 | The login surface remains visually and semantically separate from the current MFA shell, including background image, logo/icon density, placeholder-led fields, and button semantics. | Auth / coherence, accessibility | Open | `/login` is a full-screen image/card composition with sr-only labels and a click handler rather than a semantic form. Decide whether a focused auth-foundation slice is required for MFA coherence without expanding into unrelated auth redesign. |
| FOUND-006 | Loading, stale, empty, unavailable, degraded, permission, pending, success, and error states need a route-by-route inventory and browser proof. | Cross-product / states | Open | Current ML Health and Model Operations have explicit unavailable/no-traffic states; Dashboard was observed loading. Complete the inventory and fix only meaningful gaps. |
| FOUND-007 | Browser/runtime validation must include network, console, duplicate requests, layout shift, and interaction latency for affected surfaces. | Cross-product / performance | Open | Establish clean console/network baseline and compare after each focused group. Do not optimize unobservable micro-costs. |

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
| RES-008 | MFA form lacked semantic submit/OTP attributes/error association. | Current form uses `<form>`, `one-time-code`, numeric input mode, pattern, labels, and `aria-describedby`; wrong-code focus/retry remains open. |
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
| _pending_ | Remediation ledger | `git diff --check`, document review | In progress |

## Final gate

Do not call the redesign complete until all meaningful in-scope P0/P1/P2 findings are resolved or defensibly deferred, the fresh Dashboard/Alerts/MFA/ML Health/Model Operations/User Management audit is recorded, and the relevant frontend tests, BFF tests, lint, typecheck, build, browser desktop/narrow/keyboard/state/network/console checks, backend checks for any changed contracts, and `git diff --check` have fresh evidence. Remaining issues must be P3 taste, speculative future capability, or unrelated scope.
