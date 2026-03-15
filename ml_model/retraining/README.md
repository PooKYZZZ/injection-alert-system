# ML Retraining Pipeline

This directory contains the 20-day scheduled retraining pipeline.

## Purpose
- Automated retraining triggered on a 20-day cycle
- Ingests analyst-corrected feedback data from staging
- Champion/challenger validation gating before promotion
- Model rollback if validation fails

## Current Repo State
- This package currently contains only the package marker and documentation.
- The intended retraining flow is still design-level in this repo; no committed retraining entrypoint or scheduler is present here yet.

## Architectural Role
Closes the feedback loop:
  Analyst corrections → data/staging/ → retrain → validate → ml_model/model_registry/

No model is promoted without passing validation gating.
Rollback to the previous model version is always available.
