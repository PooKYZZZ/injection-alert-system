# Training configurations

These TOML files are portable presets for the script-first workflow.

- `laptop_standard_smoke.toml` performs one real, CPU-only native DistilBERT
  training epoch over bounded samples and writes a complete run bundle under
  the ignored `ml_model/results/training_runs/` directory.
- `laptop_smoke.toml` performs a CPU-only, minimal dataset preparation check.
- `laptop_cuda_distilbert.toml` runs the optimized Windows laptop CUDA
  DistilBERT preset using FP16 mixed precision. It is intended for full laptop
  training output under `ml_model/results/training_runs/`.
- `thesis_confirmatory.toml` describes the thesis DistilBERT confirmatory run.

Override paths at runtime with `--data-dir` and `--output-dir`; do not write
machine-specific paths into these files.

The maintained smoke entry point is:

```powershell
.venv\Scripts\python.exe -m ml_model.training.train --config ml_model\configs\training\laptop_standard_smoke.toml
```

The standard smoke preset uses the native `DistilBertForSequenceClassification`
architecture. Generated checkpoints and run outputs remain local and must not
be committed.
