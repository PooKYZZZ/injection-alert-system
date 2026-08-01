# Training configurations

These TOML files are portable presets for the script-first workflow.

- `laptop_smoke.toml` performs a CPU-only, minimal dataset preparation check.
- `thesis_confirmatory.toml` describes the full three-model, three-seed benchmark.

Override paths at runtime with `--data-dir` and `--output-dir`; do not write
machine-specific paths into these files.
