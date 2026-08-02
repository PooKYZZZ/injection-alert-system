# ML Evaluation

This package owns reusable metrics and script-first validation of experiment
bundles.

## Current entrypoints

- `metrics.py` — classification, calibration, threshold-security, latency,
  robustness, and reporting helpers extracted from the benchmark workflow.
- `evaluate.py` — validates a completed run without promoting or deploying it.

Example:

```powershell
.venv\Scripts\python.exe -m ml_model.evaluation.evaluate `
  --run-dir ml_model/results/benchmarks/<run-id>
```

Promotion remains a separate explicit operation under `ml_model/export/`.
