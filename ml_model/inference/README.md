# ML Inference

This directory contains production inference code.

## Purpose
- Model loading and prediction serving
- ONNX Runtime or PyTorch inference
- Mock classifier for development/testing

## Expected Contents
- `predictor.py` — Real model inference (ONNX/PyTorch)
- `mock_model.py` — Pattern-based stub (development/testing)

## Architectural Role
Receives requests from the backend orchestration layer.
Returns class label + confidence score for confidence-gated mitigation.
