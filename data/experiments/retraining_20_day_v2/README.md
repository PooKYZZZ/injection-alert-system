# Route-aware 20-day fixture collection

This directory contains a deterministic controlled simulation fixture for the
Land Records Portal's actual `GET /records/search` entry point.

The generator creates 20 batches of 30 rows each:

- 12 ordinary benign search values;
- 8 difficult-but-benign search values containing security-related words or
  harmless encoding/punctuation boundaries;
- 10 labeled attack controls covering SQL Injection, Code Injection, and Other
  Attacks with a rotating 4/3/3, 3/4/3, or 3/3/4 distribution.

Every row is marked `is_synthetic=true` and
`review_status=curated_simulation_fixture`. These are not reviewed production
samples and must not be exported as approved training data. They are allowed
only when the simulator is run with the explicit `--controlled-simulation`
flag.

The existing locked `golden-v2` set remains separate and is never copied into
these batches. The historical `v3_907k_cleaned` validation and test splits also
remain unchanged. Each cumulative day means historical training data plus all
fixture rows from that day and prior days; it does not mean an epoch.

## Recreate the fixture collection

From the repository root:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.generate_batches `
  --output-dir data/experiments/retraining_20_day_v2 `
  --seed 2026
```

The command writes the JSONL files under
`daily_batches/records_search_v2/` and a reproducibility manifest at the root
of this directory. The manifest records the generator version, seed, daily
counts, label distribution, batch hashes, and the synthetic-only evidence
boundary.

Validate all 20 batches and build the cumulative day snapshots without
training:

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.preflight_20_day `
  --config ml_model/configs/retraining_20_day_v2.toml `
  --historical-data-dir data/processed/v3_907k_cleaned `
  --daily-batch-dir data/experiments/retraining_20_day_v2/daily_batches/records_search_v2 `
  --output-dir ml_model/results/retraining_20_day_v2/preflight
```

The resulting report must say `PREPARATION_SUCCESS`, `600` accepted fixture
rows, and `0` rejected rows. It must also say `real_training_status=NOT_RUN`
and `model_quality_conclusion=NOT_PERMITTED`; this command proves only that
the inputs and snapshots are ready for the laptop training step.

## Execute the controlled simulation

The generator and batch preflight can run on the development PC. Native
DistilBERT training remains a separate laptop task and must not be inferred
from the presence of these fixtures.

```powershell
.venv\Scripts\python.exe -m ml_model.retraining.simulate_20_day `
  --config ml_model/configs/retraining_20_day_v2.toml `
  --historical-data-dir data/processed/v3_907k_cleaned `
  --daily-batch-dir data/experiments/retraining_20_day_v2/daily_batches/records_search_v2 `
  --output-dir ml_model/results/retraining_20_day_v2/native `
  --baseline ml_model/results/retraining_20_day_v2/baseline.json `
  --controlled-simulation `
  --days 1
```

Do not use a synthetic baseline or call this output a model-quality result.
The native simulation requires a freshly frozen baseline and native candidate
artifacts from the laptop. Until those exist, use the all-day orchestration
smoke and the data/snapshot preflight; report native training as `NOT_RUN`.
