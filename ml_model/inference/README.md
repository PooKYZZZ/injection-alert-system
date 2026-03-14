# ML Inference

This directory contains the runtime prediction wrapper used by the backend.

## Purpose
- Model loading and prediction serving
- PyTorch-based inference for staged serving artifacts
- Mock fallback behavior in development and testing

## Current Contents
- `predict_attack.py` — model loading helpers and prediction utilities

## Architectural Role
Receives requests from the backend orchestration layer.
Returns class label + confidence score for confidence-gated mitigation.
