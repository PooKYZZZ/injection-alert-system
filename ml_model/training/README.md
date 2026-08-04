# ML Training

This package owns the script-first training implementation. Notebooks under
`ml_model/notebooks/` are optional control and reporting surfaces; they are not
the canonical implementation.

## Current entrypoints

- `train.py` — prepares the dataset and runs the confirmatory benchmark.
- `config.py` — loads portable TOML presets and validates run settings.
- `paths.py` — resolves the repository root and artifact locations.
- `device.py` — selects CPU/CUDA/MPS explicitly and validates precision.
- `confirmatory_runner.py` — extracted checkpoint/resume/failure-isolation
  runner used by the historical final benchmark.
- `losses.py` — weighted cross-entropy and focal-loss implementations.
- `model_factory.py` — native Hugging Face sequence-classification construction
  plus explicitly selected historical custom architectures.

## Clean setup

The repository targets Python 3.14. Use an isolated virtual environment and
install the existing runtime and training dependency files.

Windows PowerShell:

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements.train.txt
python -m pip install -e .
```

Linux/macOS:

```bash
python3.14 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements.train.txt
python -m pip install -e .
```

For the tested Windows RTX 3060 laptop CUDA path, install the CUDA PyTorch
wheel before the remaining dependencies:

```powershell
python -m pip install torch==2.13.0 --index-url https://download.pytorch.org/whl/cu130
python -m pip install -r requirements.txt
python -m pip install -r requirements.train.txt
python -m pip install -e .
```

For other GPUs or operating systems, use the official
[PyTorch install selector](https://pytorch.org/get-started/locally/) for the
target machine.

## Primary commands

Run the maintained minimal CPU training smoke with:

```powershell
.venv\Scripts\python.exe -m ml_model.training.train --config ml_model/configs/training/laptop_standard_smoke.toml
```

This command performs one native DistilBERT epoch using bounded samples and
prints the resulting run directory. `laptop_smoke.toml` remains available for
the older preparation-only check.

Linux/macOS equivalent:

```bash
python -m ml_model.training.train --config ml_model/configs/training/laptop_standard_smoke.toml
```

Run the full benchmark using the portable preset:

```powershell
.venv\Scripts\python.exe -m ml_model.training.train --config ml_model/configs/training/thesis_confirmatory.toml
```

Run the optimized Windows laptop CUDA DistilBERT preset:

```powershell
.venv\Scripts\python.exe -m ml_model.training.train --config ml_model/configs/training/laptop_cuda_distilbert.toml
```

This preset is tuned for the tested RTX 3060 laptop path: DistilBERT only,
FP16 mixed precision, batch size 64, evaluation batch size 128, gradient
accumulation 2, 5 epochs, and 2 data-loader workers. If VRAM errors occur,
lower `batch_size` first and keep `gradient_accumulation_steps = 2`.

Before a final full training run, benchmark the laptop with:

```powershell
.venv\Scripts\python.exe -m ml_model.training.benchmark_laptop `
  --config ml_model/configs/training/laptop_cuda_distilbert.toml
```

The benchmark runs short one-seed DistilBERT CUDA trials across batch size,
evaluation batch size, data-loader workers, and gradient accumulation settings.
It catches CUDA out-of-memory failures and saves:

- `benchmark_bootstrap.json`
- `benchmark_results.csv`
- `benchmark_results.json`
- `benchmark_summary.json`
- `recommended_final_config.toml`

Benchmark output is written under:

```text
ml_model/results/training_runs/laptop_benchmarks/<timestamp>/
```

Use `recommended_final_config.toml` as the starting point for the final training
configuration after reviewing the recorded speed and peak CUDA memory.

Override any setting without editing the preset, for example:

```powershell
.venv\Scripts\python.exe -m ml_model.training.train `
  --config ml_model/configs/training/thesis_confirmatory.toml `
  --device cpu `
  --models distilbert `
  --seeds 42 `
  --epochs 1 `
  --output-dir C:\temp\cybertrace-training
```

The canonical training path now defaults to DistilBERT only. Historical
benchmark variants remain available by passing their model keys explicitly
with `--models`, but they are no longer part of the default laptop workflow.

Resume from the run's last checkpoint by leaving `resume = true`, or provide
an explicit checkpoint with `--resume-checkpoint`. Checkpoints are loaded with
CPU mapping and then moved to the selected device.

The training entrypoint records the resolved configuration, selected device,
Python version, dependency versions, dataset information, and run identifier.
The training entrypoint does not promote or deploy an artifact. Promotion
remains an explicit operation under `ml_model/export/`.

By default, full training runs are written to a timestamped directory under
`ml_model/results/training_runs/`. Use `--output-dir` or
`IAS_TRAINING_OUTPUT_DIR` only when you want an explicit external destination.

## Architectural role

Training is separated from inference. Results are written under
`ml_model/results/training_runs/` and remain linked to their dataset, model,
seed, checkpoint, and evaluation metadata.

## Architecture and migration boundary

Future `distilbert` registry runs use the native Hugging Face
`DistilBertForSequenceClassification` task head. The training loop continues to
consume its `logits` output through the existing runner interface. New run
metadata records the architecture, architecture family, head type, model
class, model ID, dataset version, and preprocessing version.

Historical configurations with `architecture = "transformer"` use the
preserved `TransformerClassifier` path: masked mean pooling followed by its
custom MLP head. Those checkpoints and results remain historical reference
material; they are not relabeled or repackaged as native DistilBERT runs.
Historical notebooks are reference material only and are not a second
maintained training implementation. The active staged artifact at
`ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755`
is preserved until a separately evaluated model is explicitly promoted.

## Post-PR laptop sequence

The following is an operator procedure and is not evidence that these runs have
already been performed:

```powershell
# 1. Tiny CPU smoke
.venv\Scripts\python.exe -m ml_model.training.train --config ml_model\configs\training\laptop_standard_smoke.toml

# 2. Evaluate the run directory printed by training
.venv\Scripts\python.exe -m ml_model.evaluation.evaluate --run-dir "<printed-run-directory>"

# 3. One-seed CUDA run after smoke passes
.venv\Scripts\python.exe -m ml_model.training.train --config ml_model\configs\training\laptop_cuda_distilbert.toml

# 4. Three-seed thesis run only after the one-seed run and evaluation are healthy
.venv\Scripts\python.exe -m ml_model.training.train --config ml_model\configs\training\thesis_confirmatory.toml
```

If comparison on the main PC is needed, copy only run metadata, metrics, and
checkpoint material; do not commit generated artifacts. Do not claim that the
new model is better until the same fixed test split and evaluation code have
been used. Promotion is explicit and begins with a dry run. Inspect the live
CLI help before any write:

```powershell
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run --help
.venv\Scripts\python.exe -m ml_model.export.package_serving_artifact --help
```

Do not modify the active staging directory during documentation validation.
