# Trusted Source Correlation Evidence

**Status:** Implemented and automatically validated; local packet-path proof Not Run
**Observed:** 2026-07-15

This document separates repository and local-runtime evidence from hosted
Cloudflare facts that have not yet been proved. Until every hosted prerequisite
is verified, `WAF_SOURCE_VERIFICATION_MODE` remains `unverified`.

## Baseline

- Git base: `master` at `ac86422` (`feat: implement CyberTrace V6.1 account security`).
- Feature branch: `feat/trusted-source-correlation`.
- Alembic: exactly one head, `20260712_000020`.
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
  `691 passed, 31 skipped`.
- Compose rendering proves the default stack excludes the technical pair;
  `--profile technical-waf` restores `modsecurity` and `bridge` with `8088`.
- The hosted merge resolves only `backend`, `frontend`, `demo-portal`,
  `demo-target-modsecurity`, and `demo-target-bridge`, with exactly one
  `127.0.0.1:8089:8080` binding and no `8088`.
- The controlled merge has no published ports, uses
  `controlled_private_network`, and trusts only proxy peer `172.30.10.2/32`.
- Its backend is forced to an isolated SQLite file and process-only test
  credentials, so it cannot inherit the developer `.env` database URL.

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
Inspection of that image proved its NGINX template supports:

- comma-separated `SET_REAL_IP_FROM`, expanded into `set_real_ip_from` lines;
- `REAL_IP_HEADER`; and
- `REAL_IP_RECURSIVE`.

The controlled topology sets `REAL_IP_HEADER=CF-Connecting-IP` and trusts only
`172.30.10.2/32`. The hosted override requires the operator to supply the
observed narrow `HOSTED_WAF_TRUSTED_PEER`; it deliberately has no guessed
default. Neither topology trusts `0.0.0.0/0` or all RFC1918 space.

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

**Result: Not Run.** The opt-in stack build exceeded the five-minute local
timeout before any containers were created. The orphaned build processes were
identified by exact command line and stopped; no request, transaction ID,
persisted source row, or SQLi response was produced. Therefore the following
remain unproved at runtime in this session:

- distinct persisted source addresses for controlled clients A and B;
- rejection of a forged Cloudflare header from the direct untrusted network;
- correlated transaction IDs and persisted provenance/status; and
- SQLi HTTP 403 through the controlled proxy path.

Automated Compose rendering is evidence of topology configuration only, not of
packet-path behavior.

## Stop Conditions

- Do not enable `VERIFIED` hosted mode from unit, integration, migration, or
  Docker-only evidence.
- If the immediate peer/network, CRS real-IP behavior, Workers, Pseudo IPv4, or
  direct-origin isolation remains unknown, keep mode `unverified` and record
  hosted proof as `Partial` or `Not Run`.
- If the rendered Compose topology merges an extra port or WAF pair, do not
  deploy it as a verifying topology.
