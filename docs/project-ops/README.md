# Project Ops

This folder contains operator-focused working documents that support implementation sessions and verification handoff.

## Files

- `STATUS.md`
  - current implementation status and known repo gaps
- `LIVING_CHECKLIST.md`
  - ongoing task checklist and handoff material
- `DEMO_TARGET_WAF_PROOF.md`
  - optional local portal-target WAF proof plan for `localhost:8089 -> host.docker.internal:3010`
- `../../reports/modsecurity-live-proof/e2e-proof.md`
  - checked-in local ModSecurity/OWASP CRS -> bridge -> FastAPI WAF ingest proof
- `MODSECURITY_AUDIT_LOG_POLICY.md`
  - local PD2 policy for ModSecurity JSONL audit logs, evidence fields, sensitive-data handling, retention, and rotation target
- `../client-requirements.md`
  - client-stated PD2 requirements that affect security, alerting, and confidence-tier planning
- `README.md`
  - explains the operator-doc subset itself

These files are operational notes, not the main user-facing documentation surface.
