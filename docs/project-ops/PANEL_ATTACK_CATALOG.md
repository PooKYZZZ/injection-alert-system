# Panel Attack Catalogue

Catalogue version: `panelist-local-v1`

This is a deterministic, local-only catalogue for panel demonstrations.
The expected label is ground truth only where the case says `approved_fixture`;
proposed variants require analyst review before acceptance.

Confidence is measured from the unchanged model output. A case ID or tag does
not force LOW, MEDIUM, HIGH, or CRITICAL confidence.

| Case | Family | Variant | Expected label | Ground truth | WAF expectation | Replay policy | Tags |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `N-001` | normal | `identity` | Normal | approved_fixture | ALLOW | offline_only | normal_control, high_confidence_candidate, false_positive_watch |
| `N-002` | normal | `identity` | Normal | approved_fixture | ALLOW | offline_only | normal_control, high_confidence_candidate, false_positive_watch |
| `N-003` | normal | `append_benign_query` | Normal | proposed_semantics_preserving | ALLOW | offline_only | metamorphic_candidate, review_required |
| `N-004` | normal | `lower_header_names` | Normal | proposed_semantics_preserving | ALLOW | offline_only | metamorphic_candidate, review_required |
| `N-005` | normal | `crlf` | Normal | proposed_semantics_preserving | ALLOW | offline_only | metamorphic_candidate, review_required |
| `N-006` | normal | `append_benign_query` | Normal | proposed_semantics_preserving | ALLOW | offline_only | boundary_candidate, review_required |
| `SQL-001` | sql_injection | `identity` | SQL Injection | approved_fixture | BLOCK_IF_CRS_MATCHES | offline_only | positive_control, high_confidence_candidate |
| `SQL-002` | sql_injection | `identity` | SQL Injection | approved_fixture | BLOCK_IF_CRS_MATCHES | offline_only | positive_control, high_confidence_candidate |
| `SQL-003` | sql_injection | `identity` | SQL Injection | approved_fixture | BLOCK_IF_CRS_MATCHES | offline_only | positive_control, high_confidence_candidate |
| `SQL-004` | sql_injection | `encoded_spaces` | SQL Injection | proposed_semantics_preserving | BLOCK_IF_CRS_MATCHES | offline_only | evasion_candidate, review_required |
| `SQL-005` | sql_injection | `query_case` | SQL Injection | proposed_semantics_preserving | BLOCK_IF_CRS_MATCHES | offline_only | evasion_candidate, review_required |
| `SQL-006` | sql_injection | `append_benign_query` | SQL Injection | proposed_semantics_preserving | BLOCK_IF_CRS_MATCHES | offline_only | input_surface_candidate, review_required |
| `SQL-007` | sql_injection | `lower_header_names` | SQL Injection | proposed_semantics_preserving | BLOCK_IF_CRS_MATCHES | offline_only | metamorphic_candidate, review_required |
| `SQL-008` | sql_injection | `crlf` | SQL Injection | proposed_semantics_preserving | BLOCK_IF_CRS_MATCHES | offline_only | metamorphic_candidate, review_required |
| `CODE-001` | code_injection | `identity` | Code Injection | approved_fixture | RECORD_ONLY | offline_only | positive_control, high_confidence_candidate |
| `CODE-002` | code_injection | `identity` | Code Injection | approved_fixture | RECORD_ONLY | offline_only | positive_control, high_confidence_candidate |
| `CODE-003` | code_injection | `identity` | Code Injection | approved_fixture | RECORD_ONLY | offline_only | positive_control, high_confidence_candidate |
| `CODE-004` | code_injection | `encoded_spaces` | Code Injection | proposed_semantics_preserving | RECORD_ONLY | offline_only | evasion_candidate, review_required |
| `CODE-005` | code_injection | `append_benign_query` | Code Injection | proposed_semantics_preserving | RECORD_ONLY | offline_only | input_surface_candidate, review_required |
| `CODE-006` | code_injection | `lower_header_names` | Code Injection | proposed_semantics_preserving | RECORD_ONLY | offline_only | metamorphic_candidate, review_required |
| `CODE-007` | code_injection | `crlf` | Code Injection | proposed_semantics_preserving | RECORD_ONLY | offline_only | metamorphic_candidate, review_required |
| `OTHER-001` | other_attacks | `identity` | Other Attacks | approved_fixture | RECORD_ONLY | offline_only | positive_control, high_confidence_candidate |
| `OTHER-002` | other_attacks | `identity` | Other Attacks | approved_fixture | RECORD_ONLY | offline_only | positive_control, high_confidence_candidate |
| `OTHER-003` | other_attacks | `identity` | Other Attacks | approved_fixture | RECORD_ONLY | offline_only | positive_control, high_confidence_candidate |
| `OTHER-004` | other_attacks | `crlf` | Other Attacks | proposed_semantics_preserving | RECORD_ONLY | offline_only | metamorphic_candidate, review_required |
| `OTHER-005` | other_attacks | `append_benign_query` | Other Attacks | proposed_semantics_preserving | RECORD_ONLY | offline_only | input_surface_candidate, review_required |
| `OTHER-006` | other_attacks | `crlf` | Other Attacks | proposed_semantics_preserving | RECORD_ONLY | offline_only | metamorphic_candidate, review_required |
| `OTHER-007` | other_attacks | `append_benign_query` | Other Attacks | proposed_semantics_preserving | RECORD_ONLY | offline_only | input_surface_candidate, review_required |

## Reproducible commands

From the repository root, after the backend container is running:

```powershell
docker exec injection-alert-system-backend-1 `
  python -m scripts.panel_attack_catalog `
  --output /tmp/panel-cases.jsonl --format jsonl

docker exec injection-alert-system-backend-1 `
  python -m scripts.attack_dataset_tester `
  --dataset /tmp/panel-cases.jsonl `
  --endpoint http://127.0.0.1:8000/api/predict `
  --include-normal `
  --limit 0 --seed 20260902 --pause-ms 100 `
  --max-rps 5 --max-runtime-seconds 120 --max-retries 0 `
  --run-id attack-mainpc-20260902-final `
  --environment local-docker-offline `
  --output-csv /tmp/panel-results.csv `
  --output-jsonl /tmp/panel-results.jsonl

New-Item -ItemType Directory -Force output\attack-tests | Out-Null
docker cp injection-alert-system-backend-1:/tmp/panel-cases.jsonl `
  output\attack-tests\panel-cases.jsonl
docker cp injection-alert-system-backend-1:/tmp/panel-results.csv `
  output\attack-tests\panel-results.csv
docker cp injection-alert-system-backend-1:/tmp/panel-results.jsonl `
  output\attack-tests\panel-results.jsonl
```

The tester uses the backend container's internal `/api/predict` route because
the backend port is intentionally not published on the host. Do not replace it
with a public hostname or an unbounded loop.
