# CyberTrace Login Turnstile Re-audit

**Audit date:** 2026-11-05
**Branch base:** `origin/master` at `3542838a2225db95e79e6528e21ceb5352a06d4e`
**Scope:** Auth.js password sign-in, account lookup/throttling, Turnstile, login UI, MFA/recovery, CSP, database RPC/migration patterns, deployment ingress, and the disposable auth E2E harness.

This is a source and configuration audit. It does not establish live Cloudflare rule settings, production secrets, a deployed database schema version, or successful production login enforcement.

## Findings matrix

Line references below describe the branch before implementation and may move as the feature is added.

| ID | Status | Rechecked evidence and correction |
| --- | --- | --- |
| F01 | Confirmed | `frontend/lib/auth/login-throttle.ts` (`LoginThrottle.check`, `recordFailure`) is called by `frontend/auth.ts` inside the Credentials provider's `authorize` callback. The default threshold is five, with 300-second window and cooldown. The check and later failure update are separate, so concurrent attempts can all pass before the failure count changes. |
| F02 | Confirmed | `LoginThrottle` stores rows in a per-process `Map` (`login-throttle.ts`, lines 71-105). A fresh instance has no state (covered in `login-throttle.test.ts`). Browser refresh on the same process does not clear the map; process restart, replica changes, or eviction can. |
| F03 | Confirmed | `globalMaxFailures`, `globalWindowMs`, and `globalCooldownMs` exist in the options and environment loader (`login-throttle.ts`, lines 25-30 and 181-188), but no enforcement reads them. They are misleading configuration, not a working global limiter. A global lockout bucket is not selected because it could deny unrelated accounts. |
| F04 | Confirmed | `shouldRequireTurnstile` and `verifyTurnstileToken` exist (`frontend/lib/auth/turnstile.ts`, lines 5 and 15), but repository search found no password-login call site. The helper accepts up to 4096 characters, has no timeout, and does not require a configured expected hostname. |
| F05 | Confirmed | Auth.js `authorize` is the password enforcement point (`frontend/auth.ts`, lines 72-164); `frontend/app/api/auth/[...nextauth]/route.ts` exposes the same Auth.js handlers. Protection only in the login Server Action would be bypassable. |
| F06 | Confirmed | `parseCredentialMode` distinguishes password, MFA completion, and recovery completion (`frontend/lib/auth/credential-mode.ts`, lines 43-87). The two completion modes return before password processing in `authorize`; they must remain separate. |
| F07 | Confirmed | `loginAction` currently maps all `CredentialsSignin` errors to `INVALID_CREDENTIALS` (`frontend/app/(auth)/login/actions.ts`). `LoginForm` has no challenge state or token field (`login-form.tsx`). |
| F08 | Partially confirmed | Source CSP is built in `frontend/next.config.ts` and has no Turnstile host. A read-only public `GET /login` on 2026-11-05 returned HTTP 200 through Cloudflare and an effective CSP matching the source. Cloudflare dashboard rules, other hostname policies, and future proxy transformations remain unverified. |
| F09 | Confirmed | `findAuthAccountByIdentifier` supports UUID, email, and username (`frontend/lib/server/db/auth-accounts.ts`, line 219 onward); current throttling hashes only the normalized submitted identifier. Case/whitespace normalization helps equivalent spellings but does not make the three aliases share a counter. |
| F10 | Confirmed | Existing Turnstile and throttle tests exercise their helpers, not the real `authorize` flow. Baseline targeted auth tests passed (6 files, 57 tests); they do not establish a conditional challenge or database concurrency invariant. |
| F11 | Confirmed | `frontend/.env.example` already has the server-only enable flag, secret, and expected hostname at lines 45-47. No public widget site key is documented. The feature flag defaults to false in the auth E2E environment. |
| F12 | Partially confirmed | `frontend/lib/auth/login-audit.ts` omits raw identifiers, passwords, and tokens. It logs a plain SHA-256 `identifier_hash`, which is vulnerable to offline dictionary matching for common usernames/emails if logs leak. The production log sink and retention are not available for inspection. |
| F13 | Confirmed | The app uses a server-only Supabase service-role client and narrow RPC calls (`frontend/lib/server/db/client.ts` and existing DB adapters). Migration functions use `SECURITY INVOKER`, an empty `search_path`, and restricted grants. The Playwright harness creates a labeled, disposable PostgreSQL/PostgREST environment and applies the real Alembic chain. No Redis or additional package is needed. |
| F14 | Confirmed | `frontend/package.json` currently requires Node 24, Next 16, Auth.js v5, React 19, Vitest, and Playwright. The audit did not find a dependency requirement for this feature. |

## Independent second-pass corrections

1. **Shared limiter elsewhere:** Repository searches found no other account-aware login limiter or auth-specific rate-limit RPC. The repository documents Cloudflare Tunnel ingress, but not the active Cloudflare rate-limit rule configuration. Edge controls are therefore unverified and cannot be counted as authoritative login enforcement.
2. **Challenge dead-end:** A challenge first required at failure five would appear after the existing five-failure block has already rejected the attempt. The selected policy requests the challenge on the next password attempt after three failed passwords and preserves the five-failure cooldown.
3. **Identifier aliases:** Existing counters are per submitted identifier. Known accounts must use the canonical account UUID for shared state; unknown identifiers must not create durable attacker-controlled rows.
4. **Direct callback:** The Auth.js route reaches the same `authorize` callback. The challenge decision and Siteverify call must live there, not only in a Server Action or React state.
5. **Effective CSP:** The source CSP and public login response matched during the read-only GET. This does not prove every Cloudflare rule or response transformation.
6. **Targeted lockout:** The existing five-failure/five-minute behavior can still be abused to temporarily inconvenience a targeted account. The new challenge is step-up friction at three failures, not a replacement for or reset of the cooldown. No global failure counter is added. The residual account-lockout risk is explicit; successful authentication resets the canonical account state.
7. **MFA and recovery:** MFA/recovery completion are distinct credential modes and are not password attempts. They remain unchanged. A successful password check still initiates the existing MFA challenge when required.
8. **Database pressure and races:** A check-then-record sequence is not atomic. The design uses a per-account row lock plus a short-lived attempt reservation before Argon2 and an idempotent completion operation. Each known-account password attempt adds DB calls; the existing account lookup already requires the same Supabase store. DB failure denies password authentication safely.
9. **Provider/store failure:** Turnstile validation will use a bounded timeout and fail closed when a challenge is required. Supabase throttle failures also fail closed. The UI returns a generic retry message and resets a submitted widget token; it does not disclose account existence or upstream details.
10. **Cloudflare ingress alternative:** An edge challenge/rate rule cannot, on current repository evidence, unify email/username/UUID identity or prove coverage of direct Auth.js POSTs. It may remain defense in depth, but it is not the selected authorization control.

## Threat model

**Protected asset:** the ability to guess credentials against an existing CyberTrace account without first completing a risk-triggered challenge or reaching the existing temporary cooldown.

**Threat actors and paths:** credential-stuffing scripts, password sprayers, direct Auth.js POST callers, alias rotation across email/username/UUID, concurrent requests across app instances, and requests that omit/replay a Turnstile token. Attackers may control request headers, so `X-Forwarded-For` and `CF-Connecting-IP` are not treated as trusted identity signals.

**Chosen controls:** server-side state keyed by canonical account ID for known accounts; atomic attempt reservation before Argon2; a Turnstile challenge after three failures; the existing five-failure/300-second window and 300-second cooldown; server-to-server Siteverify with action, hostname, token-size, timeout, and one-use validation; and unchanged MFA/recovery boundaries. Unknown identifiers use the existing bounded in-process map and dummy Argon2 path; no per-unknown durable row is created. The existing password-hash concurrency gate remains active.

**Residual risks:** account cooldown can still be targeted; unknown-account throttling is process-local and can be evicted/replica-local; without verified proxy trust there is no IP-specific shared budget; Supabase and Cloudflare availability affect challenged logins; and edge rules cannot be verified from this repository. These limits are recorded rather than claimed as solved.

## Evidence not established by this audit

- Cloudflare dashboard rate-limit, WAF, Turnstile widget, and hostname settings.
- Production `AUTH_TURNSTILE_*`, `SUPABASE_*`, or auth secret injection and rotation.
- Production migration state, Supabase Data API schema exposure, RLS policies as deployed, or grants after migration.
- Multi-replica/production login behavior, production Turnstile host validation, or public browser accessibility.
- Any production database or account mutation. None was attempted.
