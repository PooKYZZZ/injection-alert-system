# ML Retraining Pipeline

This directory contains the 20-day scheduled retraining pipeline.

## Purpose
- Automated retraining triggered on a 20-day cycle
- Ingests analyst-corrected feedback data from staging
- Champion/challenger validation gating before promotion
- Model rollback if validation fails

## Expected Contents
- `retrain.py` — Retraining entry point
- `validate.py` — Champion vs challenger model comparison
- `schedule.py` — Cron/timer-based scheduling logic
- `promote.py` — Safe model promotion to registry

## Architectural Role
Closes the feedback loop:
  Analyst corrections → data/staging/ → retrain → validate → model_registry/

No model is promoted without passing validation gating.
Rollback to the previous model version is always available.
