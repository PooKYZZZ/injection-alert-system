# ML Training

This directory contains model training code and configuration.

## Purpose
- Training loop for transformer-based classifiers
- Hyperparameter configuration
- Training metrics evaluation and reporting

## Current Repo State
- This package currently contains only the package marker and documentation.
- Checked-in training configuration currently lives under `config/models/`.
- Training and evaluation work in this repo is still driven by notebooks and scripts rather than a committed `ml_model/training/train.py` entrypoint.

## Architectural Role
Separated from inference to maintain clean lifecycle boundaries.
Training artifacts are output to the model registry.
