# CyberTrace Adaptive Login Turnstile Design

**Decision date:** 2026-11-05
**Status:** Approved for implementation on `feat/auth-adaptive-turnstile-login`; feature flag remains off by default.

## Policy

- Count consecutive failed **password** attempts over a 300-second window.
- After three failed password attempts, require Turnstile for the next password attempt when `AUTH_TURNSTILE_ENABLED=true`.
- Preserve the five-failure hard limit and use a 60-second cooldown by default. This shortens the original 300-second lockout at the user's request; the 300-second failure-count window is unchanged. A challenge is only permission to try the password; it does not reset failure history or create a session.
- A successful password authentication clears the canonical account failure state. If MFA is required, the existing MFA handoff still follows that password check.
- Keep CAPTCHA disabled by default. Turning it off does not turn off the five-failure throttle.

The values are application policy, not OWASP or NIST mandates. OWASP recommends layered defenses and warns that account lockout can be abused for denial of service. The shorter cooldown reduces the time a targeted account remains locked, while allowing a new five-failure round sooner; Turnstile is still required after the third failure. There is no process-wide failure bucket that can lock unrelated accounts. The remaining targeted lockout and increased attempt-rate risks are disclosed in the re-audit and deployment evidence. Cloudflare's separate five-minute token lifetime is provider-defined and is unchanged.

## Authentication flow

```text
Credentials authorize()
  -> parse exclusive password / MFA completion / recovery completion mode
  -> MFA and recovery continue through their existing completion paths
  -> password mode: resolve account and canonical UUID
  -> atomically inspect/reserve shared account attempt
     -> cooldown / exhausted: generic credential denial
     -> challenge needed, no token: generic verification-required code; no Argon2
     -> challenge needed, token: Siteverify with bounded timeout, action and hostname
        -> invalid or unavailable: deny; do not hash or count a password attempt
        -> valid: atomically reserve one attempt
     -> hash and verify with existing per-process concurrency gate
        -> wrong/disabled/unknown: consume reservation and count failure
        -> valid password: clear canonical failures; preserve existing MFA behavior
```

The same `authorize()` callback handles the browser Server Action and direct Auth.js Credentials callback. The browser only controls presentation; it cannot decide that verification is unnecessary.

## State and concurrency

Known accounts use a new additive PostgreSQL state row keyed by `auth_accounts.id`. This makes email, username, and UUID attempts converge without storing raw aliases. A short-lived reservation is inserted in the same transaction as the admission check; a row lock serializes concurrent checks. Completion consumes only a live reservation exactly once, increments a failed-password count or clears it after successful authentication, and applies the cooldown at five failures. Expired reservations are pruned on the next admission or rejected completion. Table size is bounded by existing accounts plus a small bounded number of live reservations per account; account deletion cascades the transient state.

All serving application instances must use the same `AUTH_LOGIN_*` policy and `AUTH_TURNSTILE_ENABLED` setting. The database shares counters and serializes attempts; the policy and flag are supplied by each server call.

Only the service-role server path can execute the narrow RPCs or access the throttle table. RPCs use `SECURITY INVOKER`, a blank `search_path`, qualified object names, and explicit grants. The table has RLS enabled; anon/authenticated/PUBLIC receive no table access or RPC execute grant. No client-side Supabase call or new database service is added.

Unknown account identifiers do not create persistent rows. They continue through the bounded `LoginThrottle` map and the existing dummy Argon2 verification path. This avoids unbounded writes driven by arbitrary usernames. The map is a secondary treatment for unknown accounts; it is not the authoritative limiter for known accounts. The per-process hash concurrency limit remains in force.

## Turnstile validation and UI

- Keep `AUTH_TURNSTILE_SECRET_KEY` server-only. Add `NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY` only for the conditional widget.
- Require an explicit expected hostname when enabled. Validate `success`, action `login`, exact hostname, non-empty token, and the current Cloudflare maximum token size of 2048 characters.
- Bound Siteverify with a five-second abort timeout. No retry is made: tokens are single-use, and an uncertain retry could consume/replay the same token. Provider or configuration errors fail closed when the challenge is required.
- Reject Cloudflare's documented dummy sitekeys/secrets in production configuration. The managed E2E harness alone enables the feature with Cloudflare's published dummy keys on loopback and uses the real Siteverify test response. Its exact `result_with_testing_key` response shape is accepted only when both dummy keys, the managed-test marker, and loopback app/database URLs match. Production credentials still require action `login` and the configured hostname. No production secret or test token is added to the repository.
- Render the Managed widget only after the server signals that verification is required. Use explicit rendering for conditional React UI, clear the token after every submission, and reset on error/expiry/timeout. Keep keyboard-accessible status text and the existing generic credential error behavior.
- Extend only CSP `script-src` and `frame-src` with `https://challenges.cloudflare.com`; retain `frame-ancestors 'none'` and `connect-src 'self'`.

## Standards and framework guidance applied

| Source | Current guidance used in the design |
| --- | --- |
| [OWASP Authentication Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html) | Use layered login defenses, generic login outcomes, bounded throttling, and account-lockout DoS analysis. CAPTCHA is defense in depth. |
| [OWASP Credential Stuffing Prevention Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Credential_Stuffing_Prevention_Cheat_Sheet.html) | Do not rely on CAPTCHA or IP-only controls alone; preserve MFA and combine controls at the authentication boundary. |
| [NIST SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html) | Apply suitable failed-authentication throttling and additional measures to mitigate lockout attacks. NIST does not prescribe this project's 3/5 thresholds. |
| [Cloudflare Siteverify](https://developers.cloudflare.com/turnstile/get-started/server-side-validation/) | Server validation is mandatory; tokens are single-use, expire after 300 seconds, and are limited to 2048 characters. Verify action/hostname and bound network waits. |
| [Cloudflare widget configuration](https://developers.cloudflare.com/turnstile/get-started/client-side-rendering/widget-configurations/) | Explicit rendering is suited to conditional React/SPA flows; handle success, expiry, timeout, and error lifecycle callbacks. |
| [Cloudflare CSP guidance](https://developers.cloudflare.com/turnstile/reference/content-security-policy/) | Permit only the Turnstile origin in `script-src` and `frame-src`, retaining existing restrictions. |
| [Cloudflare testing guidance](https://developers.cloudflare.com/turnstile/troubleshooting/testing/) | Official dummy keys exist for automated tests; production configuration must reject them. |
| [Auth.js Credentials reference](https://authjs.dev/reference/core/providers/credentials) | Credentials `authorize()` is the full-control boundary; inputs need explicit validation. Custom credential error codes can reach direct callback URLs, so use a generic `verification_required` code with no account details. |
| [Next.js environment variables](https://nextjs.org/docs/app/guides/environment-variables) | `NEXT_PUBLIC_` values are frozen during `next build`; provision the public Turnstile site key in the build environment. Keep the secret server-only. |
| [Supabase database functions](https://supabase.com/docs/guides/database/functions) and [RLS guidance](https://supabase.com/docs/guides/database/postgres/row-level-security) | Restrict RPC execute grants; a service-role key bypasses RLS and therefore remains server-only. |
| [WCAG 2.2, SC 3.3.8](https://www.w3.org/TR/WCAG22/#accessible-authentication-minimum) | Keep the challenge keyboard reachable, announce state/errors, and retain an accessible sign-in experience. |

## Alternatives considered

**Cloudflare edge-only rate/challenge:** rejected as the authoritative control because the checked-in deployment evidence does not establish configured rule coverage, account-alias identity, or direct Auth.js callback protection. It remains possible defense in depth.

**Process-local limiter only:** rejected for known accounts because process restart, replica selection, and concurrent requests can reset or exceed the limit.

**Redis/new service or framework:** rejected because the project already has server-only Supabase RPC conventions and a disposable PostgreSQL migration harness; an additional dependency and operational service are unnecessary.

**Persistent rows for arbitrary unknown identifiers:** rejected because attacker-controlled unique inputs could grow state without bound. Unknown requests keep the existing bounded local treatment and dummy hash.

## Operational and rollback plan

1. Apply the additive Alembic migration through the approved deployment path; do not run it against a live or unknown database during this task.
2. Provision a production Turnstile site key restricted to the deployed application host, a matching secret, and the exact expected hostname. Set `NEXT_PUBLIC_AUTH_TURNSTILE_SITE_KEY` before `next build` because Next.js freezes public values into the build. Keep `AUTH_TURNSTILE_SECRET_KEY` in the server-only runtime environment. Keep the `AUTH_LOGIN_*` values and feature flag identical on every replica; set the cooldown override to `60` seconds if it is present. Never use the official dummy keys.
3. Deploy with `AUTH_TURNSTILE_ENABLED=false`; confirm server-only secret and site-key wiring, migration/grants, CSP, and a controlled staging login path. The disposable local E2E test exercises the challenge using Cloudflare's official dummy credentials.
4. Enable the flag only after those checks. Monitor generic challenge-required, verification-failure, cooldown, and database-error counts without logging tokens or raw identifiers.
5. Roll back the feature by setting the flag false. The shared five-failure, 60-second cooldown remains active. The additive table/RPC may remain in place during application rollback; dropping it requires a separate schema rollback after confirming no code version still calls it.

No production deployment, live migration, or Cloudflare dashboard change is part of this implementation task.
