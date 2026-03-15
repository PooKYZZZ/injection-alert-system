# Frontend Dashboard

This directory contains the human-in-the-loop review dashboard.

## Purpose
- Alert visualization and triage interface
- Analyst feedback submission for retraining loop
- Confidence distribution and audit trail display
- Model version and system health monitoring

## Architectural Role
SOC-style operational interface.
Uses the BFF pattern:
  Browser -> Next.js route handler -> FastAPI
Dashboard pages are session-protected, and the implemented BFF handlers also require a valid Auth.js session.
Analyst feedback is stored through backend routes; any downstream retraining flow remains separate from the current dashboard wiring.
