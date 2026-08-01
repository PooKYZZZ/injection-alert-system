# ML Preprocessing

This package contains reusable dataset and split-loading helpers used by
training and evaluation.

## Current entrypoint

- `dataset_io.py` — resolves versioned processed datasets, loads Parquet/CSV
  splits, validates labels, creates run directories, and writes run metadata.

The canonical processed dataset remains at the repository-level
`data/processed/` boundary. The package does not duplicate that dataset under
`ml_model/`.

## Architectural role

Transforms versioned processed data into the dataframes consumed by training
and evaluation. Runtime HTTP preprocessing remains owned by
`web_app/application/http_preprocessor.py`; training-serving parity must be
verified before those two boundaries are merged.
