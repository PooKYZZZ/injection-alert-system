# Frontend Dashboard

This directory contains the human-in-the-loop review dashboard.

## Purpose
- Alert visualization and triage interface
- Analyst feedback submission for retraining loop
- Confidence distribution and audit trail display
- Model version and system health monitoring

## Architectural Role
SOC-style operational interface.
Connects to FastAPI backend via REST API.
Analyst corrections flow to `data/staging/` for the retraining pipeline.
