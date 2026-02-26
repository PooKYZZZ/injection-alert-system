# ML Export

This directory contains model format conversion and optimization tools.

## Purpose
- Export trained PyTorch models to ONNX format
- Model optimization for inference latency

## Expected Contents
- `export_onnx.py` — PyTorch to ONNX conversion script
- `optimize.py` — ONNX graph optimization

## Architectural Role
Bridge between training output and production inference.
ONNX models are stored in the model registry.
