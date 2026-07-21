# PR4 Shadow Enforcement Evidence

This report is reserved for sanitized local proof results. Do not record API
keys, authorization headers, cookies, database URLs, raw source IPs, request
bodies, or unredacted audit-log lines.

## Contract

- The original ModSecurity/CRS decision remains separate from CyberTrace ML
  triage. A completed WAF alert may create one expiring recommendation for
  `/records/search`.
- `action_taken` is existing alert metadata.
- `recommended_action` is a versioned future intent (`MONITOR`, `THROTTLE`,
  `APPLICATION_BLOCK`, or `WAF_BLOCK`).
- `actual_decision` is always `ALLOW` in PR4 shadow mode.
- A later request is correlated by canonical source IP plus scope; this is not
  verified attacker identity. Hosted source verification remains unverified.

## Evidence status

Sanitized local single-stack proof is recorded in `e2e-proof.md` and
`local-compose-proof-2026-07-21.md`. The canonical `e2e-proof.md` now includes
fresh post-merge validation: healthy recommendation matching, backend-down
fail-open, recovery, and a second complete WAF correlation smoke. The reports
cover the WAF/CRS-to-backend recommendation path, later shadow matching,
fail-open behavior, credential and asset-boundary checks, and portal latency.
Hosted or production enforcement is not claimed. Live expiration was not
destructively forced; expiry semantics are covered by the automated use-case
and repository tests.
