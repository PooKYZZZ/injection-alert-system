# Model Registry

Model weight files are not committed to this repository due to file size.

## Active Staged Run Path

The active DistilBERT staged serving path is intentionally stable:

`ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755/`

Do not rename this active directory as part of promotion.

## Setup

1. Download `distilbert_v3_model.zip` from the team shared drive:
   **[PASTE YOUR SHARED DRIVE LINK HERE]**

2. Extract it into this directory (`ml_model/model_registry/staging/`)

3. Confirm this path exists after extraction:
   `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755/`

4. Set `.env` to the real runtime model boundary:
   `MODEL_REGISTRY_PATH=ml_model/model_registry`
   (or set an explicit run directory under `ml_model/model_registry/staging/`)

## Promotion Workflow (Archive-And-Recreate)

Use the exporter promotion pipeline to replace the active run safely:

```powershell
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run ^
   --source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" ^
   --active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" ^
   --archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" ^
   --checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" ^
   --archive-suffix "pre_20260420"
```

Recommended operator order:

1. Run with `--dry-run` first.
2. Review planned actions and archive target.
3. Run without `--dry-run` once validated.

The script writes `provenance.json` and `MODEL_CARD.md` in the active staged run directory.

## Rollback

If promotion fails after archiving, the script performs automatic rollback by restoring the archived run.

Manual rollback command shape if needed:

```powershell
Move-Item "ml_model/model_registry/archive/distilbert_v3_907k_cleaned_20260312_133755_pre_20260420" "ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755"
```

## Running without the model

The backend will start in mock mode automatically if model files are missing.
All API endpoints will respond — predictions will be simulated.
You will see this line in the backend terminal:
`WARNING  Model load failed — ... Starting in mock mode.`
