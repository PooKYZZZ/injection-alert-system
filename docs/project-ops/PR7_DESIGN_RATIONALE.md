# PR7 Controlled CRITICAL WAF Enforcement — design rationale

## Purpose

PR7 is deliberately a bounded local proof, not a production deployment. It
adds a data-plane control for a narrow class of verified CRITICAL recommendations
while preserving PR6's application-level HIGH behavior and static CRS. The
implementation contract is authoritative; this document records why its scope
is intentionally constrained.

**Superseding T0 note (2026-07-28):** General hosted and production Cloudflare
enforcement remains deferred. A target-only isolated Cloudflare topology was
proved solely as a controlled T0 source-identity harness; final hostname
cutover and verified normal runtime remain unauthorized. Controlled local PR7
activation is implemented and validated in Block 2.

## Chosen design

The design keeps a dedicated effective WAF-state table instead of overloading
historical recommendations. Mutation writers use `READ COMMITTED` and lock the
singleton row first so concurrent writers serialize on the authoritative owner.
Snapshot readers use read-only `REPEATABLE READ` because they must render one
complete revision-consistent view. The revision is an ordinary locked `BIGINT`,
not a sequence, because sequence increments do not roll back with a failed
mutation.

Partial ACTIVE uniqueness, absolute expiry, bounded capacity, deterministic
rendering, validation-before-selection, one backup, applied-generation
confirmation, persistent latch, and source/path proof each control a concrete
correctness or safety failure. An ACTIVE row is the sole owner for its
source/path pair. Superseded history never resurrects after owner revocation:
fallback would silently reactivate an older decision without a new decision.

The WAF enforces canonical network identity, not human identity. Short route
scope and absolute expiry reduce but do not eliminate NAT/CGNAT collateral risk.
Only a T0-proved local source identity may enter state; client headers are not
trusted. The local proof must demonstrate that a PR7 403 has no upstream
attempt, while an independent CRS 403 remains distinguishable by tags.

The renderer uses path-first, IP-second, expiry-third chain order because the
literal protected path is the cheapest selective predicate. T0 establishes that
the pinned image accepts that syntax; T5A characterises final-rule performance,
not hand-authored approximations.

## Why the runtime state is explicit

Authoritative snapshot state and selected local state differ after disable,
mode-empty selection, rollback, or file damage. Metadata therefore persists
only the selected source revision, source checksum, and exact file checksum.
Newer failed observations remain in bounded logs; treating them as selected
authority would make rollback ambiguous. The fixed activation lock gives the
kill switch a meaningful completion guarantee without claiming that typing a
command prevents a concurrent in-flight selection.

The one-shot control command is intentionally independent of the polling
process. It shares implementation code and the activation lock, but it does not
queue work for a process that may be hung. A persistent latch survives restart.

The startup gate runs before NGINX accepts traffic because a latch, mode change,
or interrupted metadata update can otherwise leave stale non-empty rules active.
Process and container restart/recreation are the useful local thesis boundary;
host power loss, journalling, and power-cut durability are not claimed.

NGINX graceful reload can leave existing connections on old workers. Bounded
old-worker drain is preferred. If the pinned runtime cannot prove it without
disproportionate machinery, the claim is narrowed to candidate-specific fresh
connections and the existing-connection limitation is recorded.

Expiry and revocation intentionally have different outage behavior. Absolute
expiry is embedded in each rule and remains available during control-plane
outage. Revocation requires a healthy poll/fetch/reload cycle, so it has a
configured healthy-path deadline but may be delayed during outage.

`nginx -T` is a useful equivalence diagnostic, but its configuration dump can
expose internal details and is unnecessary in a poll loop. T0/tests use it with
restricted temporary output; ordinary activation uses quiet syntax validation.

## Rejected additions

The thesis does not require PostgreSQL `INET` solely for theoretical equivalence,
durable records for typed non-activation outcomes, automatic capacity backfill,
a sequence revision, a full runtime state-machine framework, exhaustive crash
injection, host power-loss durability, Docker socket access, Redis/Kafka/Celery,
Kubernetes, Terraform/Helm, custom SMTP, portal changes, or a hosted
enforcement rollout. Each would broaden ownership or infrastructure without
improving the controlled claim enough to justify it. A general-purpose
supervisor framework remains rejected. A minimal purpose-built Python PID-1
wrapper was accepted because it forwards signals, reaps children, and exits
when either known child dies.

## Risk and deferred work

T0 may show that pinned-image placement, validation equivalence, local URI
mapping, source-IP equivalence, IPv6, or no-upstream evidence is unavailable.
That blocks the corresponding enforcement claim rather than inviting a bypass.
IPv6 stays disabled unless proven.

Hosted questions remain deferred: the exact Tunnel/proxy chain, trusted peer,
Worker/header mutation, Pseudo IPv4, direct-origin reachability, firewall,
hosted IPv6, shared-IP risk acceptance, and authorization. `BLOCK-001` and
`BLOCK-002` remain open. No current result may be described as hosted,
production, or end-to-end readiness. Block 3 still owns complete
attack-to-ML creation, external ingress source identity, PR6/PR7 compatibility,
and portal no-upstream proof.

T5A completed the pinned-image 0/1/64/128/512 candidate matrix. The hard
maximum remains 512 and the default capacity remains 64. The result is
controlled-local evidence, not a production load claim.

## Block 3 deferred work

Block 3 owns the complete attack-to-ML recommendation path, trusted external
source identity, PR6/PR7 compatibility, portal no-upstream proof, and final
expiry/revocation thesis measurements. These remain separate from the
controlled-local Block 2 claim and do not authorize hosted or production
enforcement.

## Research basis

- [Python `fcntl`](https://docs.python.org/3/library/fcntl.html) supports the
  container-local activation lock.
- [Python datetime](https://docs.python.org/3/library/datetime.html) semantics
  require explicit rejection of naive datetimes.
- [NGINX command-line switches](https://nginx.org/en/docs/switches.html)
  document that `-T` tests and dumps configuration, which motivates restricted
  T0/test use only.
- [ModSecurity v3 reference material](https://github.com/owasp-modsecurity/ModSecurity/wiki/Reference-Manual-%28v3.x%29)
  permits the path-first chain starter with disruptive metadata on that
  starter, subject to pinned-image proof.
- [PostgreSQL transaction isolation](https://www.postgresql.org/docs/current/transaction-iso.html)
  supports the distinct writer and snapshot-reader isolation choices.
- [PostgreSQL date/time functions](https://www.postgresql.org/docs/current/functions-datetime.html)
  distinguish transaction-start time from `clock_timestamp()`.
- [NGINX control documentation](https://nginx.org/en/docs/control.html)
  describes graceful reload and old-worker drain behavior.
- The synthesis review is the source for the lifecycle, selected-state,
  startup, wire-contract, and bounded-recovery corrections.
