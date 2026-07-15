# ModSecurity Configuration

This directory contains ModSecurity engine configuration files.

## Purpose
- Primary WAF detection engine configuration
- ModSecurity audit log format and output settings
- Engine-level directives (SecRuleEngine, SecAuditLog, etc.)

Audit-log evidence handling, sensitive-data rules, local retention, and the rotation target are documented in `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`; automatic rotation is not implemented here.

## Current Repo State
- Root `docker-compose.yml` keeps the technical `8088` WAF/bridge pair behind the opt-in `technical-waf` profile.
- `docker-compose.demo-target.yml` contains the realistic `8089` target pair.
- `docker-compose.hosted-target.yml` replaces the `8089` binding with one loopback-only binding and requires an observed narrow `HOSTED_WAF_TRUSTED_PEER`; it does not guess that peer.
- `docker-compose.source-correlation-test.yml` is an isolated, no-host-port topology for controlled source-correlation proof.
- `source-correlation-proxy.conf` is used only by that controlled topology. It represents the one trusted proxy and overwrites `CF-Connecting-IP` with its direct client's address.

## Architectural Role
Target role: first detection layer in the CRS-first hybrid enforcement hierarchy.

Current repo state:
- Root `docker-compose.yml` includes a ModSecurity CRS container that proxies to the backend.
- The verified WAF proof path is `localhost:8088 -> ModSecurity/OWASP CRS -> backend`.
- The optional demo-target proof path is `localhost:8089 -> ModSecurity/OWASP CRS -> demo-portal:3010`.
- The dashboard browser path remains `Browser -> Next.js -> FastAPI`; this proof is not a production-grade WAF deployment claim.
- The bridge input path for Compose is `logs/modsecurity/modsec_audit.jsonl` on the host, mounted as `/var/log/modsecurity/modsec_audit.jsonl` in the ModSecurity and bridge containers.

Do not document ModSecurity as processing all incoming production requests. The historical verified local proof remains `localhost:8088`, but starting that pair now requires:

```powershell
docker compose --profile technical-waf up --build
```

The controlled topology has no ordinary host-browser route and trusts only `172.30.10.2/32` for `CF-Connecting-IP` restoration. Its separate untrusted network reaches ModSecurity directly, so a forged Cloudflare header from that network is ignored by the CRS image's real-IP mechanism.

## Audit Log Decisions

- Format: JSON audit log entries, one JSON object per appended line for bridge ingestion.
- Type: Serial audit log for the PD2 demo unless a checked-in ModSecurity config later proves a different live setup.
- Compose path: `MODSEC_AUDIT_LOG=/var/log/modsecurity/modsec_audit.jsonl`, mounted from host `logs/modsecurity/`.
- Bridge command: `scripts/waf_audit_bridge.py --input /var/log/modsecurity/modsec_audit.jsonl --follow --endpoint http://backend:8000/api/internal/waf-events`.
- Policy reference: `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md`

Required fields after bridge normalization:
- `transaction_id`
- `timestamp`
- `source_ip`
- `request_method`
- `request_path`
- `query_string`
- `request_headers`
- `crs_score`
- `crs_rule_ids`
- `matched_rule_messages`
- `matched_rule_tags`

Verified proof result:
- SQLi probe `/api/health?id=17%27%20OR%2017%3D17--` returned HTTP 403 through `localhost:8088`.
- ModSecurity audit log preserved transaction `17821639659.909603`, source IP `172.21.0.1`, and URL-encoded query string.
- Bridge posted to FastAPI with `status=200`.
- Docker-internal lookup returned `found=true`, `prediction=SQL Injection`, `action_taken=BLOCKED`, `crs_score=5`, and CRS rules `942100`, `949110`.

Optional demo-target proof:
- Compose override: `docker-compose.demo-target.yml`
- WAF path: `localhost:8089`
- Upstream: `host.docker.internal:3010`
- Nginx template: official `owasp/modsecurity-crs:nginx-alpine` generated config; `config/modsecurity/demo-target-nginx.conf` is not mounted
- Observed report path: `reports/modsecurity-live-proof/demo-target-crs-proof.md`
- Template path: `reports/modsecurity-live-proof/demo-target-crs-proof.md.template`

Sensitive data handling:
- The bridge redacts sensitive headers such as `Authorization`, `Cookie`, `Set-Cookie`, and header names containing `token`, `secret`, `key`, or `credential`.
- Request body content is truncated before ingest. Do not use full raw bodies as an operator-facing source of truth.

Rotation and retention:
- Keep audit logs append-only for PD2 evidence.
- Automatic rotation is not implemented.
- Production retention is not implemented.
- See `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md` for the current policy.
