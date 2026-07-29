# Tests — End-to-End

Full pipeline tests simulating the complete enforcement flow:
CRS detection → log bridge → ML triage → confidence-gated mitigation.

## PR7 backend-to-WAF proof

The opt-in `test_pr7_backend_waf.py` starts disposable PostgreSQL, backend, and
pinned PR7 WAF containers; applies migrations; seeds one eligible CRITICAL WAF
recommendation through the repository; verifies the authenticated snapshot and
live `403`/`204` behavior; checks PR7 audit identity; revokes the recommendation;
and confirms empty-state behavior after restart. It generates a per-run local
sync key and removes its containers, network, and volumes in teardown.

Run it from the repository root:

```powershell
$env:PR7_RUN_BACKEND_WAF_E2E = "1"
.venv\Scripts\python.exe -m pytest -s -q --tb=short tests/e2e/test_pr7_backend_waf.py
```

The test is skipped unless `PR7_RUN_BACKEND_WAF_E2E` is set. It uses only local
Docker resources and disposable credentials; it does not use Supabase or
hosted/production configuration.
