# ModSecurity Configuration

This directory contains ModSecurity engine configuration files.

## Purpose
- Primary WAF detection engine configuration
- ModSecurity audit log format and output settings
- Engine-level directives (SecRuleEngine, SecAuditLog, etc.)

## Current Repo State
- This directory is currently a documented placeholder for future custom ModSecurity configuration.
- Runnable custom ModSecurity config files are not checked into this directory yet.
- Root `docker-compose.yml` configures the CRS container to write a host-mounted JSON audit log for the PD2 demo bridge path.
- Local WAF proof is verified through `localhost:8088`; see `reports/modsecurity-live-proof/e2e-proof.md`.

## Architectural Role
Target role: first detection layer in the CRS-first hybrid enforcement hierarchy.

Current repo state:
- Root `docker-compose.yml` includes a ModSecurity CRS container that proxies to the backend.
- Runnable ModSecurity config files are not checked into this directory yet.
- The verified WAF proof path is `localhost:8088 -> ModSecurity/OWASP CRS -> backend`.
- The dashboard browser path remains `Browser -> Next.js -> FastAPI`; this proof is not a production-grade WAF deployment claim.
- The bridge input path for Compose is `logs/modsecurity/modsec_audit.jsonl` on the host, mounted as `/var/log/modsecurity/modsec_audit.jsonl` in the ModSecurity and bridge containers.

Do not document ModSecurity as processing all incoming production requests. Document the verified local proof path as `localhost:8088`.

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

Sensitive data handling:
- The bridge redacts sensitive headers such as `Authorization`, `Cookie`, `Set-Cookie`, and header names containing `token`, `secret`, `key`, or `credential`.
- Request body content is truncated before ingest. Do not use full raw bodies as an operator-facing source of truth.

Rotation and retention:
- Keep audit logs append-only for PD2 evidence.
- Automatic rotation is not implemented.
- Production retention is not implemented.
- See `docs/project-ops/MODSECURITY_AUDIT_LOG_POLICY.md` for the current policy.
