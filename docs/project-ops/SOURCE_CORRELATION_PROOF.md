# Trusted Source Correlation Evidence

**Status:** Local repository and controlled packet-path checks passed; remote CI for
the current unpushed head is not verified; hosted verification Partial
**Observed:** 2026-07-17

This document separates repository and local-runtime evidence from hosted
Cloudflare facts that have not yet been proved. Until every hosted prerequisite
is verified, `WAF_SOURCE_VERIFICATION_MODE` remains `unverified`.

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
  `698 passed, 32 skipped`.
- The required focused source/integrity suite passed: `83 passed` with one
  PostgreSQL-only test skipped locally; the executable SQLite migration cycle
  passed.
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
- GitHub Actions run `29428801740` passed backend, postgres, frontend,
  auth-e2e, and secret-scan. Earlier red runs are retained in
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

The hosted override requires the operator to supply the
observed narrow `HOSTED_WAF_TRUSTED_PEER`; it deliberately has no guessed
default. Neither topology trusts `0.0.0.0/0` or all RFC1918 space.

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
| Immediate peer/network seen by ModSecurity | Not represented in the repository and not measured from a hosted request. | Unknown |
| Narrow `set_real_ip_from` value | Not configured in the current Compose files. | Planned |
| Cloudflare Workers in the request path | No operator-managed Cloudflare configuration is stored in the repository. | Unknown |
| Pseudo IPv4 mode | No operator-managed Cloudflare configuration is stored in the repository. | Unknown |
| Direct-origin isolation | Not proved by repository configuration or an external origin-bypass test. | Unknown |
| Restored source in ModSecurity | Existing local proofs record Docker-network source addresses, not a reviewed Cloudflare-restored source. | Not Found |

These unknowns do not block the code phases, but they prohibit enabling hosted
`cloudflare_tunnel` verification. Hosted mode must remain `unverified` until a
new request proves the narrow peer/network, Workers and Pseudo IPv4 decisions,
failed direct-origin access, restored ModSecurity source, bridge correlation,
and the persisted PostgreSQL row.

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
