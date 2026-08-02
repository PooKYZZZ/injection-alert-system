# ML Retraining Pipeline

This directory documents the planned retraining pipeline. It does not currently contain a runnable scheduled retraining implementation; the reusable benchmark training entrypoint now lives under `ml_model/training/`.

## Target Purpose
- Manual or scheduled retraining trigger
- Analyst-labeled data export
- Dataset validation before training
- Dry-run/smoke mode for orchestration checks
- Real training mode only when explicitly run
- Evaluation report and candidate artifact output
- Manual approval before promotion
- Rollback path if promotion fails

## Current Repo State
- This package currently contains only the package marker and documentation.
- The daily retraining flow and scheduler are still design-level in this repo. `ml_model/training/train.py` is a script-first confirmatory benchmark entrypoint, not a complete labeled-sample retraining service.
- Do not claim blind auto-promotion, production retraining automation, or a working 20-day scheduler from this directory.

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

Reviewer identity is derived from the authenticated server session. New
inference rows persist the exact sanitized model-input text, its
`model_input_hash`, and `preprocessing_version`; WAF query strings and
sanitized bodies use the same canonical input before inference. Historical
rows with missing text/provenance remain readable but are not eligible for
approved training. The exporter is still not implemented, so automated or
source-equivalent training data remains `Planned`.

This workflow does not provide a scheduler, daily retraining operation, blind
promotion, automatic rollback, or production model-registry mutation. Any
training and promotion remains an explicit, manually reviewed operation.
