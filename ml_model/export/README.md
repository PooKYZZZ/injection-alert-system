# ML Export

This directory contains model format conversion and optimization tools.

## Purpose
- Package trained model runs into self-contained serving artifacts
- Preserve runtime metadata used by the backend loader

## Current Contents
- `package_serving_artifact.py` — packages and validates staged serving artifacts under `ml_model/model_registry/staging/`

## Architectural Role
Bridge between training output and production inference.
The packaged serving artifacts are stored in the model registry.
