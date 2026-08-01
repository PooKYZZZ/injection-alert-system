# Model Registry

Model weight files are not committed to this repository due to file size.

## Active Staged Run Path

The active DistilBERT staged serving path is intentionally stable:

`ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755/`

Do not rename this active directory as part of promotion.

## Setup

1. Obtain the approved `distilbert_v3_model.zip` bundle through the
   project’s secure, team-controlled artifact exchange. The repository does
   not contain private share URLs, credentials, or model weights. The artifact
   custodian must provide the bundle and its provenance through the approved
   project channel before a local lifecycle run.

2. Extract it into this directory (`ml_model/model_registry/staging/`)

3. Confirm this path exists after extraction:
   `ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755/`

4. Set `.env` to the real runtime model boundary:
   `MODEL_REGISTRY_PATH=ml_model/model_registry`
   (or set an explicit run directory under `ml_model/model_registry/staging/`)

5. Verify the exact Block 3A artifact lock before running the real-model test:

   ```powershell
   $env:PR7_RUN_REAL_MODEL="1"
   .venv\Scripts\python.exe -m pytest -q tests/ml/test_pr7_critical_vector.py
   ```

   The expected hashes and model version are recorded in
   `docs/project-ops/pr7-block3-artifact-lock.json`. A missing or mismatched
   artifact fails before the lifecycle stack starts.

## Promotion Workflow (Archive-And-Recreate)

Use the exporter promotion pipeline to replace the active run safely:

```powershell
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run ^
   --source-run-dir "ml_model\results\benchmarks\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" ^
   --active-run-dir "ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" ^
   --archive-root "ml_model\model_registry\archive" ^
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

The general development backend may still use its existing mock classifier
when the model boundary is unavailable. The guarded PR7 Block 3A lifecycle
does not use that fallback: its artifact-lock preflight fails before Docker
startup when the model files are missing or mismatched.
