# ML model workspace

This directory contains the model source, reproducible benchmark entrypoints, evaluation helpers, runtime artifacts, and historical experiment material for CyberTrace.

## Canonical workflow

1. Prepare or train with `python -m ml_model.training.train`.
2. Evaluate a completed run with `python -m ml_model.evaluation.evaluate --run-dir <run-directory>`.
3. Keep benchmark outputs under `ml_model/results/benchmarks/`.
4. Keep the deployed runtime artifact under `ml_model/model_registry/staging/`.

The training entrypoint does not auto-promote or overwrite the runtime model. Promotion remains a separately reviewed operation.

## Layout

- `preprocessing/`: dataset loading and dataset-boundary helpers.
- `configs/training/`: portable TOML presets for smoke and thesis runs.
- `training/`: canonical training, loss, model-construction, and confirmatory-run code.
- `evaluation/`: metrics and run-bundle validation.
- `inference/`: runtime prediction code used by the application.
- `model_registry/`: staged and historical serving artifacts.
- `results/benchmarks/`: reproducible benchmark bundles and generated metrics.
- `notebooks/benchmarks/`: experiment-facing notebooks that call canonical Python modules.
- `notebooks/reports/`: evaluation and reporting notebooks.
- `notebooks/legacy/`: retained historical notebooks.
- `stale_review/`: uncertain or superseded material retained pending final disposition.
- `archive/archives/`: compressed historical source bundles.
- `docs/experiments/`: experiment specifications and benchmark evidence notes.
- `scripts/`: operational utilities that are not importable model packages.

## Prepare-only check

From the repository root:

```powershell
.venv\Scripts\python.exe -m ml_model.training.train `
  --prepare-only `
  --models distilbert `
  --seeds 42 `
  --device cpu `
  --output-dir C:\path\to\temporary-run
```

Use a temporary output directory for checks. A full training run is intentionally separate from serving-model deployment.
