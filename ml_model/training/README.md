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
- `model_factory.py` — transformer and custom-head model construction.

## Clean setup

The repository declares Python 3.11 through 3.14. Use an isolated virtual
environment and install the existing runtime and training dependency files.

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements.train.txt
python -m pip install -e .
```

Linux/macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements.train.txt
python -m pip install -e .
```

If an accelerator-specific PyTorch build is needed, use the official
[PyTorch install selector](https://pytorch.org/get-started/locally/) for the
target operating system and hardware before installing the remaining training
dependencies.

## Primary commands

Run a CPU-safe preparation check with:

```powershell
.venv\Scripts\python.exe -m ml_model.training.train --config ml_model/configs/training/laptop_smoke.toml
```

Linux/macOS equivalent:

```bash
python -m ml_model.training.train --config ml_model/configs/training/laptop_smoke.toml
```

Run the full benchmark using the portable preset:

```powershell
.venv\Scripts\python.exe -m ml_model.training.train --config ml_model/configs/training/thesis_confirmatory.toml
```

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

Resume from the run's last checkpoint by leaving `resume = true`, or provide
an explicit checkpoint with `--resume-checkpoint`. Checkpoints are loaded with
CPU mapping and then moved to the selected device.

The training entrypoint records the resolved configuration, selected device,
Python version, dependency versions, dataset information, and run identifier.
The training entrypoint does not promote or deploy an artifact. Promotion
remains an explicit operation under `ml_model/export/`.

## Architectural role

Training is separated from inference. Results are written under
`ml_model/results/benchmarks/` and remain linked to their dataset, model,
seed, checkpoint, and evaluation metadata.
