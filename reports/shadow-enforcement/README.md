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

No live Compose or hosted proof is claimed until the opt-in smoke and latency
commands have been run with a disposable key. Add only summarized timestamps,
transaction/recommendation IDs, tier/action, policy version, response status,
and observed limitations after those commands complete.
