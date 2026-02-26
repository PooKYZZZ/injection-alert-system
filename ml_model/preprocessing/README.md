# ML Preprocessing

This directory contains data preprocessing and tokenization pipelines.

## Purpose
- HTTP request tokenization for transformer input
- Dataset loading, splitting, and augmentation
- Label encoding and class balancing

## Expected Contents
- `tokenize.py` — Tokenization pipeline (HuggingFace tokenizers)
- `dataset.py` — Dataset loading, train/val/test splits
- `transforms.py` — Data augmentation and normalization

## Architectural Role
Transforms raw HTTP request data into model-ready tensors.
Used by both initial training and the 20-day retraining pipeline.
