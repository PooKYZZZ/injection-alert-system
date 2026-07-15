# Trusted Source Correlation Evidence

**Status:** Planned implementation; topology inputs recorded
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

## Existing WAF Paths

| Path | Current services | Published boundary | Current network | Current verification |
|---|---|---|---|---|
| Technical WAF | `modsecurity`, `bridge`, `backend` | `0.0.0.0:8088 -> modsecurity:8080`; backend is exposed only inside Compose | Compose `default` | `unverified` |
| Realistic demo target | `demo-target-modsecurity`, `demo-target-bridge`, `demo-portal`, `backend` | `0.0.0.0:8089 -> demo-target-modsecurity:8080`; portal and backend are internal-only | Compose `default` | `unverified` |

The current base file has no profile on `modsecurity` or `bridge`. Therefore,
resolving the base and demo-target files with `--profile demo-target` currently
includes both WAF/bridge pairs and both host ports, `8088` and `8089`. This is
the topology Phase E must isolate.

Both bridges read separate host-mounted JSONL audit logs and submit to
`POST /api/internal/waf-events`. At this baseline they still inherit
`API_SECRET_KEY` from `.env`; the atomic credential phase will move submission
to `WAF_INGEST_API_KEY` while lookup remains on `API_SECRET_KEY`.

## CRS Real-IP Capability

The locally resolved image is `owasp/modsecurity-crs:nginx-alpine` at digest
`sha256:0385a81159d5112c113eeeed01c3f6cf05113891b02addc23abeab180934911e`.
Inspection of that image proved its NGINX template supports:

- comma-separated `SET_REAL_IP_FROM`, expanded into `set_real_ip_from` lines;
- `REAL_IP_HEADER`; and
- `REAL_IP_RECURSIVE`.

Neither current Compose WAF service sets these variables. The image defaults
observed locally are `SET_REAL_IP_FROM=127.0.0.1` and
`REAL_IP_HEADER=X-REAL-IP`; those defaults do not establish the planned
Cloudflare source contract. Phase E must supply a narrow, topology-specific
peer or network and must not trust `0.0.0.0/0` or all RFC1918 space.

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

Because Compose `5.1.4` supports `!override`, the hosted file will replace the
demo-target port list with exactly:

```yaml
ports: !override
  - "127.0.0.1:8089:8080"
```

The hosted resolved service set must contain only `backend`, `frontend`,
`demo-portal`, `demo-target-modsecurity`, and `demo-target-bridge`. It must not
contain the technical `modsecurity` or `bridge`, must not publish `8088`, and
must contain exactly one loopback `8089` mapping.

## Stop Conditions

- Do not enable `VERIFIED` hosted mode from unit, integration, migration, or
  Docker-only evidence.
- If the immediate peer/network, CRS real-IP behavior, Workers, Pseudo IPv4, or
  direct-origin isolation remains unknown, keep mode `unverified` and record
  hosted proof as `Partial` or `Not Run`.
- If the rendered Compose topology merges an extra port or WAF pair, do not
  deploy it as a verifying topology.
