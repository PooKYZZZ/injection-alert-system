# Training configurations

These TOML files are portable presets for the script-first workflow.

- `laptop_smoke.toml` performs a CPU-only, minimal dataset preparation check.
- `laptop_cuda_distilbert.toml` runs the optimized Windows laptop CUDA
  DistilBERT preset using FP16 mixed precision. It is intended for full laptop
  training output under `ml_model/results/training_runs/`.
- `thesis_confirmatory.toml` describes the thesis DistilBERT confirmatory run.

Override paths at runtime with `--data-dir` and `--output-dir`; do not write
machine-specific paths into these files.
