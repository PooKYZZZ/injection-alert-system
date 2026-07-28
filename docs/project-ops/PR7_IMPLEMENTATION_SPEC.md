# PR7 Controlled CRITICAL WAF Enforcement — implementation contract

## 1. Scope, authority, and gates

PR7 is a local, controlled, thesis-only WAF enforcement slice for verified,
non-Normal `CRITICAL` recommendations. It is separate from PR5 LOW/MEDIUM and
PR6 HIGH application blocking. It must not alter PR6, static CRS, confidence
thresholds, action transport contracts, the portal, hosted topology, or
production/staging activation.

The route remains Browser -> Next.js route handler -> FastAPI. The WAF is a
local reverse-proxy data-plane only; no browser code may call FastAPI directly.
No Docker socket, queue, new dependency, CI change, secret exposure, physical
audit-data deletion, or portal CRITICAL logic is permitted.

For T0 source-identity feasibility only, a target-only isolated Cloudflare
overlay may be used as a controlled source-identity harness. This does not
authorize hosted or production PR7 enforcement, final-hostname cutover,
verified normal runtime, or T1 and later implementation.

The application request path and the security-evidence path are distinct:

```text
Application:       Browser -> WAF -> Next.js -> FastAPI
Security evidence: ModSecurity audit transaction -> bridge -> FastAPI persistence
```

Before T1 or later work, every foundational T0 stop gate in
`PR7_T0_EVIDENCE.md` must **PASS**. Runtime IPv6 may remain `NOT_RUN` only when
IPv6 enforcement remains disabled and pure canonicalisation and mapped-address
policy tests pass. Local `ENFORCE` and migration/Compose work require their
separately recorded approvals. Hosted, staging, and production remain `off`.

## 2. Source identity and fixed policy

Eligibility requires a verified canonical source IP, an allowed literal
protected path, a non-Normal prediction, `CRITICAL` tier, a valid future
expiry, and local controlled mode.

Untrusted client-supplied forwarding headers never select enforcement identity.
A trusted proxy-overwritten value may be used only when T0 proves that it
equals the WAF's effective `REMOTE_ADDR` for the actual local request path.
T0 records the socket peer and every overwrite point at each hop.

Canonicalise source IPs with `ipaddress` before **every** WAF-entry write.
Direct uncanonicalised ORM construction is forbidden. Freeze mapped-IPv6 policy
before T1. IPv4, IPv6, and mapped-address behavior require deterministic pure
tests even when runtime IPv6 is disabled.

The renderer emits chain order:

```text
REQUEST_FILENAME exact literal path
-> REMOTE_ADDR canonical source
-> TIME_EPOCH absolute expiry
```

Disruptive actions and PR7/revision/recommendation tags appear only on the
starter rule. Absolute expiry is floored to seconds and cannot outlive
persisted expiry. Static CRS remains active. A PR7 block is a tagged generic
403 and must prove no upstream portal attempt. PR6 HIGH remains unchanged.

## 3. Database lifecycle and mutation contract

Use an additive dedicated effective-state table; do not add ACTIVE lifecycle
defaults to historical recommendations. Repository names and migration shape
follow live conventions discovered after T0, but these semantics are fixed.

### 3.1 Cardinality and lifecycle

- At most one effective-state row may exist per recommendation, enforced by
  `UNIQUE (recommendation_id)`.
- Only an eligible recommendation that becomes an effective ACTIVE owner
  creates a row. Already-expired, duplicate, shorter/equal, and
  capacity-rejected outcomes create no new row. A longer recommendation that
  becomes the owner creates its own row and supersedes the previous ACTIVE row.
- Status values are exactly `ACTIVE`, `SUPERSEDED`, `REVOKED`, and `EXPIRED`.
- Allowed transitions are `ACTIVE -> SUPERSEDED`, `ACTIVE -> REVOKED`, and
  `ACTIVE -> EXPIRED`. Terminal rows never become `ACTIVE` again.
- At most one ACTIVE owner exists for a canonical
  `(source_ip, protected_path)` pair, enforced by a partial unique index.
- A longer eligible recommendation may supersede the current ACTIVE owner.
  Superseded history never falls back or resurrects.
- Revoking the ACTIVE owner removes its block. Revoking superseded history
  changes no desired state. There is no fallback to an earlier owner.
- An already-expired candidate creates no effective-state row or revision.
- Capacity is checked under the mutation lock: default 64, hard maximum 512.
  Rejection is final; later cleanup does not backfill old recommendations.
- Foreign-key deletion is restricted so recommendation history cannot silently
  erase effective-state provenance.

### 3.2 Writer transaction

Every mutation writer uses `READ COMMITTED`, an ordinary singleton `BIGINT`
revision column, and never a database sequence. All write paths use this order:

```text
BEGIN at READ COMMITTED
1. Lock waf_enforcement_state id=1 FOR UPDATE.
2. Read mutation_now using clock_timestamp().
3. Insert or find the recommendation idempotently.
4. Mark expired ACTIVE rows EXPIRED.
5. Resolve duplicate, extension, capacity, supersession, or revocation.
6. Increment the BIGINT revision exactly once iff desired state changed.
7. Stamp every changed WAF row with that revision.
8. COMMIT.
```

The singleton row is always the first database lock. Read `mutation_now` after
it so a lock wait cannot stale the eligibility time. No network call or
operator interaction occurs inside the transaction. Recommendation creation
and its effective-state mutation commit together. An exception rolls back the
recommendation, state rows, and revision.

A duplicate alone changes neither state nor revision. A duplicate transaction
that also expires ACTIVE state increments once. Effective expiry only extends,
never shortens. All rows changed by one mutation receive the same revision.
Do not invent a retry framework; use bounded whole-transaction retry only if a
verified repository convention already exists.

### 3.3 Snapshot reader

Read a complete snapshot in a read-only `REPEATABLE READ` transaction. The real
integration test executes:

```sql
SHOW transaction_isolation;
SHOW transaction_read_only;
```

and observes `repeatable read` and `on`. Before T2 record Python, SQLAlchemy,
PostgreSQL driver, and PostgreSQL versions. Apply SQLAlchemy isolation options
before `begin()` or any statement that triggers autobegin.

Read the singleton revision and every ACTIVE row from the same database view.
Do not filter ACTIVE rows by `expires_at`. Time passage alone changes neither
desired-state rows, revision, nor state checksum. An expired ACTIVE row remains
in the snapshot until an explicit revisioned cleanup changes it to EXPIRED. Its
rendered `TIME_EPOCH` condition is already false, so retaining it cannot extend
enforcement. Thus the same revision retains the same authoritative content and
checksum until a lifecycle mutation occurs.

## 4. Snapshot API and checksums

The authenticated endpoint is read-only, local-network only, and disabled
outside controlled local mode. Its exact request is:

```http
GET /api/internal/waf-enforcement/snapshot
Authorization: Bearer <WAF_STATE_SYNC_API_KEY>
Cache-Control: no-store
```

Missing or invalid token returns 401; disabled snapshot functionality returns
404; database/snapshot failure returns safe 503; success returns 200. Compare
the token with a standard-library constant-time comparison. Never log the token
or response body at normal level. No HMAC, internal TLS, or key-management
service is required by the accepted local threat model.

The successful response is exactly:

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

Reject unknown top-level/item fields, unsupported schema, wrong policy/scope,
malformed values, duplicate identities, and naive datetimes.
`utc_millis(value)` raises `ValueError("UTC-aware datetime required")` when
`tzinfo` or `utcoffset()` is missing and converts aware values to UTC
milliseconds with `Z`.

The client accepts only the exact configured origin, HTTP 200, and parsed
`application/json` media type with optional charset. It never follows
redirects. It enforces maximum size while streaming and one configured total
deadline covering connect, headers, and body. Server and client enforce a hard
snapshot-response ceiling of 1 MiB. The development ACTIVE cap is 64 and the
absolute entry ceiling is 512. T3 proves that 512 maximally bounded entries fit
below 1 MiB; otherwise adjust field bounds or the approved ceiling before
implementation.

### 4.1 Authoritative state checksum

Compute `state_checksum_sha256` over only `schema_version`, `policy_version`,
`revision`, `scope`, and `items`. Exclude `generated_at`, the checksum field,
HTTP headers, and response whitespace. Sort items by IP version, packed IP
bytes, request path, expiry epoch, recommendation ID, then entry ID. Serialize:

```python
json.dumps(
    state_object,
    ensure_ascii=True,
    sort_keys=True,
    separators=(",", ":"),
    allow_nan=False,
).encode("ascii")
```

### 4.2 Candidate checksum

`candidate_file_checksum_sha256` is SHA-256 over the exact rendered
ModSecurity candidate bytes. It is distinct from the state checksum. The same
state produces byte-identical candidates; any byte change changes this checksum.

## 5. Runtime and persistent state

The persistent directory is `/pr7-state`, backed by a named volume or approved
bind mount. Selection uses same-filesystem atomic replacement. It contains:

- `activation.lock`, permanent and never pruned, replaced, renamed, or unlinked;
- current selection and previous candidate;
- the canonical empty candidate;
- selected metadata;
- the optional `DISABLED` latch; and
- a bounded number of unfinished temporary candidate files.

Candidates are immutable from validation through selection. Candidate pruning
operates only on candidate files and never touches `activation.lock`, metadata,
the latch, or canonical empty candidate. Host power-loss durability, directory
`fsync`, and power-cut tests are out of scope.

T0 proves syntax, include placement, and rule-ID availability in the pinned
image. A recurring integration test proves the range unused outside PR7.

Sort entries using the same canonical ordering as the state checksum. Assign
`rule_id = approved_range_start + zero_based_sorted_position`. The approved
range contains at least 512 IDs. Empty state emits no PR7 rule. IDs are
generation-local, not stable correlation identity; revision and recommendation
tags provide correlation. Tests prove same state and different input order
produce the same IDs/bytes, and 513 items fail before rendering.

### 5.1 Selected-state metadata

Persist selected/applied state only:

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

For `authoritative`, both source fields are required. For every empty kind they
are `null`. `selected_file_checksum_sha256` remains required for every selected
kind; for every empty kind it is the canonical empty candidate's checksum. The
latch file—not metadata—is disabled authority. Failed observations stay in
bounded structured logs, never selected metadata.

A failed revision 43 activation leaves revision 42 selected. Rollback restores
revision-42 bytes and metadata. The next poll retries revision 43.

- Lower revision: reject as stale and retain safe selection.
- Equal revision/different state checksum: protocol conflict; retain selection.
- Equal revision/same checksum is a no-op only when `selected_kind` is
  `authoritative`, selected source matches, the file exists, and its actual
  checksum matches metadata.
- Higher revision: validate and attempt application.
- Revision reset requires an approved disabled/reset procedure or fresh
  disposable environment.

The same authoritative revision is reapplied after any empty kind or candidate
loss/corruption.

### 5.2 Activation lock and controls

Every poller, startup, selection, rollback, disable, and enable opens the exact
fixed file `/pr7-state/activation.lock` and takes exclusive `fcntl.flock()`.
Create it once; never unlink, rename, truncate-replace, or atomically replace it.

Fetch/render may occur outside the lock, but recheck mode, latch, candidate
identity, and revision after acquisition. Hold the lock through selection,
reload, confirmation, rollback, and metadata update.

A pre-lock fetch may represent an older committed revision than the database's
latest. This eventual reconciliation is allowed when it is newer than the
locally selected revision and passes all comparison rules. The next poll
applies any later revision; the filesystem lock does not coordinate with the
PostgreSQL revision lock.

Controls use `docker exec` into the same running WAF container and invoke
`/usr/local/bin/pr7-waf-control disable|enable`. Disable works with the poller
stopped: under lock it writes the latch, selects/validates/reloads/confirms
empty, probes static CRS/control paths, and writes `disabled_empty`. Successful
disable prevents non-empty selection until explicit enable.

Enable removes the latch under lock but does not claim current rules. In
`enforce` it performs a fresh fetch. Backend failure selects confirmed empty
and records `pending_empty`; cached observations are not activated.

The completion message states:

```text
Enable completed: disable latch cleared.
Dynamic enforcement is not yet confirmed active.
Selected state: authoritative | pending_empty | mode_empty.
```

It never prints only “enabled.” While mode is `enforce`, the latch is absent,
and selection is `pending_empty`, every polling interval attempts a fresh
snapshot and authoritative application.

### 5.3 Mode and startup

| Mode | Fetch/render/validate | Non-empty selection | Selected state |
| --- | --- | --- | --- |
| `off` | No; repair empty if needed | No | `mode_empty` |
| `dry_run` | Yes | No | `mode_empty` |
| `enforce`, latched | No non-empty activation | No | `disabled_empty` |
| `enforce`, unlatched | Fresh fetch | After validation | `authoritative` or `pending_empty` |

Every `enforce -> dry_run|off` transition confirms empty. Mode changes never
remove the latch. Every `dry_run|off -> enforce` transition fetches fresh.

A pre-NGINX startup gate acquires the activation lock before traffic:

- Latch present: confirm empty and record `disabled_empty`.
- Mode not `enforce`: confirm empty and record `mode_empty`.
- Unlatched `enforce` with unavailable backend or missing/corrupt candidate:
  confirm empty, record `pending_empty`, and retain static CRS.
- Only a verified authoritative candidate may start non-empty.

Reconcile representative interrupted states: latch written before empty
selection, candidate selected before metadata, reload confirmed before
metadata, and missing/corrupt candidate. Exhaustive instruction-level crash
testing is not required.

### 5.4 Validation, reload, and rollback

Validate the immutable candidate through the same proven configuration source
with `nginx -t -q`. Then atomically select, reload, confirm a new worker
generation, run a candidate-specific fresh-connection probe, run normal/CRS
controls, and only then write selected metadata.

Generation confirmation proves reload timing. Candidate-specific probing proves
the intended content serves. Normal/CRS probes prove availability and static
CRS continuity. A PID change alone does not prove candidate content.

Prefer bounded old-worker drain. If T0 cannot prove it without disproportionate
complexity, narrow the claim to fresh connections and record existing-connection
behavior. On failure restore the previous candidate, reload/confirm it, and
restore its selected-source metadata. If none is valid, confirm empty and
record `pending_empty`.

`nginx -T` is only for T0/runtime integration tests. Redirect it to a
restrictive temporary file, retain redacted evidence, and remove it. Ordinary
reconciliation never runs it.

### 5.5 Revocation, expiry, and processes

Expiry is data-plane availability: `TIME_EPOCH` ends rules while backend and
poller are unavailable. Revocation is control-plane availability: healthy
polling must meet a configured total deadline; outage may delay revocation, but
expiry remains authoritative. Freeze polling interval, HTTP deadline, reload
allowance, and scheduling allowance before T4; report measurements at T6.

NGINX master death exits the container. Expected fetch/parse/backend errors
leave the synchroniser alive but degraded. Unexpected synchroniser death exits
the container for Compose restart. The recovery claim covers process and
container restart/recreation through the volume, not host power loss.

## 6. Ordered work and tests

1. **T0:** amend and run feasibility evidence; no performance benchmark.
2. **T1:** schema, cardinality, lifecycle, and constraints.
3. **T2:** mutation transaction and repeatable snapshot.
4. **T3:** exact authenticated wire/checksum contract.
5. **T4A:** strict client, canonicalisation, renderer, expiry, rule-ID tests.
6. **T4B:** immutable selection, startup, reload/content proof, rollback.
7. **T4C:** fixed-lock controls, latch, enable, modes, and races.
8. **T5:** local Compose plus PR6/static-CRS regressions.
9. **T5A:** measure 0/1/64/128/512 generated rules; keep cap 64 until measured.
10. **T6:** controlled E2E; finish latched disabled and empty.

Minimum tests are:

- **Database:** concurrent different-source activation; duplicate without and
  with expired cleanup; longer-owner supersession; active-owner and historical
  revocation; no resurrection; expired and capacity-rejected candidates;
  injected full rollback; one-view concurrent snapshot; real isolation and
  read-only assertions; passive ACTIVE expiry leaves revision, snapshot item,
  and checksum unchanged while its rule stops matching; explicit cleanup marks
  EXPIRED, increments once, and removes the item.
- **Snapshot/client:** `generated_at` checksum stability; changed-state checksum
  change; lower and equal-conflicting revision rejection; valid maximum body;
  redirect, malformed, oversized, unsupported-schema, and wrong-token failures;
  naive datetime rejection; deterministic IPv4/IPv6/mapped-address policy.
- **Runtime:** candidate immutability; invalid-candidate exclusion; separate
  generation/content confirmation; selected-source rollback; same-revision
  reapplication after every empty kind; missing/corrupt detection; latch-first,
  selected-before-metadata, and reload-before-metadata recovery; poller-stopped
  disable; real lock exclusion; mode-empty transitions; unavailable-backend
  `pending_empty`; claimed volume persistence; documented process deaths;
  pruning preserves the `activation.lock` inode and an already-held lock.
- **E2E:** eligible CRITICAL state and tagged generic 403; no-upstream sentinel;
  wrong source/path normal portal flow; forged-header resistance; expiry with
  backend/poller unavailable; healthy revocation deadline; outage-delayed
  revocation with expiry; static CRS and PR6 unchanged; final latched-disabled
  empty state.

## 7. Stop conditions and reporting

Stop and report `BLOCKED` for failed pinned syntax/placement,
candidate/live equivalence, validation, source equivalence/forgery resistance,
protected-path mapping, no-upstream proof, rule-ID collision, activation
control, an unproved database/WAF clock relationship, or CRS/PR6 regression.
An unproved clock relationship blocks the hard-expiry claim and T1 or later
work. Reload proof requires both generation and candidate-specific content
evidence. IPv6 may be `NOT_RUN` only under section 1.

Report exact `PASS`/`FAIL`/`NOT_RUN` commands and outcomes, migration result,
changed files, local E2E evidence, portal non-reachability, persistence
boundary, remaining risks, and confirmation that hosted/staging/production
stayed off. Leave local state latched disabled and empty.
