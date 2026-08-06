# ML Retraining Pipeline

This directory contains a controlled offline 20-day cumulative retraining
simulation. It is not a production scheduler, queue, online-learning service,
or automatic promotion path. The reusable training entrypoint remains under
`ml_model/training/`.

## Target Purpose
- Manual explicitly invoked retraining trigger
- Analyst-labeled data export
- Dataset validation before training
- Dry-run/smoke mode for orchestration checks
- Real training mode only when explicitly run
- Evaluation report and candidate artifact output
- Manual approval before promotion
- Rollback path if promotion fails

## Implemented controlled experiment

- `experiment_contract.py` loads the immutable v1 TOML contract.
- `validate_batch.py` rejects unapproved, unprovenanced, duplicate, conflicting,
  unknown-label, predicted-label, preprocessing-mismatched, and golden-overlap
  samples while preserving privacy-safe quarantine evidence. It also validates
  model-input hashes and batch-day provenance. Real approved rows require
  reviewer identity and review time; checked-in synthetic rows are explicitly
  simulation fixtures and are rejected unless the smoke/test override is set.
- `snapshots.py` creates versioned cumulative train snapshots and preserves the
  historical validation/test splits, including the metadata and checksum
  contract required by the training preflight. It builds one reusable index
  over train, validation, and test per simulation, checks exact normalized
  hashes before safe length-bucketed fuzzy candidates, and checks only new
  daily samples against historical and accepted daily records. It rejects
  exact, near-duplicate, duplicate, and conflicting-label contamination and
  records row counts, candidate comparisons, exact/fuzzy matches, rejected
  IDs, and hashes for data, metadata, checksums, historical inputs, and the
  canonical snapshot manifest.
- `drift.py` records deterministic per-batch request, label, source,
  confidence, query-parameter, and validation-error dimensions.
- `prediction_artifacts.py` writes deterministic, hash-checked baseline and
  candidate per-example artifacts from the locked golden controls. Stable
  sample IDs and dataset/golden/split provenance are required for joining.
- `statistical_evidence.py` records paired McNemar exact results, absolute
  accuracy difference, paired error counts, and seeded bootstrap confidence
  intervals only when those artifacts are valid and aligned. Missing evidence
  is `NOT_RUN`; malformed or mismatched evidence is `INVALID`; no p-value is
  promoted to a significance claim.
- `integrity.py` blocks a candidate unless its serving manifest, exact-run
  contract, dataset hash, pinned model/tokenizer identity, policy mappings,
  selected checkpoint, and reload/hash identity remain unchanged.
- `simulate_20_day.py` calls the maintained training/evaluation/export seams,
  performs isolated candidate packaging/reload/backend checks, applies frozen
  gates, and records `ACCEPTED`, `REJECTED`, or `NOT_RUN` per day. A requested
  final day includes every preceding cumulative day; partial runs are
  `PARTIAL`, not complete `SUCCESS`.
- `run_baseline.py` evaluates a specifically selected current artifact against
  the locked golden set without silently discovering or modifying staging.

The `--smoke` mode uses tiny synthetic data and injected adapters to prove
orchestration startup and failure safety. It reports `SMOKE_SUCCESS`,
`real_training_status=NOT_RUN`, `model_quality_conclusion=NOT_PERMITTED`, and
`baseline_status=SMOKE_SYNTHETIC`; its statistical evidence is `NOT_RUN` and
it is not a model-quality or thesis result. The synthetic fixture is not
production data.

The real baseline, corrected one-seed run, three-seed confirmation, and full
20-day native simulation remain `REQUIRES_LAPTOP` unless their artifacts and
reports are freshly generated and inspected.

## Validation commands and evidence boundaries

From the repository root, run the complete synthetic smoke with all days:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.simulate_20_day `
  --config ml_model/configs/retraining_20_day_v1.toml `
  --output-dir ml_model/results/retraining_20_day_v1/smoke `
  --smoke `
  --days 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20
```

For native execution, first create a baseline artifact and its paired
prediction artifact, then run the simulator with reviewed non-synthetic daily
batches:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.run_baseline `
  --config ml_model/configs/retraining_20_day_v1.toml `
  --artifact-dir ml_model/model_registry/staging/<frozen-run> `
  --output ml_model/results/retraining_20_day_v1/baseline.json

.venv\Scripts\python.exe -m ml_model.retraining.simulate_20_day `
  --config ml_model/configs/retraining_20_day_v1.toml `
  --historical-data-dir data/processed/v3_907k_cleaned `
  --daily-batch-dir data/experiments/retraining_20_day_v1/daily_batches `
  --output-dir ml_model/results/retraining_20_day_v1/native `
  --baseline ml_model/results/retraining_20_day_v1/baseline.json `
  --days 1
```

Then, only after the one-seed and three-seed prerequisites pass, run days 1
through 20 using the same baseline, dataset version, reviewed batches, and
locked golden set. Real training still must be performed on the laptop. No
smoke run, aggregate metric, or present p-value is evidence that the real
model improved.

## Architectural Role
Closes the feedback loop:
  Analyst corrections → reviewed-sample export → data/staging/ → retrain → validate → ml_model/model_registry/

Planned safe flow:

```text
Analyst corrections -> labeled export -> dataset validation -> dry-run or real training
-> evaluation report -> candidate artifact -> manual approval -> promotion -> rollback if needed
```

Existing promotion/rollback tooling lives under `ml_model/export/`; it is not the same thing as a complete retraining pipeline.

## Verified label review input

The web application now records immutable, per-alert review revisions in
`traffic_label_reviews`. The canonical verified-label classes are `SQL
Injection`, `Code Injection`, `Other Attacks`, and `Normal`; this vocabulary is
separate from triage transport status and confidence tier. A future exporter
must select only the latest review with `approval_state=approved_for_training`.
Reviews marked `excluded_from_training` must remain excluded, and superseded
history must not be exported as a second sample.

Reviewer identity is derived from the authenticated server session. New v2
inference rows persist the exact sanitized model-input text, its
`model_input_hash`, and `preprocessing_version`; WAF query strings and
sanitized bodies use the same canonical input before inference. Sensitive
fields are redacted while safe injection indicators are retained as explicit
tokens for classification. The supported legacy v1 artifact keeps its exact
inference behavior but persists only the model-input hash, so those rows are
not eligible for approved training until a redacted v2 artifact is deployed.
Historical rows with missing text/provenance remain readable but are not
eligible for approved training. The exporter is still not implemented, so
automated or source-equivalent training data remains `Planned`.

This workflow does not provide a scheduler, daily production retraining
operation, blind promotion, automatic rollback, or production model-registry
mutation. Any training and promotion remains an explicit, manually reviewed
operation. See `docs/project-ops/LAPTOP_TRAINING_HANDOFF.md` for the exact
operator sequence.
