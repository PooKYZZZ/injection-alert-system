# Batch 2 Audit: Auth/sign-in retry and provider/session gating

## 1. Batch summary

### What this batch is supposed to do
- Remove hidden action replay and event-bus style retry behavior from sign-in prompting.
- Make sign-in-required behavior explicit: user is asked to sign in, then manually retries from the alert panel.
- Tighten auth defaults so production does not silently run with weak/default secrets.
- Keep provider wiring simple and avoid stale invalidation side effects.
- Keep user-facing outcomes distinguishable for wrong password vs non-credential failures.

### Why this batch is risky
- It touches auth bootstrap and runtime secret handling (`auth.ts`), which can hard-fail the app at startup.
- It modifies top-level app provider composition (`app/providers.tsx`), where subtle wiring mistakes affect all authenticated UX.
- It changes sign-in entry behavior (`app/(auth)/login/page.tsx`) that controls user trust and error semantics.
- It replaces event-driven retry logic with a context/toast flow (`components/SignInToast.tsx`), where hidden side effects and stale assumptions are common.

### Main files
- `frontend/auth.ts`
- `frontend/app/providers.tsx`

### Supporting files
- `frontend/app/(auth)/login/page.tsx`
- `frontend/components/SignInToast.tsx`

### Tests that are supposed to prove this behavior
- `frontend/app/providers.test.tsx`
- `frontend/components/SignInToast.test.tsx`
- `frontend/app/(auth)/login/page.test.tsx`
- `frontend/features/alerts/queries.test.tsx` (integration-adjacent proof that 401 intent surfaces sign-in toast and avoids raw-401 invalidation)

### Test execution evidence collected during this audit
- `npx vitest run --pool=threads app/providers.test.tsx components/SignInToast.test.tsx features/alerts/queries.test.tsx` => PASS (3 files, 3 tests)
- `npx vitest run --pool=threads app/(auth)/login/page.test.tsx` => FAIL (5/5 tests)
- Primary failure cause in `login/page.test.tsx`: test expects labeled password field (`getByLabelText('Password')` and id linkage), but page currently has unlabeled input.

## 2. Files audited
- `frontend/auth.ts`
- `frontend/app/providers.tsx`
- `frontend/app/(auth)/login/page.tsx`
- `frontend/components/SignInToast.tsx`

Additional evidence files read for cross-checking behavior assumptions:
- `frontend/app/providers.test.tsx`
- `frontend/components/SignInToast.test.tsx`
- `frontend/app/(auth)/login/page.test.tsx`
- `frontend/features/alerts/queries.ts`
- `frontend/features/alerts/queries.test.tsx`
- `frontend/app/(auth)/login/actions.ts`
- `frontend/auth.config.ts`
- `frontend/proxy.ts`

## 3. Findings

### Critical

1. Login page proof suite is broken and currently merge-blocking.
- File: `frontend/app/(auth)/login/page.tsx`
- Evidence: `frontend/app/(auth)/login/page.test.tsx` fails 5/5 tests.
- Root issue: tests require explicit label/id semantics for password input; implementation has no `<label>` and no `id` on the password input.
- Risk: sign-in UX behavior is no longer test-proven for wrong-password, fallback error, re-enable flow, and redirect-error handling.
- Why hostile: this removes executable confidence in the exact flow this batch claims to harden.

2. Sign-in toast can silently fail to navigate when popups are blocked.
- File: `frontend/components/SignInToast.tsx`
- Code path: `handleSignIn()` uses `window.open(..., '_blank')` inside try/catch; fallback only triggers on thrown error.
- Risk detail: browsers can return `null` for blocked popup without throwing. In that case, no fallback `window.location.assign(...)` runs, toast closes, and user receives no sign-in.
- Impact: user believes "Sign in" was triggered, but session-required flow is not actually executed.
- Why hostile: violates explicit/honest sign-in-required behavior.

### High

3. Callback URL is generated and passed but not consumed by login action flow.
- Files: `frontend/components/SignInToast.tsx`, `frontend/app/(auth)/login/actions.ts`
- Behavior observed:
  - Toast sends user to `/login?callbackUrl=<current-url>`.
  - `loginAction()` always calls `signIn(..., { redirectTo: '/dashboard' })` and does not read callback URL.
- Risk: flow implies context-preserving return mechanics that do not exist; introduces dead intent and confusion.
- Why hostile: this is "hidden indirection" in auth UX and can mislead operators during incident handling.

4. Auth boot now hard-fails without configured secret (security-positive but availability-sensitive).
- File: `frontend/auth.ts`
- Change: removed default secret fallback and now throws if neither `AUTH_SECRET` nor `NEXTAUTH_SECRET` is set.
- Security posture: improved.
- Operational risk: misconfigured environments fail startup immediately with no degraded auth mode.
- Why hostile: if deployment/config discipline is uneven across envs, this is an outage-class change.

### Medium

5. Unavailable-auth and generic server failure are collapsed into one user message.
- File: `frontend/app/(auth)/login/page.tsx`
- Behavior: only two UI outcomes from page-level logic:
  - `INVALID_CREDENTIALS` => "Incorrect password"
  - all else => "Unable to sign in right now"
- Risk: required distinctions (wrong password vs unavailable auth vs other failure) are not explicit to user/operator.
- Why hostile: triage clarity suffers during auth incidents.

6. Session/provider gating remains implicit rather than visibly modeled at provider layer.
- File: `frontend/app/providers.tsx`
- Behavior: provider stack includes QueryClient + SignInToast context; no explicit session provider here.
- Notes:
  - Repo currently appears to gate auth via NextAuth middleware and server-side `auth()` checks in API routes.
  - This may be acceptable architecture, but provider-layer intent is not self-evident and can confuse future maintainers expecting client session context.
- Risk: maintenance and future regressions, not immediate exploitability.

### Positive findings (risk removed)

7. Event-bus replay path appears removed from provider and toast flow.
- Files: `frontend/app/providers.tsx`, `frontend/components/SignInToast.tsx`
- Evidence:
  - No `action-retry-success` listener in providers path.
  - No retry button or hidden fetch replay in toast component.
  - `providers.test.tsx` explicitly asserts no listener registration.
  - `SignInToast.test.tsx` asserts informational/redirect-only behavior and no fetch invocation.
- Effect: reduces hidden mutation/replay side effects and stale invalidation coupling.

## 4. High-risk files in this batch
- `frontend/app/(auth)/login/page.tsx`
  - Test proof collapse (5/5 failures), ambiguous unavailable-auth semantics.
- `frontend/components/SignInToast.tsx`
  - Popup-block silent failure path, callbackUrl indirection mismatch.
- `frontend/auth.ts`
  - Startup hard-fail on missing secret (secure but availability-critical).

## 5. Files that appear disciplined
- `frontend/app/providers.tsx`
  - Lean provider composition; removed event-bus invalidation complexity.
- `frontend/auth.ts`
  - Correctly eliminates insecure default secret fallback.
- `frontend/components/SignInToast.tsx`
  - Successfully removes hidden action replay and stale invalidation/event dispatch behavior.

## 6. Questions or ambiguities needing cross-batch verification
- Is callbackUrl support intentionally deferred, or should login action consume callbackUrl to complete honest context-return semantics?
- Is there an explicit requirement for a third user-facing auth state ("auth service unavailable") beyond generic sign-in failure messaging?
- Are deployment environments guaranteed to set `AUTH_SECRET`/`NEXTAUTH_SECRET` consistently, and is there CI/CD gating for that?
- Is client-side session provider intentionally excluded project-wide, with server/middleware-only gating as the documented standard?
- Should popup-block behavior be considered a mandatory resilience requirement for SOC workflows?

## 7. Batch verdict
- Verdict: **FAIL (merge-blocking for this batch)**
- Rationale:
  - Core sign-in page behavior is not test-proven due complete suite failure.
  - Sign-in toast has a silent navigation failure mode under popup blocking.
  - Callback URL semantics are inconsistent, indicating residual flow indirection.
- Security note:
  - Secret hardening in `auth.ts` is a positive security improvement, but must be paired with verified environment readiness.
