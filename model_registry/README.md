# Model Registry

This directory is the **versioned model promotion boundary** — not a model dump folder.

## Promotion Flow

```
ml_model/export/  →  model_registry/staging/  →  model_registry/production/
    (artifact)         (evaluation gate)             (live-serving artifact)
```

A model moves through this promotion path only after passing the evaluation gate defined in `ml_model/retraining/`.

## Directory Map

```
model_registry/
├── manifests/    # Per-version metadata files (YAML/JSON)
│                 # Schema: { version, training_date, dataset_fingerprint,
│                 #           eval_f1, eval_precision, eval_recall,
│                 #           confidence_threshold_used, promoted_by, rollback_target }
│
├── staging/      # Candidate model artifact (promoted from ml_model/export/)
│                 # Active during 20-day retraining evaluation window
│                 # config/environments/staging.yaml loads from this slot
│
└── production/   # Active production model artifact (validated and approved)
                  # config/environments/production.yaml loads ONLY from this slot
                  # Rollback = swap production/ with previous staging/ manifest entry
```

## Rollback Procedure

The rollback capability is trace-backed to `manifests/`. Each manifest records a `rollback_target` field pointing to the previous production version hash.
