# ML Training

This directory contains model training code and configuration.

## Purpose
- Training loop for transformer-based classifiers
- Hyperparameter configuration
- Training metrics evaluation and reporting

## Expected Contents
- `train.py` — Training loop entry point
- `config.yaml` — Hyperparameters, epochs, learning rate schedules
- `evaluate.py` — Metrics computation (accuracy, F1, FPR, confusion matrix)

## Architectural Role
Separated from inference to maintain clean lifecycle boundaries.
Training artifacts are output to the model registry.
