# PR7 Controlled CRITICAL WAF Enforcement
## Permanent-chat project handoff, decision register, and implementation context

**Prepared:** 2026-07-27
**Purpose:** Transfer the complete PR7 planning and review context from a temporary chat into a permanent chat without losing the reasoning, scope decisions, implementation constraints, accepted corrections, rejected complexity, current readiness, or outstanding work.

---

# 1. How to use this handoff

Upload this file and the following four current PR7 documents into the permanent chat:

1. `PR7_IMPLEMENTATION_SPEC.md`
2. `PR7_DESIGN_RATIONALE.md`
3. `PR7_T0_EVIDENCE.md`
4. `PR7_CONTROLLED_CRITICAL_WAF_ENFORCEMENT_PLAN.md`

Use this handoff as context and history. The documents have the following authority:

1. **`PR7_IMPLEMENTATION_SPEC.md` is normative.** It defines required implementation behaviour.
2. **`PR7_T0_EVIDENCE.md` records runtime feasibility.** At handoff preparation its status was `NOT_RUN`; the superseding T0 note below records the current `T0: GO` status.
3. **`PR7_DESIGN_RATIONALE.md` explains why decisions were made.** It does not override the implementation contract.
4. **`PR7_CONTROLLED_CRITICAL_WAF_ENFORCEMENT_PLAN.md` is only the document index and status boundary.**
5. **This handoff preserves conversation history and unresolved review notes.** If it conflicts with a deliberately updated normative specification, the latest implementation specification wins.

The next AI should not redesign PR7 from scratch. It should first read all five files, check that the final corrections listed in this handoff have been incorporated, and then help execute T0 or implement the authorised stage.

**Superseding T0 note (2026-07-28):** General hosted and production Cloudflare
enforcement remains deferred. The target-only isolated Cloudflare topology was
proved solely as a controlled T0 source-identity harness. This supersedes only
the earlier source-identity `NOT_RUN` status; it does not authorize final
hostname cutover, verified normal runtime, local PR7 `ENFORCE`, or T1 and later.
E28 and E29 now close the source-identity and process-topology gates; T0 is
complete with decision `GO`. The real PID-1 wrapper and real synchroniser remain
deferred to T4B. T1 has not started and requires separate authorization.

---

# 2. Executive project summary

PR7 is a narrow, local, thesis-only addition to the CyberTrace project. It turns a limited class of persisted security recommendations into temporary ModSecurity rules in a local WAF.

The intended claim is:

> A persisted, verified, non-Normal `CRITICAL + WAF_BLOCK` recommendation can become a temporary, source-IP-scoped and path-scoped ModSecurity rule. A later matching request is denied by the WAF before the Next.js portal is contacted. The block ends through absolute expiry or through healthy control-plane revocation. Existing PR6 HIGH application blocking and static OWASP CRS behaviour remain unchanged.

The feature is deliberately not a production WAF control plane. It is not intended to demonstrate hosted readiness, multi-node convergence, enterprise operations, or Cloudflare integration.

The current high-level flow is:

```text
Browser
  -> local NGINX + ModSecurity WAF
  -> Next.js land-records portal route handler
  -> FastAPI / CyberTrace services
  -> PostgreSQL
```

The WAF is a reverse-proxy data plane. Browser code must not call FastAPI directly.

Existing system responsibilities remain separate:

- **PR5:** LOW/MEDIUM recommendation behaviour.
- **PR6:** HIGH application-level blocking.
- **Static CRS:** independent generic web-attack protection in ModSecurity.
- **PR7:** temporary local WAF rules for a tightly constrained class of verified CRITICAL recommendations.

PR7 must not alter PR5, PR6, static CRS, confidence thresholds, action-transport contracts, the portal's CRITICAL logic, hosted topology, staging behaviour, or production activation.

---

# 3. Repository baselines mentioned during planning

The earlier monolithic planning document recorded these baselines:

- CyberTrace master SHA: `09f4d80defabd9b01e588d0d546ba006e96735d9`
- Portal stable / `portal-pre-waf` SHA: `def2cf3c248b298144764d965cd81a8b428943d9`

These values were planning references at the time of review. They must be verified against the actual repository before execution. T0 must record the exact repository commit, Compose project, image digest, and versions used in the real run.

---

# 4. Fixed thesis boundary

## 4.1 What PR7 is allowed to claim

PR7 may claim only a controlled local demonstration in the verified pinned environment. The thesis evidence may cover:

- Atomic persistence of the recommendation and effective WAF state.
- Revision-consistent complete snapshots.
- Deterministic rule generation.
- Validation before candidate selection.
- A later matching request blocked at ModSecurity.
- Objective evidence that the portal was not contacted for the PR7 block.
- Static CRS remaining active.
- PR6 remaining unchanged.
- Absolute expiry functioning during backend or poller outage.
- Revocation functioning within a measured healthy-path control-plane deadline.
- A local persistent kill switch that works even when the polling process is stopped.
- Recovery across the exact process/container restart or recreation boundary proved through the selected volume.

## 4.2 What PR7 must not claim

The project must not be described as:

- Hosted-ready.
- Staging-ready.
- Production-ready.
- Internet-scale.
- Multi-node consistent.
- A distributed WAF management platform.
- A generic security policy engine.
- Full end-to-end hosted enforcement.
- Resilient to host clock manipulation or host power loss unless separately proved.

## 4.3 Deferred hosted issues

The following remain explicitly deferred and should not be solved inside PR7:

- Cloudflare Tunnel and proxy-chain identity.
- Trusted hosted peer configuration.
- Cloudflare Worker or header mutation behaviour.
- Pseudo IPv4.
- Direct-origin reachability and hosted firewall policy.
- Hosted IPv6.
- Shared-IP risk acceptance.
- Production authorisation and operations.
- `BLOCK-001` and `BLOCK-002` from earlier planning.

No local result may be presented as resolving those hosted questions.

---

# 5. Scope restrictions and prohibited additions

The user explicitly requested thesis-level best practices rather than enterprise platform construction. A small amount of overengineering is acceptable only when it materially improves correctness, determinism, reproducibility, failure recovery, testability, thesis evidence, or coding-agent reliability.

The following must not be added unless a concrete local correctness failure proves them indispensable:

- Kubernetes.
- Terraform or Helm.
- Redis.
- Kafka.
- Celery or a general job queue.
- Distributed consensus.
- Multi-WAF-node synchronisation.
- A generic policy engine.
- Docker socket access.
- A remote administration API.
- SIEM integration.
- External alerting infrastructure.
- Automated Cloudflare rule management.
- Hosted or production rollout.
- A general process-supervisor framework.
- PostgreSQL `INET` solely for theoretical canonicalisation.
- Durable database records for every non-activation reason.
- Automatic reconsideration of capacity-rejected recommendations.
- A new portal-side CRITICAL decision.
- Portal observability changes merely for convenience.
- Internal TLS or HMAC where the accepted local threat model does not require them.
- A sequence-based global WAF revision.
- A full formal runtime state-machine framework.
- Exhaustive instruction-level crash injection.
- Host-power-loss durability or power-cut tests.

A minimal PID-1 wrapper may be acceptable if T0 proves that the pinned image needs one to start the known processes, forward termination, reap children, and exit when the relevant child dies. That is not permission to add a general supervisor framework.

---

# 6. Core architectural decisions

## 6.1 Dedicated effective WAF-state table

PR7 uses an additive, dedicated effective-state table instead of giving historical recommendation rows mutable ACTIVE lifecycle semantics.

Reasons:

- Recommendation history and effective data-plane state are different concepts.
- PR5/PR6 history should not acquire PR7-specific mutable defaults.
- A dedicated table makes ownership, supersession, expiry, revocation, capacity, revision, and snapshot selection explicit.
- Database constraints can protect the effective-state invariants without changing historical recommendation semantics.

This decision should remain.

## 6.2 Effective ownership model

The intended model is one effective-state history row for each recommendation that actually becomes an effective ACTIVE owner.

The final normative wording should say:

> At most one effective-state row may exist per recommendation. Only an eligible recommendation that becomes an effective ACTIVE owner creates a row. Already-expired, duplicate, shorter/equal, and capacity-rejected outcomes create no new effective-state row.

Statuses are exactly:

```text
ACTIVE
SUPERSEDED
REVOKED
EXPIRED
```

Allowed transitions are exactly:

```text
ACTIVE -> SUPERSEDED
ACTIVE -> REVOKED
ACTIVE -> EXPIRED
```

Terminal rows never reactivate.

For a canonical `(source_ip, protected_path)` pair:

- At most one row is ACTIVE.
- A longer eligible recommendation may supersede the current ACTIVE owner.
- The new recommendation becomes the sole ACTIVE owner.
- The prior owner becomes SUPERSEDED in the same transaction and revision.
- Superseded history never falls back or resurrects.
- Revoking the ACTIVE owner removes the effective block.
- Revoking a non-active historical recommendation changes no desired state.
- There is no hidden fallback queue.

Recommended database invariants:

```text
UNIQUE (recommendation_id)
partial UNIQUE (canonical_source_ip, protected_path) WHERE status = 'ACTIVE'
FOREIGN KEY recommendation_id ... ON DELETE RESTRICT
CHECK constraints or domain validation for allowed status/terminal fields
```

## 6.3 Capacity semantics

- Development cap: 64 ACTIVE entries.
- Hard maximum: 512 ACTIVE entries.
- Capacity is evaluated under the singleton mutation lock after revisioned cleanup using the same `mutation_now`.
- Capacity rejection is final for that recommendation.
- Later cleanup or revocation does not backfill an old rejected recommendation.
- A new recommendation is required for later consideration.
- T5A measures actual generated configurations at 0, 1, 64, 128, and 512 rules.
- No performance threshold is invented before measurement.

## 6.4 No durable non-activation table

Recommendation persistence and effective WAF-state mutation are atomic when effective state changes.

For non-activated outcomes:

- The recommendation remains durable history.
- A typed application result and structured log may describe already-expired, shorter/equal, duplicate, or capacity-rejected outcomes.
- Those result/log records are not durable decision history.
- Do not add a second durable outcome table unless the thesis explicitly requires durable category metrics.

---

# 7. Database transaction and revision decisions

## 7.1 Writer isolation

Mutation writers use:

```text
READ COMMITTED
```

Snapshot readers use:

```text
REPEATABLE READ
READ ONLY
```

The reason for the split:

- Writer transactions need the singleton row lock to block and then proceed against the latest committed owner state.
- Snapshot readers need one stable database view containing a revision and all entries from the same committed desired state.
- Leaving the writer at unspecified or Repeatable Read isolation could produce avoidable serialization aborts under contention.

## 7.2 Singleton-first lock order

Every effective-state mutation path must use the same order:

```text
BEGIN at READ COMMITTED
1. SELECT singleton revision/control row FOR UPDATE.
2. Read one mutation_now using PostgreSQL clock_timestamp().
3. Insert or find the recommendation idempotently.
4. Mark expired ACTIVE rows EXPIRED.
5. Resolve duplicate, extension, capacity, supersession, or revocation.
6. Increment the ordinary BIGINT revision once iff desired state changed.
7. Stamp every changed effective-state row with that revision.
8. COMMIT.
```

The singleton row is always the first database lock. All mutation entry points must follow the same ordering to minimise deadlock risk.

No network call, WAF reload, file operation, or operator interaction occurs inside the database transaction.

## 7.3 Mutation time

Use one `clock_timestamp()` value read after acquiring the singleton lock.

That value is used consistently for:

- Candidate future-expiry eligibility.
- Expired ACTIVE cleanup.
- Capacity calculation after cleanup.
- Lifecycle decisions made in that transaction.

Do not use transaction-start `now()` captured before a lock wait for those decisions.

## 7.4 Revision semantics

The authoritative WAF revision is an ordinary transactional `BIGINT` column on the singleton row.

Do not use:

- A PostgreSQL sequence.
- An identity column.
- A timestamp as the authoritative revision.

Rules:

- Increment exactly once per transaction iff desired WAF state changed.
- Duplicate alone: no revision.
- Shorter/equal candidate alone: no revision.
- Capacity rejection alone: no revision.
- Already-expired candidate alone: no revision.
- Cleanup that changes expired ACTIVE rows: one revision.
- Duplicate plus cleanup in the same transaction: exactly one revision due to cleanup.
- Supersession changes old and new rows under one revision.
- Exception/rollback leaves recommendation, state rows, and revision unchanged.

Do not invent a generic retry framework. Use bounded whole-transaction retry only if a repository convention already exists and its behaviour is verified.

---

# 8. Snapshot consistency and expiry invariant

## 8.1 Snapshot transaction

The internal snapshot endpoint must read:

- The singleton revision.
- Every authoritative ACTIVE row.

from one read-only Repeatable Read database transaction.

A real PostgreSQL integration test must execute:

```sql
SHOW transaction_isolation;
SHOW transaction_read_only;
```

and observe:

```text
repeatable read
on
```

Before T2, record:

- Python version.
- SQLAlchemy version.
- PostgreSQL driver and version.
- PostgreSQL server version.

Apply SQLAlchemy isolation/read-only settings before `begin()` or any operation that triggers autobegin.

## 8.2 Expired ACTIVE rows remain until cleanup

This invariant was discussed repeatedly and must be present in the final specification:

> The snapshot includes every row whose status is ACTIVE from the same Repeatable Read database view. It does not filter ACTIVE rows using the current time. Time passage alone changes neither desired-state rows, revision, nor state checksum. An ACTIVE row whose expiry has passed remains in the authoritative snapshot until an explicit revisioned cleanup mutation marks it EXPIRED.

This is necessary because otherwise the snapshot could change while the revision remains unchanged.

The stale rule is harmless in the data plane because its absolute `TIME_EPOCH` condition is false after expiry.

Required tests:

```text
ACTIVE row passes expiry with no database mutation
-> revision unchanged
-> row still present in snapshot
-> state checksum unchanged
-> ModSecurity condition no longer matches

later explicit cleanup
-> row becomes EXPIRED
-> revision increments once
-> row disappears from snapshot
-> checksum changes
```

---

# 9. Snapshot API and checksum contract

## 9.1 Exact response envelope

The intended response is:

```json
{
  "schema_version": 1,
  "policy_version": "confidence-waf-enforcement-v1",
  "revision": 42,
  "scope": "RECORD_SEARCH",
  "generated_at": "2026-07-27T01:02:03.000Z",
  "state_checksum_sha256": "...",
  "items": [
    {
      "entry_id": 12,
      "recommendation_id": 123,
      "source_ip": "203.0.113.7",
      "request_path": "/records/search",
      "expires_at": "2026-07-27T01:07:03.000Z"
    }
  ]
}
```

The endpoint is:

- Read-only.
- Local-network only.
- Disabled outside controlled local mode.
- Authenticated with a dedicated Bearer secret.
- `Cache-Control: no-store`.
- Free of raw attack payloads and request headers.

Recommended HTTP behaviour to freeze before T3:

```text
GET /api/internal/waf-enforcement/snapshot
Authorization: Bearer <WAF_STATE_SYNC_API_KEY>

missing/invalid token -> 401
snapshot disabled -> 404
safe service/database failure -> 503
success -> 200 application/json
```

Use standard-library constant-time token comparison where available. Never log the token. Do not add HMAC, internal TLS, or key-management infrastructure solely for this local proof.

## 9.2 Client acceptance rules

The client accepts only:

- The exact configured origin.
- HTTP 200.
- Parsed media type `application/json`, allowing the ordinary optional charset parameter.
- A supported schema and exact policy/scope.
- A response no larger than the configured hard limit.
- A complete response within one total monotonic deadline covering connect, headers, and body.
- No redirects.

Reject:

- Redirects.
- Wrong media type.
- Unsupported schema.
- Unknown top-level or item fields if strict-schema policy is retained.
- Wrong policy or scope.
- Duplicate identities.
- Naive datetimes.
- Malformed JSON.
- Truncated bodies.
- Bodies above the hard limit.
- A trickle response exceeding the total deadline.

The recommended hard response ceiling is:

```text
1 MiB
```

Both server and client should enforce it. T3 must prove that a legitimate 512-entry bounded snapshot fits within the ceiling.

## 9.3 UTC serializer

`utc_millis(value)` must reject naive datetimes:

```python
if value.tzinfo is None or value.utcoffset() is None:
    raise ValueError("UTC-aware datetime required")
```

It converts aware datetimes to UTC millisecond precision with a trailing `Z`.

Tests cover:

- UTC-aware.
- Non-UTC aware.
- DST-sensitive aware.
- Naive rejected.

## 9.4 State checksum

The authoritative state checksum is SHA-256 over a deliberately canonical state object containing only:

```text
schema_version
policy_version
revision
scope
items
```

Exclude:

```text
generated_at
state_checksum_sha256
HTTP headers
response whitespace
```

Items are sorted by:

```text
IP version
packed IP bytes
request path
expiry epoch
recommendation ID
entry ID
```

Canonical serialization:

```python
json.dumps(
    state_object,
    ensure_ascii=True,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("ascii")
```

The same revision and desired state must have the same state checksum even when `generated_at` differs.

## 9.5 Candidate checksum

`candidate_file_checksum_sha256` is SHA-256 over the exact rendered ModSecurity candidate bytes.

It is not the same thing as the state checksum.

- State checksum proves deterministic desired-state representation.
- Candidate checksum proves exact selected file bytes and detects corruption or divergence.
- SHA-256 is not authentication.

---

# 10. Source-identity decisions

PR7 enforces canonical network identity, not human identity.

The required invariant is:

```text
persisted verified traffic source
== effective-state source_ip
== snapshot source_ip
== rendered ModSecurity @ipMatch source
== ModSecurity REMOTE_ADDR on the later request
```

The original statement that forwarded headers never select identity was corrected. The actual rule is:

> Untrusted client-supplied forwarding headers never select enforcement identity. A trusted, overwritten proxy-derived value may be used only when T0 proves that it exactly equals the WAF's effective `REMOTE_ADDR` along the real local request path.

T0 must record hop-by-hop provenance:

| Hop | Socket peer | Header accepted | Who overwrites it | Trusted peer set | Value passed onward | Value persisted |
|---|---|---|---|---|---|---|
| Browser → WAF | | | | | | |
| WAF → Next.js | | | | | | |
| Next.js → FastAPI | | | | | | |
| FastAPI persistence | | | | | | |

Tests must cover:

- Real IPv4 local path.
- Client-forged forwarding values.
- Duplicate forwarding headers.
- Trusted peer path.
- Untrusted peer path.
- Canonical string behaviour.
- IPv4-mapped IPv6 policy.
- Runtime IPv6 only when actually enabled.

Source IP is canonicalised with Python `ipaddress` before every effective-state write. Direct uncanonicalised ORM construction is forbidden.

The partial unique index is only a backstop for canonical stored values; textual uniqueness alone does not prove semantic IPv6 uniqueness.

Mapped-IPv6 policy must be frozen before T1. Runtime IPv6 may remain disabled, but pure IPv4/IPv6/mapped-address canonicalisation tests are still required.

---

# 11. Protected-path decisions

PR7 is path-scoped. It does not implement a generic URI canonicalisation framework.

The renderer uses exact literal path matching in this order:

```text
REQUEST_FILENAME exact path
-> REMOTE_ADDR canonical source
-> TIME_EPOCH absolute expiry
```

Path-first order was selected because the protected literal path is the cheapest and most selective predicate. T0 must prove the exact syntax and variable behaviour in the pinned image.

T0 must inspect a finite path matrix, including:

- `/records/search`
- `/records/search?query=x`
- `/records/search/`
- `/records//search`
- `/records/%73earch`
- `/records/search%2F`
- `/RECORDS/search`
- `/records/../records/search`
- Relevant methods such as GET, HEAD, and POST.
- Every discovered Next.js rewrite or route alias.
- An unrelated path.
- A static CRS control.

For each row, record:

```text
raw request target
method
ModSecurity REQUEST_FILENAME
NGINX-visible URI
portal route/protected work reached
HTTP status
exact upstream fields
PR7 or CRS tag
PASS/FAIL/NOT_RUN
```

Do not broaden the rule to speculative aliases. Each allowed protected literal must be proved or excluded.

---

# 12. Rule-rendering decisions

## 12.1 Chain order and actions

The generated chain order is:

```text
REQUEST_FILENAME
REMOTE_ADDR
TIME_EPOCH
```

Disruptive actions and metadata belong only on the chain starter:

- `deny`
- status 403
- PR7 tag
- revision tag
- recommendation tag
- rule ID

The implementation must explicitly control transforms, usually with `t:none`, according to the exact syntax accepted by the pinned image.

## 12.2 Absolute expiry

- Persisted expiry is converted to whole-second epoch by flooring.
- A rule may therefore stop up to 999 milliseconds early.
- It must not outlive persisted expiry.
- `TIME_EPOCH` provides local expiry even when the backend and poller are unavailable.

## 12.3 Deterministic rule IDs

The final specification should freeze deterministic ID assignment after T0 approves a numeric range.

Recommended rule:

```text
1. Sort entries using the canonical state ordering.
2. Assign rule_id = approved_range_start + zero_based_sorted_position.
3. The approved range contains at least 512 IDs.
4. Empty state emits no PR7 rule.
5. IDs are generation-local, not permanent record identifiers.
6. Correlation uses revision and recommendation tags.
```

Tests:

```text
same state -> same IDs and bytes
different input ordering -> same IDs and bytes
513 entries -> rejected before rendering
```

T0 records:

- Proposed range.
- Official convention consulted.
- Effective-ID extraction command.
- Collision result against the pinned effective configuration.
- Approved PR7 range.

No guarantee about future CRS versions is required. Re-scan whenever the image digest or effective local configuration changes.

---

# 13. Persistent runtime-state decisions

## 13.1 Persistent directory

All PR7 runtime state lives in:

```text
/pr7-state
```

It is backed by a named volume or approved bind mount.

The recovery claim covers the exact process and container restart/recreation boundary proved through this storage. It does not claim host-power-loss durability.

## 13.2 Permanent lock file

The activation lock is:

```text
/pr7-state/activation.lock
```

Rules:

- Create it once.
- Never unlink it.
- Never rename it.
- Never replace it atomically.
- Never include it in candidate pruning.
- Poller, startup recovery, selection, rollback, disable, and enable open that exact path.
- All those paths use exclusive `fcntl.flock()`.
- T0 records mount identity, owner, group, permissions, and actual cross-process behaviour.

The state-directory retention wording must distinguish the lock file from candidates:

```text
activation.lock — permanent and never pruned
current selection
previous candidate
canonical empty candidate
selected metadata
optional DISABLED latch
bounded unfinished temporary candidates
```

Candidate pruning operates only on candidate files.

## 13.3 Candidate immutability and atomic selection

Candidate lifecycle:

```text
1. Create a temporary candidate in the destination state directory.
2. Write all bytes.
3. Flush and close it.
4. Compute its exact file checksum.
5. Apply restrictive permissions.
6. Never modify the candidate again.
7. Validate that exact immutable candidate.
8. Atomically select it using same-filesystem replacement.
9. Reload NGINX.
10. Confirm generation and intended content.
11. Write selected metadata atomically.
12. Prune old candidate files only.
```

An invalid candidate must never become selected.

Host power-loss durability, directory `fsync`, and power-cut tests are out of scope. Startup reconciliation handles process/container interruption.

---

# 14. Selected-state metadata

Persist selected/applied state only. Do not persist the latest failed observation as selected authority.

Recommended metadata:

```json
{
  "metadata_schema_version": 1,
  "selected_kind": "authoritative|disabled_empty|mode_empty|pending_empty",
  "selected_source_revision": 42,
  "selected_source_state_checksum_sha256": "...",
  "selected_file_checksum_sha256": "...",
  "selected_at": "2026-07-27T01:02:03.000Z"
}
```

Rules:

- `authoritative` requires source revision and source state checksum.
- Empty kinds use `null` source revision/checksum.
- `selected_file_checksum_sha256` is still required for every empty kind and equals the checksum of the canonical empty candidate.
- The latch file, not a duplicate metadata boolean, is the authority for disabled state.
- Failed observations remain in bounded structured logs.
- A failed revision 43 activation leaves revision 42 selected.
- Rollback restores revision-42 bytes and revision-42 selected metadata.
- The next poll retries revision 43.

Snapshot comparison:

```text
lower revision
-> reject as stale; retain current safe selection

equal revision + different state checksum
-> protocol-integrity failure; retain current safe selection

equal revision + same state checksum
-> no-op only if selected_kind=authoritative,
   source revision/checksum match,
   selected file exists,
   actual selected file checksum matches metadata

higher revision
-> validate and attempt apply

revision reset
-> requires an approved disabled/reset procedure or a fresh disposable environment
```

The same authoritative revision must be reapplied after any empty selected kind or after candidate loss/corruption.

---

# 15. Mode and latch semantics

Modes:

| Mode/latch state | Fetch/render/validate | Non-empty selection | Selected kind |
|---|---|---|---|
| `off` | No steady-state fetch; repair empty if needed | No | `mode_empty` |
| `dry_run` | Yes | No | `mode_empty` |
| `enforce` + latch | No non-empty activation | No | `disabled_empty` |
| `enforce` unlatched | Fresh fetch | After validation | `authoritative` or `pending_empty` |

Rules:

- `mode != enforce` always means no PR7 dynamic rule selected.
- `enforce -> dry_run` selects, reloads, and confirms empty.
- `enforce -> off` selects, reloads, and confirms empty.
- Mode changes never remove the latch.
- `dry_run/off -> enforce` performs a fresh fetch; do not activate a cached dry-run candidate.
- `pending_empty` means enforce is requested, latch is absent, but no authoritative candidate is confirmed.
- While in unlatched `enforce + pending_empty`, every ordinary polling interval attempts a fresh snapshot and application.

A snapshot fetched before taking the local activation lock may be older than the database's latest committed revision. That is acceptable eventual reconciliation if it is newer than the locally selected revision and passes comparison. The next poll applies any later revision. Do not attempt to coordinate the local file lock with the PostgreSQL mutation lock.

---

# 16. Disable and enable controls

Controls execute through the actual running WAF container:

```text
docker exec <verified-container> /usr/local/bin/pr7-waf-control disable
docker exec <verified-container> /usr/local/bin/pr7-waf-control enable
```

The control path must not start a fresh unrelated container because it must share the same lock inode, candidate files, latch, metadata, and NGINX process.

## 16.1 Disable

Under the activation lock:

1. Create the persistent latch.
2. Select/validate/reload/confirm the canonical empty candidate.
3. Run static CRS and control probes.
4. Write `disabled_empty` selected metadata.
5. Return success only after the declared reload-completion rule.

Disable must work while the poller is stopped.

After successful disable returns, no non-empty candidate may be selected until a successful explicit enable clears the latch.

## 16.2 Enable

Under the activation lock:

1. Remove the latch.
2. Do not claim rules are automatically active.
3. In enforce mode, perform a fresh fetch and reconciliation.
4. If the backend is unavailable, keep confirmed empty and record `pending_empty`.
5. Never activate a cached failed observation.

Recommended operator message:

```text
Disable latch cleared.
Dynamic enforcement is not yet confirmed active.
Selected state: authoritative | pending_empty | mode_empty.
```

`enable` may remain the user-facing alias, but conceptually it is `clear-disable-latch` followed by fresh reconciliation.

---

# 17. Pre-NGINX startup gate

Startup recovery must happen before NGINX accepts traffic.

Under the activation lock:

```text
if DISABLED latch exists:
    verify/select canonical empty
    write disabled_empty metadata

elif mode != enforce:
    verify/select canonical empty
    write mode_empty metadata

elif unlatched enforce and a verified authoritative selected file exists
     and its actual checksum matches metadata:
    retain that authoritative selection

else:
    verify/select canonical empty
    write pending_empty metadata
```

Only a verified authoritative candidate may start non-empty.

This protects against:

- Crash after latch creation but before empty selection.
- Mode change while the container was stopped.
- Candidate selected before metadata.
- Reload confirmed before metadata.
- Missing candidate.
- Corrupt candidate.
- Metadata/file mismatch.

Representative crash tests are sufficient:

1. Crash after latch creation, before empty selection.
2. Crash after candidate selection, before metadata.
3. Crash after reload confirmation, before metadata.

Also test missing/corrupt candidate recovery and one rollback interruption. Exhaustive instruction-level crash injection is not required.

---

# 18. NGINX validation, reload, and rollback

## 18.1 Validation

Validate the exact immutable candidate with:

```text
nginx -t -q
```

using the same T0-proved configuration source as the live configuration, allowing only approved temporary path/include differences.

`nginx -T` is permitted only for T0 and runtime integration tests. Redirect its complete output to a restrictive temporary file, retain only bounded redacted evidence, and remove it. Do not run `nginx -T` during ordinary reconciliation.

## 18.2 Separate proof responsibilities

Reload evidence has distinct components:

```text
new worker/generation observation
-> proves reload timing

candidate-specific fresh-connection probe
-> proves the intended candidate content serves

normal control probe
-> proves general WAF availability

static CRS probe
-> proves CRS remains active
```

A PID change alone does not prove candidate content.

## 18.3 Old workers

NGINX graceful reload can leave existing connections on old workers.

Preferred T0 outcome:

1. Record pre-reload worker PIDs.
2. Record post-reload worker PIDs.
3. Prove the new candidate using a fresh connection.
4. Observe existing-connection behaviour.
5. Prove bounded old-worker drain if feasible without disproportionate machinery.

If bounded drain cannot be credibly proved, narrow the claim:

> PR7 activation and disable are confirmed for fresh connections opened after the new generation is observed. Existing requests or connections during graceful reload may complete under the previous generation.

Do not add a distributed acknowledgement protocol or large worker-generation state machine.

## 18.4 Rollback

On activation failure:

- Restore the previous immutable candidate.
- Reload and confirm it.
- Restore its selected-source metadata.
- If no valid previous candidate exists, select/confirm canonical empty and record `pending_empty`.
- Retain only one previous candidate.

---

# 19. Expiry and revocation semantics

These are intentionally different.

## 19.1 Absolute expiry

Absolute expiry is data-plane local behaviour:

- The rendered rule contains a floored epoch cutoff.
- `TIME_EPOCH` evaluates without the backend or poller.
- Expiry is the outage-independent upper bound.
- The rule must not outlive persisted expiry under the approved local clock relationship.

## 19.2 Database/WAF clock gate

T0 must treat clock equivalence as a foundational gate, not merely an informational table.

Record repeated samples:

```text
PostgreSQL clock_timestamp() epoch
WAF-observed TIME_EPOCH
measured difference
accepted relationship or safety margin
```

Allowed results:

```text
PASS — shared local clock relationship is acceptable
PASS WITH MARGIN — renderer subtracts an approved whole-second margin
BLOCKED — no credible no-later-than-persisted-expiry relationship
```

A failed or unproved relationship blocks the hard-expiry claim and later implementation.

Host clock rollback/manipulation may remain out of scope if explicitly disclosed.

## 19.3 Revocation

Revocation is control-plane-dependent:

```text
poll
+ snapshot fetch
+ validation
+ reload
+ confirmation
```

A healthy-path revocation deadline must be configured before T4 and measured at T6.

Recommended formula:

```text
poll interval
+ total snapshot deadline
+ validation/reload/confirmation allowance
+ scheduling allowance
```

During backend or poller outage:

- Revocation may be delayed until recovery.
- The existing rule may remain until its absolute expiry.
- The thesis must not describe revocation as outage-independent.

---

# 20. Process and container behaviour

Required semantics:

- NGINX master death exits the container.
- Expected snapshot fetch, parse, validation, or backend failures leave the poller alive but degraded.
- Unexpected synchroniser death exits the container for Compose restart.
- Persistent latch/candidate/metadata state survives through the volume.
- No general process supervisor is added.

T0 must record:

- PID 1 and entrypoint.
- NGINX master and workers.
- Poller process.
- Signal forwarding.
- Child reaping.
- Exit behaviour when NGINX master dies.
- Exit behaviour when the poller dies unexpectedly.
- Exact persistence boundary proved:
  - process restart,
  - container restart,
  - Compose recreation,
  - no host-restart claim unless actually proved.

---

# 21. Performance and scale decisions

Performance benchmarking does not belong in T0.

T0 proves feasibility only:

- Syntax.
- Placement.
- Include equivalence.
- Rule-ID range.
- Source/path behaviour.
- Reload/content proof.
- Controls/startup/process behaviour.

T5A uses the final renderer and runtime adapter to measure actual generated configurations at:

```text
0
1
64
128
512
```

Record:

- Query cost.
- Rendering time.
- Candidate size.
- Validation time.
- Reload/confirmation time.
- Probe time.
- Resource use.
- Protected-path latency.
- Unrelated-path latency.

Keep the development cap at 64 until measurements are recorded. Do not invent pass thresholds in advance.

---

# 22. T0 feasibility requirements

At handoff preparation T0 was `NOT_RUN`; superseding evidence E28 and E29
now establish `T0: GO`.

T0 is evidence gathering, not implementation. No schema, migration, renderer, runtime synchroniser, Compose activation, or local ENFORCE may be assumed complete because a plan exists.

Every foundational gate must PASS before T1 or later work. Runtime IPv6 may remain `NOT_RUN` only when runtime IPv6 stays disabled and the required pure canonicalisation/mapped-address policy tests pass.

## 22.1 Run identity

Record:

- UTC date/time.
- Operator.
- Repository commit.
- Compose project.
- Verified running container.
- Exact image digest.
- Python version.
- SQLAlchemy version.
- PostgreSQL driver and server versions.
- NGINX version.
- ModSecurity engine and connector versions.
- CRS version.
- PID 1 and entrypoint.
- Persistent volume identity.
- Local-only mode/config proof.
- Secret handling without recording secret values.

## 22.2 Foundational gates

The gate table must include:

1. Pinned placement and pre-NGINX startup-gate feasibility.
2. Include location and exact chain syntax.
3. Candidate/live configuration equivalence.
4. Invalid/valid candidate validation.
5. Rule-ID provenance and collision scan.
6. Reload generation and candidate-content proof.
7. URI/path mapping.
8. Source equivalence.
9. Header-forgery resistance.
10. No-upstream proof with exact sentinel fields.
11. Activation lock and same-container one-shot control.
12. Startup safety for latch/mode/missing/corrupt cases.
13. Canonical empty state and static CRS.
14. Process topology and exit behaviour.
15. **Database/WAF clock relationship.**

The current T0 file was specifically identified as needing the clock relationship added to the foundational gate table rather than leaving it in a separate informational section.

## 22.3 Evidence handling

For every command:

- Record exact command.
- Record exit code.
- Record bounded, redacted relevant output.
- Mark PASS, FAIL, or NOT_RUN.
- Do not record credentials.
- Do not retain raw complete `nginx -T` output.
- If a property cannot be observed credibly, mark BLOCKED rather than inventing a workaround.

---

# 23. Ordered implementation stages

## T0 — Feasibility only

Prove all foundational gates. No performance benchmark.

## T1 — Schema and domain

Implement:

- Dedicated table.
- Singleton revision/control row.
- At-most-one row per effective recommendation.
- Statuses and allowed transitions.
- FK restriction.
- Partial ACTIVE uniqueness.
- Canonical-IP write path.
- Unit tests for constraints and lifecycle.

Requires separate migration approval and every foundational T0 gate PASS.

## T2 — Lifecycle mutation and snapshot reader

Implement:

- READ COMMITTED writer transaction.
- Singleton-first lock order.
- `mutation_now` after lock.
- Cleanup.
- Duplicate/extension/capacity/supersession/revocation.
- Transactional revision.
- Read-only Repeatable Read snapshot.
- Expired-ACTIVE snapshot invariant.
- Real PostgreSQL concurrency/isolation tests.

## T3 — Snapshot API

Implement:

- Exact schema.
- Bearer authentication.
- Local-only activation.
- Canonical checksum.
- Generated-at exclusion.
- Strict validation.
- No redirect.
- Body and total-time limits.
- 1 MiB maximum proof.

## T4A — Pure client and renderer

Implement:

- Strict snapshot client.
- UTC/date validation.
- IP canonicalisation.
- Exact rule chain/template.
- `t:none`/action placement according to T0.
- Deterministic IDs.
- Deterministic candidate bytes.
- Malformed input and ceiling tests.

## T4B — Runtime adapter

Implement:

- Persistent state directory.
- Immutable candidate creation.
- Same-filesystem atomic selection.
- Validation.
- Reload timing/content proof.
- Previous-candidate rollback.
- Selected-source metadata.
- Pre-NGINX startup gate.
- Process-death semantics.
- Ordinary reconciliation without `nginx -T`.

## T4C — Controls and races

Implement:

- Permanent activation lock.
- Persistent latch.
- Poller-independent same-container disable.
- Enable/fresh reconciliation.
- `pending_empty`.
- Mode transitions.
- Same-revision reapplication.
- Lock and control races.

## T5 — Local Compose and regressions

- Non-local environments remain off.
- Static CRS regressions pass.
- PR6 HIGH regressions remain unchanged.

## T5A — Performance characterisation

Measure 0/1/64/128/512 generated rules with the final implementation.

## T6 — Controlled end-to-end proof

Prove:

- Eligible CRITICAL recommendation becomes authoritative state.
- Snapshot revision/checksum consistency.
- Exact candidate correspondence.
- Live candidate application.
- PR7-tagged generic 403.
- Portal non-reachability.
- Wrong source/path normal flow.
- Header-forgery resistance.
- Hard expiry during outage.
- Healthy revocation deadline.
- Outage-delayed revocation but local expiry.
- Static CRS active.
- PR6 unchanged.
- Disable independent of poller.
- Claimed restart persistence.
- Final latched-disabled empty state.

---

# 24. Minimum test set

## 24.1 Database tests

1. Two concurrent different-source activations serialize correctly.
2. Duplicate with no cleanup causes no revision.
3. Duplicate with expired ACTIVE cleanup causes exactly one revision.
4. Longer recommendation supersedes the ACTIVE owner.
5. Shorter/equal recommendation creates no new row.
6. Revoking the ACTIVE owner removes effective state.
7. Revoking superseded history changes nothing.
8. Superseded history never resurrects.
9. Already-expired candidate creates no effective-state row.
10. Capacity-rejected recommendation never backfills.
11. Injected failure rolls back recommendation, state rows, and revision.
12. Forced lock wait across candidate expiry uses post-lock `mutation_now`.
13. Snapshot sees one stable view while another transaction commits.
14. Real PostgreSQL isolation and read-only settings are asserted.
15. ACTIVE row passes expiry without mutation: snapshot/checksum remain unchanged.
16. Explicit cleanup marks EXPIRED, increments revision once, and removes item.

## 24.2 Snapshot/client tests

17. Different `generated_at` with same state yields same checksum.
18. One logical state change yields a different checksum.
19. Lower revision is rejected.
20. Equal revision with different checksum is rejected.
21. Valid maximum-size body succeeds.
22. Redirect fails.
23. Wrong media type fails.
24. Oversized body fails while streaming.
25. Truncated/malformed body fails.
26. Unsupported schema/policy/scope fails.
27. Missing/wrong token fails.
28. Total deadline stops trickle response.
29. Naive datetime fails.
30. IPv4/IPv6/mapped-address policy is deterministic.

## 24.3 Renderer/runtime tests

31. Same state in different input order produces same candidate bytes and IDs.
32. 513 entries are rejected before rendering.
33. Candidate is immutable from validation through selection.
34. Invalid candidate never becomes current.
35. Candidate pruning preserves lock inode and non-candidate state.
36. Generation observation and candidate-content proof are separate.
37. Failed revision application restores prior selected-source metadata.
38. Same revision reapplies after disabled/mode/pending empty.
39. Missing/corrupt selected file is detected.
40. Startup with latch and stale non-empty candidate starts empty.
41. Startup in off mode with stale candidate starts empty.
42. Startup with unavailable backend enters `pending_empty` and preserves CRS.
43. One-shot disable works with poller stopped.
44. Real poller/control processes exclude one another using the fixed lock.
45. Mode transitions select empty correctly.
46. Enable with backend failure remains confirmed empty.
47. Claimed volume preserves latch and selected state across recreation.
48. Process deaths have documented container effects.

## 24.4 End-to-end tests

49. Eligible CRITICAL recommendation creates authoritative effective state.
50. Matching source/path receives PR7-tagged 403.
51. Upstream fields prove no portal attempt.
52. Wrong source reaches portal normally.
53. Wrong path reaches portal normally.
54. Forged forwarding header cannot choose identity.
55. Absolute expiry works with backend and poller unavailable.
56. Healthy revocation meets configured deadline.
57. Revocation during outage may delay, but expiry still ends the rule.
58. Static CRS continues to block its independent control.
59. PR6 HIGH tests remain unchanged.
60. Final state is latched disabled and empty.

---

# 25. Stop conditions

Stop and report `BLOCKED` rather than bypassing the requirement if any foundational property fails or cannot be observed credibly:

- Pinned image placement.
- Exact syntax/include feasibility.
- Candidate/live equivalence.
- Candidate validation.
- Applied generation plus candidate-content proof.
- Protected-path mapping.
- Source equivalence.
- Header-forgery resistance.
- No-upstream evidence.
- Rule-ID range/collision.
- Activation-lock and control feasibility.
- Pre-NGINX startup safety.
- Database/WAF clock relationship for the hard-expiry claim.
- Capacity invariant.
- Invalid candidate, reload, confirmation, or rollback behaviour.
- Static CRS regression.
- PR6 regression.
- Any non-local activation.

Runtime IPv6 may remain disabled/NOT_RUN only under the documented exception.

After controlled proof, leave the local system latched disabled and empty.

---

# 26. Review history and accepted synthesis

## 26.1 Earlier plan concerns

The original monolithic plan was approximately 1,500 lines and repeated normative requirements across architecture, rationale, tasks, tests, AI instructions, and checklists. Reviews identified a risk of internal contradiction and AI-agent omission.

The plan was split into:

- Normative implementation contract.
- Design rationale.
- T0 evidence template.
- Document index.

That split was accepted and should remain.

## 26.2 Important defects already corrected

Earlier reviews found and the current design corrected:

- Equal revision no-op after disabled empty could leave the WAF empty forever.
- A latch check without one shared activation lock did not close the selection race.
- Disable depended on a potentially stopped poller.
- `off`/`dry_run` mode transitions could leave old enforce rules active.
- Rule chains were ordered time-first rather than path-first.
- Naive datetimes could be interpreted using machine-local time.
- Ordinary activation used or risked using `nginx -T` on every reconciliation.
- Duplicate and cleanup revision semantics contradicted each other.
- Non-activation logs were described too strongly as durable transactional outcomes.
- Capacity rejection lacked final/no-backfill semantics.
- Poller and NGINX process-death behaviour was unspecified.
- Snapshot HTTP redirects were not explicitly rejected.
- Canonical IP uniqueness claims were stronger than the textual database index actually guaranteed.
- Rule-ID scans were not planned as repeatable integration evidence.
- Performance benchmarking overloaded T0.
- The old plan was too long for reliable AI implementation.

## 26.3 Claude independent review

Accepted findings:

- Explicitly separate writer isolation from snapshot isolation.
- Use writer READ COMMITTED with singleton locking.
- Distinguish reload timing proof from candidate-content proof.
- Record rule-ID provenance, not only PASS/FAIL.
- Ensure one-shot control uses the same running container and lock inode.

Moderation:

- Writer isolation ambiguity was treated as High rather than an architectural Critical once the correction was straightforward.
- Future CRS-upgrade guarantees were rejected; pinned-image rescanning is sufficient.

## 26.4 Unbiased ChatGPT independent review

Accepted findings:

- Define canonical state-checksum input and exclude `generated_at`.
- Separate state checksum and candidate-file checksum.
- Persist selected-source identity, not ambiguous latest-observed authority.
- Define lifecycle ownership, supersession, revocation, and no resurrection.
- Add pre-NGINX startup recovery.
- Add database/WAF clock evidence.
- Specify source provenance hop by hop.
- Add explicit lower/equal-conflicting/higher revision behaviour.
- Pin fixed lock path, persistence boundary, and inode policy.
- Pin SQLAlchemy version/driver and verify transaction settings in real PostgreSQL.
- Distinguish absolute expiry from control-plane revocation.
- Freeze candidate immutability and metadata ordering.
- Make the wire contract exact enough for an AI implementation agent.

Moderated findings:

- Graceful old-worker drain is preferred, but the thesis may narrow its claim to fresh connections if bounded drain requires disproportionate machinery.
- Exhaustive crash injection was reduced to representative boundaries.
- Host-power-loss durability was rejected.
- A large persistent runtime-state framework was rejected.
- Failed observations remain in logs rather than full durable metadata.

---

# 27. Current latest-document status

The current documents already incorporate most synthesis corrections.

The latest implementation contract is approximately 351 lines and includes:

- Thesis/local gates.
- Trusted source-provenance rule.
- Dedicated lifecycle and owner semantics.
- Writer READ COMMITTED and snapshot Repeatable Read.
- Canonical state checksum.
- Candidate checksum.
- Selected-source metadata.
- Fixed activation lock.
- Same-container controls.
- `pending_empty`.
- Pre-NGINX startup gate.
- Reload timing/content split.
- Bounded old-worker-drain preference.
- Revocation/expiry distinction.
- Ordered stages and minimum tests.

The current T0 evidence template is approximately 143 lines and includes:

- Full version inventory.
- Rule-ID provenance.
- Clock samples.
- Expanded URI matrix.
- Source-provenance matrix.
- Reload/worker evidence.
- Lock and one-shot evidence.
- Startup cases.
- Process topology and persistence boundary.

Historical run instructions above are superseded by E28 and E29; the current
T0 result is `GO`.

---

# 28. Final outstanding document corrections

These were the residual corrections identified in the earlier review. They are
historical context; E28 and E29 have since closed T0. T1 remains unstarted and
requires separate authorization.

## 28.1 Required before T0

### Add clock relationship to the foundational gate table

The current T0 file has a clock section but the clock relationship must also appear in the foundational stop-gate table.

Suggested row:

```markdown
| Database/WAF clock relationship | `NOT_RUN` | Repeated PostgreSQL `clock_timestamp()` and WAF `TIME_EPOCH` samples satisfy the approved relationship or safety margin; otherwise hard expiry is BLOCKED | NOT_RUN |
```

Also state that a failed or unproved relationship blocks the no-later-than-persisted-expiry claim and later implementation.

## 28.2 Required before T1

### Fix cardinality wording

Replace:

```text
One effective-state row exists per recommendation.
```

with:

```text
At most one effective-state row may exist per recommendation.
Only an eligible recommendation that becomes an effective ACTIVE owner creates
one. Already-expired, duplicate, shorter/equal, and capacity-rejected outcomes
create no new effective-state row.
```

Add or retain `UNIQUE (recommendation_id)`.

## 28.3 Required before T2/T3

### Add expired-ACTIVE snapshot invariant

Add normative wording that snapshots include status=ACTIVE rows without filtering by the current time and that only revisioned cleanup removes them.

## 28.4 Required before T4B

### Exclude activation lock from pruning

State that candidate pruning touches only candidate files and never the permanent activation lock, metadata, latch, or canonical empty candidate.

## 28.5 Required before T4A

### Freeze deterministic rule-ID assignment

Use canonical sort order plus range-start position unless repository constraints require another T0-approved deterministic mapping.

## 28.6 Required before T3

### Freeze body and authentication details

- 1 MiB hard response ceiling.
- Bearer header name/secret source.
- 401/404/503 behaviour.
- `Cache-Control: no-store`.
- Token logging prohibition.

## 28.7 Required before T4B/T4C

### Clarify empty checksums and pending retry

- Empty selected kinds still require canonical empty-file checksum.
- Unlatched enforce + `pending_empty` retries every polling interval.
- Enable output must not imply authoritative rules are already active.

---

# 29. Current readiness decision

| Area | Current decision |
|---|---|
| Architecture | GO |
| Thesis scope | GO |
| Document split | GO |
| Broad redesign review | Stop; no longer useful |
| T0 template | Conditional GO after adding clock as foundational gate |
| T0 execution | GO after that edit |
| T1 | Blocked until T0 passes and cardinality wording is corrected |
| T2 | Blocked until T0 passes and expired-ACTIVE snapshot invariant is normative |
| T3 | Blocked until T0 passes and exact auth/body details are frozen |
| T4A | Blocked until T0 passes and deterministic IDs are frozen |
| T4B | Blocked until T0 proves placement/reload/startup mechanics |
| T4C | Blocked until real lock/control path passes T0 |
| Local ENFORCE | Not authorised until T1–T5 pass and separate approval is recorded |
| Hosted/staging/production | Out of scope and off |

The project is no longer in redesign territory. The correct next action is to make the residual edits, execute T0, and let pinned-runtime evidence determine any later adjustment.

---

# 30. Instructions for an AI coding/review agent

The AI should:

1. Read the implementation contract first and treat it as normative.
2. Read the T0 evidence and treat every `NOT_RUN` as unknown.
3. Never assume commands, paths, image behaviour, SQLAlchemy APIs, ModSecurity syntax, or process topology.
4. Inspect the live repository and pinned environment for every T0-derived value.
5. Stop on a foundational T0 failure rather than silently weakening the claim.
6. Preserve PR5, PR6, static CRS, portal behaviour, hosted topology, and non-local off state.
7. Use repository conventions rather than inventing file placement or abstractions.
8. Keep tasks stage-bounded; do not implement later-stage mechanisms early.
9. Add tests with each behaviour change.
10. Separate pure logic from runtime mutation.
11. Never log secrets or raw complete `nginx -T` output.
12. Avoid new dependencies unless explicitly authorised and proven necessary.
13. Do not add enterprise infrastructure.
14. Report exact changed files, commands, test results, and remaining risks.
15. Leave the controlled environment latched disabled and empty after proof.

When uncertain:

- Prefer a T0 experiment to speculative architecture.
- Prefer a minimal correction to redesign.
- Distinguish verified fact, T0-derived fact, assumption, and recommendation.
- Do not describe local evidence as hosted or production readiness.

---

# 31. Recommended opening prompt for the permanent chat

Copy the following message into the permanent chat after uploading this handoff and the four current PR7 documents:

```text
This chat is the permanent working chat for PR7 Controlled CRITICAL WAF
Enforcement in the CyberTrace thesis project.

Read these files completely before responding:

1. PR7_PERMANENT_CHAT_HANDOFF.md
2. PR7_IMPLEMENTATION_SPEC.md
3. PR7_DESIGN_RATIONALE.md
4. PR7_T0_EVIDENCE.md
5. PR7_CONTROLLED_CRITICAL_WAF_ENFORCEMENT_PLAN.md

Authority order:
- PR7_IMPLEMENTATION_SPEC.md is normative.
- PR7_T0_EVIDENCE.md records actual feasibility; E28 and E29 establish T0 GO.
- PR7_DESIGN_RATIONALE.md explains decisions.
- The document index is only navigation/status.
- The handoff preserves prior review context and outstanding corrections.

Do not redesign the architecture from scratch and do not recommend enterprise
infrastructure. This is a local, controlled, thesis-level proof. Hosted,
staging, and production remain off and out of scope.

First, verify whether the final outstanding corrections in section 28 of the
handoff are already present in the current files. Report only:

1. Corrections already incorporated.
2. Exact remaining edits, with file and section.
3. Whether T0 may start.
4. The objective next action.

Treat every NOT_RUN entry as unknown, never PASS. Do not implement T1 or later
until every foundational T0 gate passes and the required approval is recorded.
```

---

# 32. Final concise handoff statement

PR7 has a sound thesis-scale architecture and a disciplined scope. The important correctness mechanisms are justified and should remain: a dedicated effective-state table, atomic writer transaction, singleton revision lock, Repeatable Read snapshot, explicit ownership/supersession, absolute expiry, deterministic checksums and renderer, validation before selection, one previous candidate, selected-source metadata, a permanent shared activation lock, poller-independent disable, pre-NGINX startup recovery, source/path proof, and static CRS/PR6 regression evidence.

The project should not undergo another broad architecture redesign. Apply the small residual document corrections, run T0, and use observed pinned-runtime evidence as the source of truth for the implementation stages that follow.
