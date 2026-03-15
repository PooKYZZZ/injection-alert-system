# ML Preprocessing

This directory contains data preprocessing and tokenization pipelines.

## Purpose
- HTTP request tokenization for transformer input
- Dataset loading, splitting, and augmentation
- Label encoding and class balancing

## Current Repo State
- This package currently contains only the package marker and documentation.
- The active preprocessing scripts live under `scripts/` and `data/`, not under this package yet.

## Architectural Role
Transforms raw HTTP request data into model-ready tensors.
Used by both initial training and the 20-day retraining pipeline.
