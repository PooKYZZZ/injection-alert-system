# Trusted Source Correlation Evidence

**Status:** Temporary target-only isolated Cloudflare source-identity proof
passed for T0; final hostname cutover was not performed, normal runtime was
restored to `unverified`, and PR7 enforcement remains disabled.
**Observed:** 2026-07-28

This document separates repository and local-runtime evidence from hosted
Cloudflare facts that have not yet been proved. Until every hosted prerequisite
is verified, `WAF_SOURCE_VERIFICATION_MODE` remains `unverified`.

The controlled proof confirmed the current trust gap:

```text
localhost process -> 127.0.0.1:8089 -> CF-Connecting-IP: 203.0.113.77
-> ModSecurity transaction.client_ip: 203.0.113.77
```

The observed `172.18.0.1/32` peer is the general Windows-host-to-Docker
gateway, not an authenticated `cloudflared` identity. It must not be used to
enable `cloudflare_tunnel` verification in the existing topology.

## Baseline

- Git base: `master` at `ac86422` (`feat: implement CyberTrace V6.1 account security`).
- Feature branch: `feat/trusted-source-correlation`.
- Alembic parent revision at feature start: `20260712_000020`.
- Docker Compose: `5.1.4`; this is newer than the plan's minimum `2.24.4`, so
  the hosted override may use `ports: !override` rather than relying on port-list
  merging.
- Backend baseline with test-only `APP_ENV=testing`,
  `NOTIFICATION_WORKER_ENABLED=false`, and
  `NOTIFICATION_WORKER_REQUIRED=false`: `619 passed, 31 skipped`.
- Without those process-only overrides, the local `.env` requires the hosted
  PostgreSQL notification worker while integration fixtures use SQLite. The
  baseline then fails at startup because SQLite has no
  `public.claim_notification_outbox_batch_v61` function. No `.env` value was
  changed for this work.

## Implemented Repository State

- Alembic now has exactly one head, `20260715_000021`.
- The full backend suite passed with process-only test settings:
  `703 passed, 32 skipped`.
- The latest focused source/integrity suite passed `189`; the migration-focused
  run passed `2` with one PostgreSQL-only test skipped locally, and the
  executable SQLite migration cycle passed.
- PostgreSQL CI upgraded from `20260712_000020` to head; `114` integration
  tests and `39` migration tests passed. The earlier local parent/head
  downgrade and re-upgrade cycle also passed; CI exercised the updated
  constraint on the full chain.
- The SQLite migration cycle is intentionally a minimal parent-shaped isolated
  execution proof for this revision's add/backfill/constraint/downgrade path.
  PostgreSQL is the authoritative full-chain proof for historical schema,
  relationships, indexes, and PostgreSQL-specific behavior.
- Compose rendering proves the default stack excludes the technical pair;
  `--profile technical-waf` restores `modsecurity` and `bridge` with `8088`.
- The hosted merge resolves only `backend`, `frontend`, `demo-portal`,
  `demo-target-modsecurity`, and `demo-target-bridge`, with exactly one
  `127.0.0.1:8089:8080` binding and no `8088`.
- The controlled merge has no published ports, uses `unverified`, and trusts
  only proxy peer `172.30.10.2/32`.
- The controlled ModSecurity audit parts are `AIJDEFHZ`; part `B` (raw request
  headers) is intentionally excluded. The bridge still receives transaction
  identity, URI, client address, CRS messages, rule IDs, and status metadata.
- Clean-checkout Compose tests clear runtime `env_file` declarations with
  test-only overrides and supply isolated SQLite/test credentials through the
  subprocess environment. The real runtime Compose files still require `.env`.
- GitHub Actions for implementation head `6cfe67b` passed backend, postgres,
  frontend, auth-e2e, and secret-scan. Earlier red runs are retained in
  `docs/project-ops/STATUS.md` with their corrected root causes.
- A real ModelService startup smoke after the Transformers `5.5.0` upgrade
  loaded the configured staged DistilBERT artifact and produced the expected
  `DistilBertForSequenceClassification` service; no unrelated initialization
  error was observed. Model artifact/classifier-head repair remains out of
  scope.

## Existing WAF Paths

| Path | Current services | Published boundary | Current network | Current verification |
|---|---|---|---|---|
| Technical WAF | `modsecurity`, `bridge`, `backend` | `0.0.0.0:8088 -> modsecurity:8080`; backend is exposed only inside Compose | Compose `default` | `unverified` |
| Realistic demo target | `demo-target-modsecurity`, `demo-target-bridge`, `demo-portal`, `backend` | `0.0.0.0:8089 -> demo-target-modsecurity:8080`; portal and backend are internal-only | Compose `default` | `unverified` |
| Target-only Cloudflare prerequisite | `cloudflared`, `demo-target-modsecurity`, `demo-target-bridge`, `demo-portal`, `backend` | No host port for `demo-target-modsecurity`; ingress is only `cloudflared` | Dedicated internal WAF ingress plus egress; WAF retains private application network | `unverified` until manual proof |

At baseline the base WAF pair had no profile. The implementation now puts both
services behind `technical-waf`, so the demo-target merge no longer includes
the technical pair or port `8088`.

Both bridges read separate host-mounted JSONL audit logs and submit to
`POST /api/internal/waf-events` with `WAF_INGEST_API_KEY`. Transaction lookup
continues to require `API_SECRET_KEY`.

## CRS Real-IP Capability

The locally resolved image is `owasp/modsecurity-crs:nginx-alpine` at digest
`sha256:0385a81159d5112c113eeeed01c3f6cf05113891b02addc23abeab180934911e`.
Inspection of that image proved its NGINX build includes `ngx_http_realip_module`
and its generated template accepts the real-IP environment variables. The
initial diagnostic also proved that the image placed those directives inside
the generated `location` include, where the running request remained at the
proxy address. The controlled fix uses narrowly mounted templates instead:

- `config/modsecurity/source-correlation-proxy-backend.conf.template` keeps
  proxy forwarding but contains no real-IP directives;
- `config/modsecurity/source-correlation-realip.conf.template` emits the
  directives at HTTP context; and
- the controlled values are exactly:
  `set_real_ip_from 172.30.10.2/32`,
  `real_ip_header CF-Connecting-IP`, and `real_ip_recursive off`.

The pinned image is:
`owasp/modsecurity-crs@sha256:0385a81159d5112c113eeeed01c3f6cf05113891b02addc23abeab180934911e`.
The inspected components are NGINX `1.28.2`, ModSecurity `3.0.14`,
ModSecurity-nginx connector `1.0.4`, and CRS `3.3.8`. The image's generated
template also supports:

- comma-separated `SET_REAL_IP_FROM`, expanded into `set_real_ip_from` lines;
- `REAL_IP_HEADER`; and
- `REAL_IP_RECURSIVE`.

The hosted override requires the operator to supply the observed narrow
`HOSTED_WAF_TRUSTED_PEER`; it deliberately has no guessed default. The value is
persisted in the ignored root `.env` and loaded by
`scripts/start_hosted_target.ps1`, which rejects missing or broad peers and
requires `WAF_SOURCE_VERIFICATION_MODE=unverified`. Neither topology trusts
`0.0.0.0/0` or all RFC1918 space.

The diagnostic before the template fix was:

```text
header CF-Connecting-IP=172.30.10.4
$remote_addr=172.30.10.2
$realip_remote_addr=172.30.10.2
transaction.client_ip=172.30.10.2
```

After the fix, the same request was:

```text
header CF-Connecting-IP=172.30.10.4
$remote_addr=172.30.10.4
$realip_remote_addr=172.30.10.2
transaction.client_ip=172.30.10.4
```

## Cloudflare Evidence Gate

| Required fact | Evidence | Status |
|---|---|---|
| Tunnel placement | One host `cloudflared` process was observed; no `cloudflare/cloudflared` container was present. Process arguments and tunnel configuration were not inspected because they may contain credentials. | Partial: host-managed process observed |
| Immediate peer/network seen by ModSecurity | Operator-provided hosted observation is `172.18.0.1`; the value is deployment-specific and must be rechecked after topology changes. | Partial |
| Narrow `set_real_ip_from` value | Hosted overlay renders the persisted `HOSTED_WAF_TRUSTED_PEER` through the checked-in launcher; current local value is `172.18.0.1/32`. | Partial |
| Cloudflare Workers in the request path | No operator-managed Cloudflare configuration is stored in the repository. | Unknown |
| Pseudo IPv4 mode | No operator-managed Cloudflare configuration is stored in the repository. | Unknown |
| Direct-origin isolation | Not proved by repository configuration or an external origin-bypass test. | Unknown |
| Restored source in ModSecurity | Operator home/mobile evidence showed each known public egress source matching the ModSecurity, bridge, FastAPI, PostgreSQL, and dashboard records. | Passed: operator evidence |
| Bridge and database correlation | The same hosted transaction path was correlated through bridge logs, FastAPI lookup, PostgreSQL, and dashboard evidence. | Passed: operator evidence |
| New audit-log credential leakage | Fresh hosted audit output was checked for Authorization, Cookie, and Access JWT material. | Passed |

These remaining unknowns do not block the frozen PR1 code, but they prohibit
enabling hosted `cloudflare_tunnel` verification. Hosted mode must remain
`unverified` until the Pseudo IPv4 decision, Worker header behavior,
direct-origin isolation, and immediate tunnel-side peer are independently
confirmed.

## Target-only isolation prerequisite

`docker-compose.target-cloudflare.yml` is a separate target-specific overlay.
It pins `cloudflare/cloudflared:2026.7.1` to digest
`sha256:188bb03589a32affed3cf4d0590565ffe67b78866e6b5582574afab2b705bafe`,
uses the read-only external secret `CLOUDFLARED_TARGET_TOKEN_FILE`, and runs
the metrics readiness endpoint on port `20241`. The WAF ingress network is
`internal: true`, uses `172.30.20.0/28`, and assigns `172.30.20.2` to
cloudflared. The only rendered `set_real_ip_from` value is `172.30.20.2/32`;
broad private ranges are not accepted. The bridge remains on the application
network and audit part `B` remains excluded.

The overlay is a preparation artifact. It does not change the live Dashboard,
the existing Windows tunnel for `app.cybertracesystems.com`, or the current
verification mode.

The live temporary-hostname proof subsequently established the following
deployment observations while the application remained `unverified`:

| Check | Result |
|---|---|
| Temporary hostname | `target-proof.cybertracesystems.com` |
| Tunnel / connector | `cybertrace-target-docker` / Healthy |
| Workers in path | None |
| Pseudo IPv4 | Off |
| Home visitor / ModSecurity client | `112.201.128.235` / `112.201.128.235` |
| Mobile visitor / ModSecurity client | `209.35.167.151` / `209.35.167.151` |
| Home/mobile separation | `112.201.128.235 != 209.35.167.151` |
| Direct origin | `127.0.0.1:8089` had no listener; HTTP status `000` |
| Cross-container forged header | `CF-Connecting-IP: 203.0.113.77` was not accepted; client remained `172.18.0.3` |

### Guarded verified-mode attempt (2026-07-28)

The temporary guarded proof was attempted through the authenticated
`target-proof.cybertracesystems.com` session with marker
`CF-VERIFIED-PROOF-1785213573826`.

The request reached the isolated WAF and produced the strongest transaction
correlation available:

- transaction ID: `178521357517.137695`
- request path: `/records/search`
- response: HTTP 403
- ModSecurity `transaction.client_ip`: `112.201.128.235`
- ModSecurity messages: 2 (`942100`, `949110`)
- persisted source IP: `112.201.128.235`
- persisted action/status: `BLOCKED` / `COMPLETED`

The verified-mode gate did **not** pass. The persisted row was
`DIRECT_REMOTE_ADDR` / `UNVERIFIED`, not
`CLOUDFLARE_CONNECTING_IP` / `VERIFIED`. The backend had the guarded
`cloudflare_tunnel` mode, but the bridge container retained its safe default
`WAF_SOURCE_PROVENANCE_MODE=direct_remote_addr`. This is an activation
configuration gap, not evidence authorizing Cloudflare verification.

The runtime was restored to `WAF_SOURCE_VERIFICATION_MODE=unverified` after
the attempt. Cloudflared, ModSecurity, and the backend were healthy; the WAF
host port remained absent; and PR7 enforcement remained disabled. No verified
transaction was recorded as proof, and PR #94 remains Draft.

### Corrected guarded verified-mode proof (2026-07-28)

After configuring the target bridge explicitly with
`WAF_SOURCE_PROVENANCE_MODE=cloudflare_connecting_ip` and rebuilding only the
bridge image, the guarded proof was repeated with marker
`CF-VERIFIED-PROOF-1785214180455`.

The proof passed:

- transaction ID: `178521418071.169644`
- request path: `/records/search`
- response: HTTP 403
- immediate tunnel peer: `172.30.20.2`
- NGINX effective visitor address: `112.201.128.235`
- ModSecurity `transaction.client_ip`: `112.201.128.235`
- persisted source IP: `112.201.128.235`
- ModSecurity messages: 2 (`942100`, `949110`)
- bridge delivery: HTTP 200; `cf_connecting_ip_matches_client_ip=true`
- persisted provenance/status: `CLOUDFLARE_CONNECTING_IP` / `VERIFIED`
- persisted action/status: `BLOCKED` / `COMPLETED`
- ingest source: `modsec_audit_bridge`

The equality requirement held:

```text
persisted source_ip
== ModSecurity transaction.client_ip
== NGINX effective remote_addr
== Cloudflare visitor identity
== 112.201.128.235
```

The safe runtime was restored immediately afterward: backend verification is
`unverified`, bridge provenance is `direct_remote_addr`, cloudflared and
ModSecurity are healthy, the direct origin returned HTTP `000`, the WAF host
port is absent, and PR7 enforcement remains disabled.

The persisted rows for the observed transactions were:

| Transaction | Source IP | Provenance | Verification | Ingest source | Path | Action / result |
|---|---|---|---|---|---|---|
| `178521095080.454926` | `112.201.128.235` | `DIRECT_REMOTE_ADDR` | `UNVERIFIED` | `modsec_audit_bridge` | `/records/search` | `BLOCKED` / `SQL Injection` |
| `178521099065.289049` | `172.18.0.3` | `DIRECT_REMOTE_ADDR` | `UNVERIFIED` | `modsec_audit_bridge` | `/records/search` | `BLOCKED` / `SQL Injection` |
| `178521193186.007519` | `209.35.167.151` | `DIRECT_REMOTE_ADDR` | `UNVERIFIED` | `modsec_audit_bridge` | `/records/search` | `BLOCKED` / `SQL Injection` |

These rows satisfy the present correlation requirement:

```text
persisted source_ip == ModSecurity transaction.client_ip
```

They do not authorize verified mode by themselves.

The source-verification correction is server-controlled: the authenticated
internal route accepts trusted Cloudflare provenance only when the bridge marks
an event as ModSecurity audit evidence, the payload's canonical source and
Cloudflare match are valid, and the configured mode is explicitly
`cloudflare_tunnel`. A generic internal payload cannot self-assign trusted
provenance or `VERIFIED`; no new database enum value or trusted boolean was
added. See
`docs/project-ops/CLOUDFLARE_TARGET_INGRESS_ISOLATION_RUNBOOK.md` for the
manual proof and rollback.

## Final Hosted Source-Correlation Evidence

The operator completed the hosted packet-path proof from two independent
networks. Home Wi-Fi and mobile data produced different public egress sources,
and each source remained consistent through ModSecurity, the bridge, FastAPI,
PostgreSQL, and the dashboard. A direct forged `CF-Connecting-IP` and
`X-Forwarded-For` request did not replace the actual direct source or produce
`VERIFIED`. The fresh audit-log review found no authentication, cookie, or
Cloudflare Access credential leakage. Hosted restart/recreate also preserved
the narrow real-IP configuration and removed the stale technical WAF pair.

These results prove hosted source correlation, not hosted authorization trust.
The four Cloudflare/origin checks in the evidence gate remain required before
changing the mode from `unverified`.

## Hosted Replacement Strategy

Because Compose `5.1.4` supports `!override`, the hosted file replaces the
demo-target port list with exactly:

```yaml
ports: !override
  - "127.0.0.1:8089:8080"
```

The hosted resolved service set contains only `backend`, `frontend`,
`demo-portal`, `demo-target-modsecurity`, and `demo-target-bridge`. It does not
contain the technical `modsecurity` or `bridge`, does not publish `8088`, and
contains exactly one loopback `8089` mapping.

## Local Controlled Proof

**Result: Passed locally on 2026-07-17.** The isolated stack was recreated with
fresh disposable audit files. All three SQLi requests returned HTTP 403 and the
bridge posted each event with status 200. The diagnostic access log, ModSecurity
transaction, bridge payload, and backend lookup agreed:

| Request | NGINX original peer | Restored / persisted source | Provenance | Status |
|---|---|---|---|---|
| Client A via trusted proxy | `172.30.10.2` | `172.30.10.4` | `DIRECT_REMOTE_ADDR` | `UNVERIFIED` |
| Client B via trusted proxy | `172.30.10.2` | `172.30.10.5` | `DIRECT_REMOTE_ADDR` | `UNVERIFIED` |
| Direct client with forged headers | `172.30.11.4` | `172.30.11.4` | `DIRECT_REMOTE_ADDR` | `UNVERIFIED` |

The final observed transaction IDs were `178427404768.801613`,
`178427404739.083371`, and `178427404733.523349`. The no-`B` audit
configuration still preserved method,
URI/query, CRS score/rules, source, provenance, and deterministic fingerprint;
the new raw audit file contained no `Authorization`, `Cookie`, or
`CF-Access-Jwt-Assertion` header names.

This is local Docker evidence only. It is not hosted Cloudflare proof and does
not authorize enabling `cloudflare_tunnel` verification.

`source_ip` identifies the observed network egress address, not a guaranteed
person or device. Shared home NAT, carrier-grade NAT, VPNs, and other egress
concentrators can legitimately make multiple visitors share one public address.

## Stop Conditions

- Do not enable `VERIFIED` hosted mode from unit, integration, migration, or
  Docker-only evidence.
- If the immediate peer/network, CRS real-IP behavior, Workers, Pseudo IPv4, or
  direct-origin isolation remains unknown, keep mode `unverified` and record
  hosted proof as `Partial` or `Not Run`.
- If the rendered Compose topology merges an extra port or WAF pair, do not
  deploy it as a verifying topology.
