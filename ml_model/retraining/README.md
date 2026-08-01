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
  Analyst corrections → data/staging/ → retrain → validate → ml_model/model_registry/

Planned safe flow:

```text
Analyst corrections -> labeled export -> dataset validation -> dry-run or real training
-> evaluation report -> candidate artifact -> manual approval -> promotion -> rollback if needed
```

Existing promotion/rollback tooling lives under `ml_model/export/`; it is not the same thing as a complete retraining pipeline.
