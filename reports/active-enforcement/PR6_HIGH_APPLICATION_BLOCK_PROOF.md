# PR6 HIGH Application Block Proof

## Evidence level

- IMPLEMENTED: PASS in CyberTrace and the Land Records portal working trees.
- AUTOMATED_TESTED: PASS.
- INTEGRATION_TESTED: PASS for the internal HTTP contract and disposable local CyberTrace-to-portal path.
- CONTROLLED_E2E_VERIFIED: PENDING exact final-head rerun; the prior controlled run covered active HIGH, expiry, protected-content suppression, dependency fail-open, logging, and recovery.
- HOSTED_VERIFIED: NOT_RUN; hosted topology proof remains blocked.
- PRODUCTION_ENABLED: NO.

## Implemented contract

CyberTrace reuses the existing `enforcement_recommendations` table, v2 policy,
source eligibility, scope, policy version, and `expires_at`. The active lookup
selects HIGH above MEDIUM/LOW and continues to exclude CRITICAL. A selected HIGH
returns the exact internal body `{"decision":"BLOCK"}`.

The portal validates that exact body server-side. `BLOCK` prevents the
record-search work callback from executing, renders generic temporary-block
content, and emits `enforcement.application_block_applied` at the actual block
branch. Unknown or metadata-bearing
BLOCK payloads are invalid and follow the existing bounded fail-open path.

## Automated validation

| Command | Result |
|---|---|
| Focused enforcement repository/use-case tests | PASS, 29 tests |
| Enforcement route plus policy tests | PASS, existing route/policy coverage |
| Full backend with process-only notification-worker overrides | PASS, 858 passed / 36 skipped |
| PostgreSQL-only enforcement repository file | NOT_RUN, 2 skips: explicit disposable URL required |
| Portal unit suite | PASS, 32 tests after review fixes |
| Portal typecheck | PASS |
| Portal lint | PASS |
| Portal production build | PASS; `/records/search` dynamic |
| Targeted Ruff | PASS |

The first unisolated full-backend attempt failed because root `.env` notification
worker settings invoked a PostgreSQL-only outbox function in SQLite tests. No
PR6 assertion failed. The documented process-only worker overrides produced the
passing full-suite result above.

## Controlled local E2E

Date: 2026-07-23 (Asia/Manila).

Environment: one main Docker Compose project, PR6 CyberTrace and portal images,
disposable PostgreSQL 16, `APP_ENV=development`, explicit ENFORCE, and
the development/test-only unverified-source bypass. The disposable source was
the Compose gateway `172.18.0.1`. The database and three test services were
removed after proof; hosted and production configuration were untouched.

The prior E2E image preceded the review fixes in this consolidated update. An
exact final-head smoke must be rerun before this document can claim
`CONTROLLED_E2E_VERIFIED: PASS` again.

| Case | Observed result |
|---|---|
| Active HIGH | HTTP 200 generic temporary-block page; no record table or known record content; `Cache-Control: no-store, must-revalidate, no-cache, max-age=0, private` |
| Persisted state | `RECORD_SEARCH`, HIGH, `APPLICATION_BLOCK`, ENFORCE, `confidence-enforcement-v2`, active, malicious SQL Injection trigger |
| Expired HIGH | Normal search page returned; no challenge, throttle, or block view |
| CyberTrace stopped with HIGH active | Normal search page returned after one bounded attempt; portal logged `TIMEOUT_OR_NETWORK` with `actual_decision=ALLOW` |
| Recovery | Backend returned healthy; the same still-active HIGH blocked again |
| Block logging | Portal logs `enforcement.application_block_applied` at the actual block branch, separately from recommendation creation/evaluation |

Exact different-source E2E is NOT_PROVEN because the local WAF topology exposes
one gateway source. Automated repository tests prove a HIGH row for source A is
not selected for source B. Wrong scope is structurally bounded to the only
supported request/schema value, `RECORD_SEARCH`; no other portal route received
an enforcement call.

## Security invariants

- I1/I2: PASS. Active HIGH returns BLOCK; the protected-work invocation-count test is zero and E2E returns no record content.
- I3/I4: PASS. Existing policy tests cover Normal at every confidence tier and produce no recommendation, including HIGH confidence.
- I5: PASS in repository automation and controlled expiry E2E.
- I6: PASS in automated repository source isolation; distinct-source E2E not proven in the one-source local topology.
- I7: PASS by fixed `RECORD_SEARCH` schema and route-local enforcement point.
- I8/I9: PASS through unchanged LOW/MEDIUM tests and full regressions.
- I10/I11: PASS. CRITICAL remains excluded; SHADOW remains non-disruptive.
- I12/I13: PASS. Timeout/network/HTTP/malformed paths fail open only for the CyberTrace layer; existing public-page behavior is unchanged.
- I14: PASS. The check is in the server page before protected work.
- I15: PASS in configuration/source tests; deployed bypass remains rejected.
- I16: PASS. The route is dynamic, the internal fetch uses `no-store`, and E2E observed private/no-store response headers.
- I17: PASS. PR6 applies to later matching requests; it makes no retroactive WAF claim about the triggering request.

## Adversarial review

- Unknown decision, metadata-bearing BLOCK, malformed JSON, HTTP failure,
  timeout, and connection failure cannot fabricate a block.
- CRITICAL, SHADOW, expired, wrong-policy, wrong-source, and ineligible-source
  rows cannot become PR6 BLOCK through the active lookup.
- The protected route has no alternate browser-only enforcement switch; direct
  UI manipulation cannot skip the server check. Other routes are intentionally
  outside the approved scope.
- Shared NAT is tracked as `LIMIT-006`, a known source-key limitation. Production is still gated
  on controlled Cloudflare headers, Pseudo IPv4 review, direct-origin isolation,
  and immediate peer trust. PR6 does not redesign identity.
- HTTP status is a known limitation: the stable Next.js page API returns the
  generic block view with HTTP 200. Native 403 for a Server Component requires
  experimental `authInterrupts`, which was not enabled across the application.

The consolidated review fixes the malformed-candidate precedence and stale
challenge/unsupported-tier paths. Exact final-head E2E remains pending. Hosted
activation is still blocked by `BLOCK-001`, `BLOCK-002`, and the explicit
`LIMIT-006` rollout decision; HTTP-status semantics remain `LIMIT-007`.

## Research citation record

### NIST SP 800-207

- TYPE: STANDARD
- SOURCE: https://doi.org/10.6028/NIST.SP.800-207
- CLAIM SUPPORTED: policy decisions and resource-adjacent enforcement are separable responsibilities.
- HOW IT AFFECTED PR6: CyberTrace remains the decision/state owner; the portal remains the application enforcement point.

### OWASP Authorization Cheat Sheet

- TYPE: OFFICIAL
- SOURCE: https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html
- CLAIM SUPPORTED: server-side checks belong at the correct enforcement location and existing request security controls must remain independent.
- HOW IT AFFECTED PR6: the check remains server-side and route-local before protected work; fail-open applies only to the CyberTrace layer.

### OWASP Logging Cheat Sheet

- TYPE: OFFICIAL
- SOURCE: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- CLAIM SUPPORTED: log security actions without secrets, and ensure blocking based on security data cannot become denial of service against other users.
- HOW IT AFFECTED PR6: safe distinct block/degraded events, strict source gates, expiry, and explicit shared-NAT analysis.

### RFC 9110 and RFC 9111

- TYPE: STANDARD
- SOURCES: https://www.rfc-editor.org/rfc/rfc9110.html and https://www.rfc-editor.org/rfc/rfc9111.html
- CLAIM SUPPORTED: 403 represents understood-but-refused requests; `no-store` prevents intentional storage by private and shared caches.
- HOW IT AFFECTED PR6: 403 was evaluated but rejected because the installed stable framework path requires an experimental global feature; no-store and dynamic/private response behavior were retained and verified.

### Cloudflare visitor IP and HTTP-header guidance

- TYPE: OFFICIAL
- SOURCE: https://developers.cloudflare.com/fundamentals/reference/http-headers/
- CLAIM SUPPORTED: `CF-Connecting-IP` depends on the controlled proxy chain and Pseudo IPv4 configuration; forwarding metadata can be spoofable outside it.
- HOW IT AFFECTED PR6: production source gates and the deployed bypass rejection remain unchanged; hosted activation stays off.

### AWS Builders' Library timeout/retry guidance

- TYPE: INDUSTRY
- SOURCE: https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/
- CLAIM SUPPORTED: remote calls need bounded timeouts, while retries can amplify load and require deliberate design.
- HOW IT AFFECTED PR6: the existing single bounded attempt remains; no retry, cache, or circuit breaker was added without repository evidence.

### Balepin et al., specification-based intrusion detection and response

- TYPE: PEER_REVIEWED
- SOURCE: https://seclab.cs.ucdavis.edu/papers/Balepin-RAID-03.pdf
- CLAIM SUPPORTED: false positives in automated response can deny legitimate users, making response precision and safety important.
- HOW IT AFFECTED PR6: HIGH confidence alone is insufficient; only a persisted, active, applicable malicious recommendation can block.

No community source overrode the standards, official documentation, repository
contracts, or controlled evidence.

## PR7 boundary

CRITICAL remains `WAF_BLOCK` intent for a later WAF/ModSecurity enforcement
phase. PR6 does not mutate WAF rules, firewalls, or CRITICAL behavior.
