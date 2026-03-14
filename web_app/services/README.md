# Backend Services

This directory contains runtime services that sit between API routes and ML artifacts.

## Purpose
- Model lifecycle: model loading, version selection, and readiness behavior
- Runtime service boundaries that keep routes thin

## Current Contents
- `model_service.py` — model loading and runtime prediction boundary

## Architectural Role
Decouples runtime model behavior from HTTP route handlers and app startup.
