# Backend Services

This directory contains business logic services decoupled from API routes.

## Purpose
- Log bridge: ModSecurity audit log ingestion and parsing
- Mitigation orchestrator: Confidence-gated enforcement decisions
- Model lifecycle: Model loading, version selection, health checks

## Expected Contents
- `log_bridge.py` — ModSecurity audit log parser and ingestion
- `mitigation.py` — Confidence-gated action orchestration (BLOCK/THROTTLE/ALLOW)
- `model_service.py` — Model loading and version management

## Architectural Role
Decouples enforcement logic from HTTP route handlers.
The log bridge connects the CRS detection layer to the ML scoring layer.
The mitigation orchestrator connects ML confidence output to Ansible automation.
