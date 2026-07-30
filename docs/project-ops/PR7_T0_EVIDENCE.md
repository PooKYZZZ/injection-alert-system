# PR7 T0 feasibility evidence

> Historical feasibility record. Later Block 1/Block 2 implementation results
> are recorded in `PR7_BLOCK_2_EVIDENCE.md` and `STATUS.md`.

**Status: T0: GO.** E28 closes controlled source identity and E29 closes
process topology and persistence. Every foundational gate passes, subject only
to the accepted disabled-runtime-IPv6 exception. This does not authorize T1-T6,
local `ENFORCE`, or hosted activation; T1 and later require separate approval.
Earlier failed and `NOT_RUN` observations below are historical or superseded
by E28/E29.

## Run identity and safety boundary

| Field | Value |
| --- | --- |
| Continuation observation time | `2026-07-27T15:14:29Z` as reported by the local shell |
| Operator | `froipc\\froi` |
| Repository | `G:\\AI\\PDDDD\\injection-alert-system` |
| Branch / commit | `master` / `09f4d80defabd9b01e588d0d546ba006e96735d9` |
| Governing documents | All five exact PR7 documents were reread completely; SHA-256/line-count read audit: spec 420 lines, evidence 193 lines before this update, rationale 120 lines, handoff 1736 lines, plan 14 lines |
| Pre-existing worktree | Five untracked PR7 documents; no tracked files modified |
| Runtime scope | Local Compose only; pinned WAF digest; no hosted/staging/production environment; no PR7 migration, schema, renderer, synchroniser, control command, or local `ENFORCE` |
| Secret handling | Temporary local test values were passed through process environment only and were not recorded |

## Evidence audit

`PR7-T0-E01` through `PR7-T0-E09` remain supported by exact commands,
bounded observations, and evidence IDs in the prior record. They cover the
five-document prerequisite, local WAF-only bring-up, effective include source,
baseline versions, live path-first syntax, invalid-candidate rejection,
fresh-connection reload/content proof, baseline restore, and cleanup.

No prior PASS was downgraded. `PR7-T0-E08` remains `NOT_RUN` in the prior
record and is completed below as `PR7-T0-E10` with an exact range. The prior
backend-not-started statement is superseded by the isolated backend probe,
which was local and disposable but did not complete the full Browser ->
Next.js -> FastAPI source path.

## New executed evidence

| Evidence ID | Gate / exact command | Exit | Bounded observation | Result |
| --- | --- | ---: | --- | --- |
| `PR7-T0-E10` | `docker exec ... find /etc/modsecurity.d /opt/owasp-crs -type f -name "*.conf" -exec sed -n "s/.*id:\\([0-9][0-9]*\\).*/\\1/p" {} + \| sort -n -u`; PowerShell integer filter `10000..10511` | 0 | Live IDs ranged from `1234` to `9006970`; exact approved local-use candidate `10000-10511` contains 512 contiguous IDs and `collision_count=0`. ModSecurity local/internal convention and CRS `900000-999999` convention were consulted. | PASS for this pinned digest/config. Any digest or config change requires a rescan. |
| `PR7-T0-E11` | Disposable source topology: `docker compose -f docker-compose.yml -f docker-compose.source-correlation-test.yml -f docker-compose.source-correlation-test.override.yml --profile source-correlation-test up -d --no-build ...` | 0 after bounded startup | Backend used `APP_ENV=testing`, SQLite `/tmp/source-correlation-test.db`, and baseline `init_db()`; no Alembic/PR7 migration ran. Internal networks were used. | PASS for local/disposable backend-safe setup; the first build attempt timed out and was not used as evidence. |
| `PR7-T0-E12` | `docker exec source-test-client-a curl ... /api/alerts`; forged `X-Forwarded-For`, `X-Real-IP`, and `CF-Connecting-IP`; bridge SQLite query of `traffic_logs`; WAF access-log query | 0 | Trusted path client `172.30.10.4` produced WAF `remote_addr=172.30.10.4`, `realip_remote_addr=172.30.10.2`, `cf_connecting_ip=172.30.10.4`; persisted row stored `source_ip=172.30.10.4`, `DIRECT_REMOTE_ADDR`. Forged values did not change the persisted source. Untrusted direct client `172.30.11.4` remained the WAF source despite forged headers. | PASS for the exercised WAF -> FastAPI direct source invariant and header-forgery cases; full Next.js hop remains unproved. |
| `PR7-T0-E13` | Three paired samples: PostgreSQL `psql ... select extract(epoch from clock_timestamp())`; WAF temporary `SecRule ... msg:'PR7_T0_CLOCK epoch=%{TIME_EPOCH}'`; `docker exec` request; UTC shell timestamp | 0 | Samples: `PG=1785164896.070141`, `WAF=1785164896`, diff `0.070141`; `PG=1785164897.325594`, `WAF=1785164897`, diff `0.325594`; `PG=1785164898.489830`, `WAF=1785164898`, diff `0.489830` seconds. Temporary PostgreSQL container had no volume and was removed. | PASS WITH MARGIN. WAF epoch is whole-second precision; later renderer must subtract exactly 1 whole second. |
| `PR7-T0-E14` | `docker exec` same-container `/usr/bin/flock -x /pr7-state/activation.lock`; second nonblocking `flock`; `stat`; candidate create/delete; `docker exec` cleanup | 0 | Lock inode `85243`, owner `0`, group `0`, mode `600`; holder acquired; contender was blocked with rc `1`; inode remained `85243` before/after candidate cleanup. Disposable `/pr7-state` was removed. | Partial mechanics PASS only; separate second `docker exec` and persistent mount/recreation proof remain `NOT_RUN`. |
| `PR7-T0-E15` | Temporary URI rule `id:1000005` logging `REQUEST_URI` and `REQUEST_FILENAME`; GET/query/trailing/doubled/encoded/case/parent/HEAD/POST requests to `127.0.0.1:8089` | 0 | `/records/search` literal baseline was `200`; query, trailing slash, doubled slash, encoded `s`, encoded slash, HEAD, and POST were individually observed by the rule. Query preserved `REQUEST_FILENAME=/records/search` while `REQUEST_URI` retained `?query=x`; `%2F` normalized to `/records/search/`; uppercase `/RECORDS/search` bypassed the rule and reached Next.js with `404`; `../` normalized to the protected path. | PASS for the required local URI/method matrix, with observed normalization recorded rather than inferred. |
| `PR7-T0-E16` | Temporary phase-1 deny; `Invoke-WebRequest /records/search`; WAF audit/error fields; `docker logs --since 2s demo-portal`; normal `/`; static CRS control | 0 for probe/restore | PR7 probe response was `418`, rule `1000005`, tag `PR7_T0_uri_matrix`, `REQUEST_URI=/records/search`, `REQUEST_FILENAME=/records/search`, no portal log lines in the request window. Normal `/` was `200`. Static CRS control was `403` with rule `949110` in NGINX error evidence. | PASS for bounded no-upstream sentinel: PR7-tagged phase-1 deny plus zero portal-log activity; normal control independently reached Next.js. |
| `PR7-T0-E17` | Pinned image `docker inspect`; `docker exec id/ls`; bounded `/docker-entrypoint.sh` and `/docker-entrypoint.d` inspection | 0 | Image digest remained `sha256:0385...911e`; entrypoint `/docker-entrypoint.sh`, command `nginx -g daemon off;`, runtime user `nginx`. Entrypoint runs `/docker-entrypoint.d/*` before `exec "$@"`; same-container `docker exec` is available. No `/pr7-state` mount exists in current Compose. | Partial placement feasibility only; persistent mount, final pre-NGINX gate, and unexpected synchroniser death behavior are not established. |
| `PR7-T0-E18` | Disposable startup probe mounted as `/docker-entrypoint.d/00-pr7-startup-probe.sh`, command `nginx -t -q`, six state cases | 0 for all six | Probe wrote `before_nginx=1`. Latch + stale candidate, mode `off` + stale candidate, missing, corrupt, and metadata-only cases all selected `decision=empty`; matching candidate + metadata selected `decision=nonempty`. No final PR7 runtime file was retained. | PASS for startup-order/safe-empty feasibility of the disposable harness; final startup gate remains unimplemented and not authorized. |
| `PR7-T0-E19` | Disposable child exit and `kill -TERM 1`; `docker inspect` before/after; attempted container restart | 0 for commands; restart exited 1 | Disposable child exited `143` while NGINX remained running. Terminating PID 1 left the container `exited` with exit `0`. Restart of the mutated probe container failed during entrypoint regeneration because the temporary root-owned override was not writable by runtime user `nginx`; fresh-container recreation was not used to claim restart persistence. | NOT_RUN for the complete topology/restart/persistence gate; the observed restart limitation is retained as a blocker. |

## Foundational gate outcomes

| Gate | Result | Evidence / reason |
| --- | --- | --- |
| Include and syntax | PASS | `E03`, `E05`, `E06`, `E09` |
| Candidate/live equivalence | PASS | `E03`, `E05`; only bounded temporary include difference was used |
| Candidate validation | PASS | Valid path-first probe passed `nginx -t -q`; invalid directive failed it |
| Pinned placement | PASS | `E21` and `E22` prove persistent `/pr7-state` placement, separate-process lock exclusion, recreation, and state survival; process death remains a separate gate |
| Rule-ID provenance | PASS | Exact approved range `10000-10511`, 512 IDs, zero live collisions in pinned scan (`E10`) |
| Reload and content | PASS | Prior `E07`/`E09` fresh-connection generation/content proof |
| URI mapping | PASS | Full required local matrix in `E15`; uppercase and normalization boundaries observed |
| Source equivalence | PASS for controlled T0 harness | `E28`: persisted source equals ModSecurity `transaction.client_ip`, NGINX effective remote address, and Cloudflare visitor identity `112.201.128.235` |
| Header-forgery resistance | PASS | `E28` rejects forged cross-container forwarding; earlier direct-topology resistance remains historical `E12` |
| Direct-origin isolation | PASS | `E28`: no WAF host port and direct-origin HTTP `000` during the target-only proof |
| No-upstream proof | PASS bounded local | `E16`: phase-1 PR7 tag, exact rule/URI fields, no portal log lines; normal and CRS controls separate |
| Database/WAF clock relationship | PASS WITH MARGIN | `E13`; exact required margin is 1 second |
| Activation control | PASS | `E14`, `E21`, and `E22` prove lock exclusion, separate-process contention, persistent mount, and recreation survival |
| Startup safety | PASS feasibility only | `E18` proves pre-NGINX ordering and safe-empty cases using a disposable harness |
| Empty, static CRS, and PR6 regression | PASS | Empty/CRS restoration in `E09`/`E16`; unchanged backend and portal regression suites passed in `E24`/`E25` |
| Process topology and persistence | PASS | `E29`: valid derivative-image bootstrap, direct-child supervision, unexpected child death, SIGQUIT/TERM/INT forwarding, child reaping, nonzero failure, clean shutdown, and named-volume recreation |

## Source identity invariant

The exact candidate invariant established for the exercised topology is:

```text
persisted traffic_logs.source_ip
== WAF ModSecurity REMOTE_ADDR
== direct socket source selected by the WAF real-IP configuration
```

Observed value: `172.30.10.4`; provenance:
`DIRECT_REMOTE_ADDR`; verification status in the existing application record:
`UNVERIFIED`. This is not a full PR7 source-equivalence PASS because the
required Next.js hop was not present in the disposable source topology.

## Clock outcome

**PASS WITH MARGIN.** PostgreSQL `clock_timestamp()` was later than WAF
`TIME_EPOCH` by less than one second in all three samples. The exact whole
second margin required for a later renderer is **1 second**. No renderer was
implemented.

## Final closure evidence

| Evidence ID | Gate / exact command | Exit | Bounded observation | Result |
| --- | --- | ---: | --- | --- |
| `PR7-T0-E20` | `docker ps -a`; `docker inspect injection-alert-system-backend-1 --format ...`; `git status`; temp-file/container/network checks | 0 | The backend container present at closure was created at `2026-07-27T15:02:20Z` and exited `137`. The preceding recorded pre-closure state was an exited backend container created four days earlier, but its original ID/config was not captured. Current state was restored to exited; exact pre-T0 identity cannot be reconstructed. | PARTIAL baseline restoration; cleanup completeness is not claimed as exact identity restoration. |
| `PR7-T0-E21` | Temporary Compose override adding named volume `pr7closure_pr7_state:/pr7-state`; `docker inspect`; `docker volume inspect`; separate `docker exec` holder and contender commands | 0 | Named volume mounted at `/pr7-state`; lock owner `101`, group `0`, mode `660`, inode `83445`. Holder acquired; separate host-issued `docker exec` contender returned rc `1` while held and acquired after release. Candidate-only pruning removed `candidate.test` while preserving lock, latch, empty, and metadata files. | PASS persistent placement and separate-process lock mechanics. |
| `PR7-T0-E22` | Initial checksums; `docker rm -f pr7closure-demo-target-modsecurity-1`; Compose recreation with the same temporary override; checksums/state/stat/`nginx -t -q`/portal/CRS controls | 0 | Container changed from `4f55...51d6` to `3631...adfd`; volume remained `pr7closure_pr7_state`; lock inode remained `83445`; lock/latch/empty/metadata checksums remained the empty-file SHA-256; NGINX validation passed; portal control `200`; CRS control `403`. | PASS recreation persistence for the disposable named volume. |
| `PR7-T0-E23` | `docker exec ... sleep; kill child; wait`; `docker exec ... kill -TERM 1`; `docker inspect`; Compose recreation | 0 | Disposable child exited `143` while NGINX stayed alive. PID 1/NGINX master termination left the container exited with code `0`. Recreate from the same volume restored state and passed `nginx -t -q`. | PARTIAL process proof; unexpected synchroniser-like child death does not terminate the container. Pinned image requires a minimal PID-1 wrapper for the documented process-death semantics. |
| `PR7-T0-E24` | `.venv\\Scripts\\python.exe -m pytest -q tests/unit/test_enforcement_repository.py tests/unit/test_enforcement_use_cases.py tests/unit/test_enforcement_policy.py tests/integration/test_enforcement_check_route.py` | 0 | `49 passed` in `6.88s`; no PR6 source or test file was modified. | PASS unchanged backend PR6 HIGH regression coverage. |
| `PR7-T0-E25` | `npm run test:unit` in `G:\\AI\\land-records-portal` | 0 | TAP summary: `32 passed`, `0 failed`, `0 skipped`; no portal source or test file was modified. | PASS unchanged portal PR6 regression coverage. |
| `PR7-T0-E26` | `Get-Content web_app/domain/source_address.py`; unchanged `tests/unit/test_source_address.py` and `tests/unit/test_source_verification.py`; pure `ipaddress` probe | 0 | Repository convention is Option A: `::ffff:203.0.113.7 -> 203.0.113.7`. Repository tests: `21 passed`; pure cases covered IPv4, expanded/compressed IPv6, case normalization, dotted/hex mapped IPv6, equality, invalid forms, whitespace, and deterministic output. Runtime IPv6 remained disabled. | PASS mapped-IPv6 exception under the existing repository convention; no normative document edit was needed. |
| `PR7-T0-E27` | `docker compose -p pr7closure ... down -v`; exact `docker rm -f`, `docker volume rm pr7closure_pr7_state`, `docker network rm pr7closure_default`; final Docker/temp/git checks | 0 | Temporary portal/WAF containers, named volume, network, override, and disposable state were removed. No `pr7closure`, `source-test`, `demo-target`, or `pr7-t0-postgres` resources remain. | PASS disposable cleanup; exact pre-T0 backend identity remains the baseline uncertainty recorded in `E20`. |

## E28 source-identity closure

`PR7-T0-E28` is the corrected guarded target-only Cloudflare overlay proof
recorded in `SOURCE_CORRELATION_PROOF.md`: marker
`CF-VERIFIED-PROOF-1785214180455`, transaction `178521418071.169644`, and
`/records/search` returned the expected `403`. Immediate peer was
`172.30.20.2`; effective visitor, ModSecurity `transaction.client_ip`, and
persisted source were all `112.201.128.235`, with provenance
`CLOUDFLARE_CONNECTING_IP`, verification `VERIFIED`, bridge HTTP `200`, and
`BLOCKED/COMPLETED`. Forged cross-container forwarding was rejected; no WAF
host port and direct-origin HTTP `000` remained. Home/mobile separation, no
workers, Pseudo IPv4 off, and restored normal runtime were observed.

Result: PASS for controlled T0 source equivalence, header-forgery resistance,
and direct-origin isolation. This is a T0 harness result, not hosted or
production authorization. Earlier failed and direct-topology attempts remain
historical evidence.

`PR7-T0-E29` valid derivative-image process-topology proof passed. The
derivative used the exact pinned CRS digest, an exec-form PID-1 wrapper, the
original `/docker-entrypoint.sh nginx -t -q` bootstrap, and a non-forking fake
synchroniser. Stage 4 emitted `supervisor-ready` with PID 1 supervising NGINX
and the synchroniser. Killing the synchroniser produced wrapper exit `72` and
`unexpected-sync reaped=2`; killing NGINX produced exit `71` and
`unexpected-nginx reaped=2`. Docker stop delivered inherited `SIGQUIT` and
produced exit `0` with `clean-shutdown signal=QUIT reaped=2`; explicit SIGTERM
and SIGINT also exited `0` with `reaped=2`. Named-volume recreation preserved
the pre-existing marker and the recreated wrapper reached readiness. The
derivative image, containers, and volume were removed after the proof.

## Final source and IPv6 decisions

The controlled T0 source-equivalence gate is **PASS** via `E28`. The exact
verified equality is `persisted source_ip == ModSecurity transaction.client_ip
== NGINX effective remote_addr == Cloudflare visitor identity ==
112.201.128.235`.
E28 proves the controlled target-only source-identity harness. It does not
authorize hosted or production readiness, final hostname cutover, or verified
normal runtime; normal runtime remains `DIRECT_REMOTE_ADDR` / `unverified`.

The mapped-IPv6 policy is explicitly established by live repository convention,
not silently invented: **Option A, collapse mapped IPv6 to IPv4**. Runtime IPv6
remained disabled and no runtime IPv6 claim is made.

## Cleanup and safe state

- Restored both temporary ModSecurity override files to their original single-comment contents.
- `nginx -t -q` passed after restoration; WAF loaded 928 rules.
- Normal `/records/search` returned `200`; static CRS control returned `403`.
- Removed temporary include backups, `/pr7-state`, startup state, probe script, disposable PostgreSQL, source-correlation containers, demo-target containers, and source-test networks.
- Removed the disposable `pr7closure_pr7_state` named volume and `pr7closure_default` network after recreation evidence.
- No raw `nginx -T` dump was retained.
- No PR7 migration, effective-state table, renderer, synchroniser, control command, or local `ENFORCE` was created or used.
- Final runtime check: no source-test, demo-target, `pr7closure`, or `pr7-t0-postgres` resource remains. The backend container name remains exited; exact pre-T0 container identity restoration is unknown.

## Final T0 decision

**T0: GO.** E28 proves
the controlled source-identity gate. Persistent placement, separate-process
lock exclusion, recreation persistence, unchanged PR6 regression, and the
mapped-IPv6 exception are also proven. The only remaining foundational gate is
the disposable minimal PID-1 wrapper, now proven by `E29`, covering NGINX and
synchroniser death semantics, signal forwarding, child reaping, nonzero
unexpected exit, clean shutdown, and state-volume survival. T1 and later
stages remain blocked.

Objective next action: preserve the T0 evidence and obtain explicit
authorization before beginning any separately scoped T1 work. Do not implement
T1 schema or migrations, final PR7 runtime, local `ENFORCE`, or hosted
activation automatically.
