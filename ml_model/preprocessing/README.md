# ML Preprocessing

This package contains reusable dataset and split-loading helpers used by
training and evaluation.

## Current entrypoint

- `dataset_io.py` — resolves versioned processed datasets, loads Parquet/CSV
  splits, validates labels, creates run directories, and writes run metadata.
- `model_input.py` — dependency-light canonicalization, query/body redaction,
  model-input construction, and SHA-256 provenance for both training and serving.

The canonical processed dataset remains at the repository-level
`data/processed/` boundary. The package does not duplicate that dataset under
`ml_model/`.

## Architectural role

Transforms versioned processed data into the dataframes consumed by training
and evaluation. Runtime HTTP preprocessing re-exports the shared `model_input.py`
contract; it does not own a second implementation.

The repository defaults to the existing `v3_907k_cleaned` plus explicit
`http-preprocessor-v1` compatibility contract until the v2 dataset and model
exist. The only metadata-less artifact compatibility exception is the known
`v3_907k_cleaned` staged model; unknown metadata-less artifacts are rejected.
Use `laptop_smoke_v2.toml` to opt into the v2 dataset/model-input contract.

## Regenerating the v2 dataset

The legacy `data/processed/v3_907k_cleaned/` directory is preserved. After
verifying the raw source path, regenerate the new version with:

```powershell
.venv\Scripts\python.exe data\clean_907k.py
```

This writes `data/processed/v3_907k_cleaned_model_input_v2/` and its
`metadata_preprocessing.json`. No dataset generation or model retraining is
performed as part of the source-contract change.
