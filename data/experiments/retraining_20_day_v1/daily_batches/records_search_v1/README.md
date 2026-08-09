# Records-search controlled simulation batches

This directory contains the prepared, route-specific input for the controlled
offline retraining simulation. It is not a production export and it is not
evidence of twenty days of reviewed production traffic.

- Batch set: `records-search-v1`
- Target method and route: `GET /records/search`
- Days: `day_01.jsonl` through `day_20.jsonl`
- Rows: 2 per day, 40 total
- Labels: 20 `Normal` controls and 20 attack controls
- Attack classes: SQL Injection, Code Injection, and Other Attacks
- Preprocessing: `http-preprocessor-v1`
- Status: `curated_simulation_fixture`
- Synthetic marker: `is_synthetic=true`

Every row has a SHA-256 `model_input_hash`, a batch-day value, and a stable
fixture provenance ID. The values are distinct from the locked `golden-v2`
cases and were checked against the available historical dataset with the
repository contamination index: no exact or near-duplicate overlaps were
found at the configured `0.90` threshold.

The normal validator intentionally rejects these rows in ordinary training
mode. The explicit `--controlled-simulation` flag is required to use them, and
the resulting report must be described as controlled-simulation evidence only.
For a production-like experiment using reviewed samples, provide a separate
non-synthetic export with `review_status=approved_for_training` and omit that
flag.
