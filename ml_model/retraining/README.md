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
  contract required by the training preflight. It rejects exact and
  near-duplicate historical contamination and records hashes for data,
  metadata, checksums, historical inputs, and the canonical snapshot manifest.
- `drift.py` records deterministic per-batch request, label, source,
  confidence, query-parameter, and validation-error dimensions.
- `statistical_evidence.py` records paired McNemar and bootstrap evidence only
  when aligned baseline and candidate predictions are supplied; otherwise it
  reports `NOT_RUN`.
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
orchestration startup and failure safety. It reports `SMOKE_SUCCESS` and is
not a model-quality result.

The real baseline, corrected one-seed run, three-seed confirmation, and full
20-day native simulation remain `REQUIRES_LAPTOP` unless their artifacts and
reports are freshly generated and inspected.

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
