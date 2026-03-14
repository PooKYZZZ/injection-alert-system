# Model Registry

This directory is the canonical model artifact tree for the repository.

## Promotion flow

```text
ml_model/export/ -> ml_model/model_registry/staging/ -> ml_model/model_registry/production/
```

## Current structure

```text
ml_model/model_registry/
├── staging/     candidate artifacts and exact-run metadata
├── eval/        evaluation outputs, comparisons, and promotion summaries
└── production/  reserved production slot
```

## Rules

- Treat this directory as the only active model-registry path in the repo.
- Do not write to `production/` from the web app.
- Keep heavyweight model binaries out of casual documentation edits and cleanup passes.
