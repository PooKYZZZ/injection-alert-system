# Laptop Training Handoff

## Current repository state

- Branch: `feature/20-day-retraining-simulation`
- Merge/PR state: local implementation branch; not pushed and no remote PR was
  created in this session.
- Experiment status on the development PC: unit tests and the two-day
  orchestration smoke passed. The real baseline, seed-2026 training,
  three-seed confirmation, and full 20-day native DistilBERT simulation were
  `NOT_RUN` / `REQUIRES_LAPTOP`.
- Primary contract: `ml_model/configs/retraining_20_day_v1.toml`
- Primary output root: `ml_model/results/retraining_20_day_v1/`

All commands below are run from the repository root. They use relative paths,
so they remain portable when the repository path contains spaces.

## Synchronize the laptop

If the PR has been merged into `master`:

```powershell
git fetch origin
git switch master
git pull --ff-only origin master
```

If the PR is still open:

```powershell
git fetch origin
git switch feature/20-day-retraining-simulation
git pull --ff-only origin feature/20-day-retraining-simulation
```

Confirm the expected implementation is present:

```powershell
git status --short
git log -6 --oneline
Test-Path ml_model/configs/retraining_20_day_v1.toml
Test-Path docs/project-ops/LAPTOP_TRAINING_HANDOFF.md
```

## Recreate and verify the environment

Use the repository’s existing dependency files; this implementation adds no
dependency.

```powershell
py -3.14 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r requirements.train.txt
```

Verify Python, PyTorch, CUDA, the GPU, and the established dataset before
training:

```powershell
python --version
python -c "import torch; print({'torch': torch.__version__, 'cuda_available': torch.cuda.is_available(), 'cuda_version': torch.version.cuda, 'device_count': torch.cuda.device_count()}); print([torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())])"
nvidia-smi
Test-Path data/processed/v3_907k_cleaned/train.parquet
Test-Path data/processed/v3_907k_cleaned/validation.parquet
Test-Path data/processed/v3_907k_cleaned/test.parquet
Get-ChildItem data/processed/v3_907k_cleaned -File | Select-Object Name,Length
```

If CUDA, the expected GPU, or the established dataset is unavailable, stop and
record the operation as `BLOCKED`; do not substitute v2 preprocessing or an
unverified dataset.

## Repository checks and smoke

Run the focused implementation tests:

```powershell
.venv\Scripts\python.exe -m pytest -q --tb=short tests/unit/test_run_baseline.py tests/unit/test_experiment_contract.py tests/unit/test_golden_controls.py tests/unit/test_retraining_batches.py tests/unit/test_simulate_20_day.py
```

Run the tiny no-network, two-day orchestration smoke. Its success proves
orchestration and failure safety only, not model quality:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.simulate_20_day --config ml_model/configs/retraining_20_day_v1.toml --output-dir ml_model/results/retraining_20_day_v1/smoke --smoke --days 1 2
```

Expected smoke files include:

- `ml_model/results/retraining_20_day_v1/smoke/simulation_report.json`
- `ml_model/results/retraining_20_day_v1/smoke/simulation_report.md`
- `ml_model/results/retraining_20_day_v1/smoke/day_01/day_report.json`
- `ml_model/results/retraining_20_day_v1/smoke/day_02/day_report.json`

## Baseline first

Select the exact current staged artifact. Do not let the baseline discover an
arbitrary latest run or write to an active registry:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.run_baseline `
  --config ml_model/configs/retraining_20_day_v1.toml `
  --artifact-dir ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755 `
  --output ml_model/results/retraining_20_day_v1/baseline.json
```

Inspect `baseline.json` before candidate training. The report records artifact
identity and hash, golden results, the exact pagination result, packaging and
backend-loading status, and metric availability. Missing operational rates
remain `Unknown`/`REQUIRES_LAPTOP`; they are not converted to zero.

## Corrected one-seed run

After the baseline is frozen, run the maintained simulator for the first
cumulative day with seed `2026`:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.simulate_20_day `
  --config ml_model/configs/retraining_20_day_v1.toml `
  --historical-data-dir data/processed/v3_907k_cleaned `
  --daily-batch-dir data/experiments/retraining_20_day_v1/daily_batches `
  --output-dir ml_model/results/retraining_20_day_v1/seed_2026 `
  --baseline ml_model/results/retraining_20_day_v1/baseline.json `
  --days 1
```

The run must use native DistilBERT, v1 preprocessing, the locked labels and
policy, and a maximum of four epochs. Inspect the day report, evaluator output,
candidate package, reload result, golden controls, exact pagination result, and
acceptance gates before proceeding.

## Three-seed confirmation

Run seeds `42`, `1337`, and `2026` only after the one-seed candidate passes the
mandatory blockers. The existing training TOML freezes the seed list and
maximum epoch count. For a prepared cumulative snapshot, the maintained
training entrypoint is:

```powershell
.venv\Scripts\python.exe -m ml_model.training.train `
  --config ml_model/configs/training/thesis_confirmatory.toml `
  --data-dir ml_model/results/retraining_20_day_v1/seed_2026/day_01/snapshots/day_01 `
  --output-dir ml_model/results/retraining_20_day_v1/three_seed `
  --no-resume
```

Record every seed, mean, standard deviation, best and worst result, class
instability, golden results, false-positive/escape trends, calibration, and
latency. Do not select only the best seed.

## Full 20-day cumulative simulation

Run all days only after baseline, one-seed, and three-seed prerequisites pass:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.simulate_20_day `
  --config ml_model/configs/retraining_20_day_v1.toml `
  --historical-data-dir data/processed/v3_907k_cleaned `
  --daily-batch-dir data/experiments/retraining_20_day_v1/daily_batches `
  --output-dir ml_model/results/retraining_20_day_v1/full `
  --baseline ml_model/results/retraining_20_day_v1/baseline.json `
  --days 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20
```

Expected output is one directory per day containing validation evidence,
cumulative snapshot manifests, evaluator/training results, an isolated
candidate registry where applicable, and `day_report.json`, plus:

- `ml_model/results/retraining_20_day_v1/full/simulation_report.json`
- `ml_model/results/retraining_20_day_v1/full/simulation_report.md`

Every day must be represented as `ACCEPTED` or `REJECTED`; a failed day must
retain its error, stage, quarantine, and partial evidence. The simulator does
not modify `ml_model/model_registry/production/` or an active staging artifact.

## Reporting and copy-back

Inspect reports from the repository root:

```powershell
Get-Content ml_model/results/retraining_20_day_v1/baseline.json
Get-Content ml_model/results/retraining_20_day_v1/full/simulation_report.json
Get-Content ml_model/results/retraining_20_day_v1/full/simulation_report.md
Get-ChildItem ml_model/results/retraining_20_day_v1/full -Recurse -File | Select-Object FullName,Length
```

Copy back only reviewable evidence: baseline and aggregate/day JSON or
Markdown reports, validation/quarantine reports, snapshot manifests and
hashes, selected small metadata manifests, and explicitly requested candidate
identity evidence. Do not copy or commit private datasets, full checkpoints,
ordinary logs, secrets, virtual environments, caches, or generated model
artifacts without an explicit artifact handoff decision.

## Failure recovery and rollback boundary

If a batch is rejected, preserve the quarantine and day report, correct the
prepared input through the review process, and rerun that day in a new output
directory. If training, evaluation, packaging, reload, golden controls, or the
backend check fails, preserve the candidate and failure evidence; do not skip
the day and do not promote it. The active model remains unchanged.

Any later staging promotion or rollback is a separate, explicitly authorized
operation. Before it, archive and hash the current artifact, validate the
candidate metadata, reload-test it, run the backend controls, and confirm the
old artifact remains available. This handoff does not claim hosted, WAF, or
production readiness.

## Current evidence status

| Operation | Status in this coding session |
|---|---|
| Contract, validator, snapshot, simulator, baseline tooling | `PASS` (implemented and focused-tested) |
| Two-day synthetic orchestration smoke | `PASS` (orchestration-only) |
| Real current-model baseline | `NOT_RUN` / `REQUIRES_LAPTOP` |
| Corrected seed-2026 native training | `NOT_RUN` / `REQUIRES_LAPTOP` |
| Three-seed confirmation | `NOT_RUN` / `REQUIRES_LAPTOP` |
| Full cumulative 20-day native simulation | `NOT_RUN` / `REQUIRES_LAPTOP` |
| Hosted/production promotion or rollback | `NOT_RUN` / not authorized |
