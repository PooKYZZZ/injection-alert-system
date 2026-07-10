# ML Export

This directory contains model format conversion and optimization tools.

## Purpose
- Package trained model runs into self-contained serving artifacts
- Preserve runtime metadata used by the backend loader
- Promote final-training DistilBERT outputs into the staged serving boundary safely

## Current Contents
- `package_serving_artifact.py` — packages and validates staged serving artifacts under `ml_model/model_registry/staging/`
- `promote_final_training_run.py` — strict archive-and-recreate promotion pipeline from final-training outputs into the active staged run

## DistilBERT Promotion Workflow

Run a dry-run first:

```powershell
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run ^
	--source-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\notebooks\training done\Final training\results\v3_907k_cleaned_final_confirmatory_weighted_ce_3seed_20260412_035441\distilbert\loss_weighted_ce\seed_2026" ^
	--active-run-dir "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" ^
	--archive-root "G:\AI\PDDDD\injection-alert-system\ml_model\model_registry\archive" ^
	--checkpoint-filename "best_distilbert_weighted_ce_seed2026.pt" ^
	--archive-suffix "pre_20260420" ^
	--dry-run
```

Then run the real promotion (remove `--dry-run`).

The promotion flow is strict and fail-closed:

- validates required final-training files
- archives the full active staged run outside the active path
- recreates the active staged directory fresh
- writes `best_distilbert_ckpt.pt`, `config_used.json`, `eval_report.json`, and `git_hash.txt`
- writes a provisional, not-ready eval provenance record and passes that exact
  calibration source to `package_serving_artifact.py` in strict mode
- verifies local reload
- finalizes the same eval provenance record under
  `ml_model/model_registry/eval/<timestamp>/`, with packaging, reload, and
  quality readiness kept separate
- writes `provenance.json` and `MODEL_CARD.md`

If a downstream step fails after archive, the script restores the archived run back to the active path.

## Architectural Role
Bridge between training output and production inference.
The packaged serving artifacts are stored in the model registry.
