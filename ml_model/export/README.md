# ML Export

This directory contains model format conversion and optimization tools.

## Purpose
- Package trained model runs into self-contained serving artifacts
- Preserve runtime metadata used by the backend loader
- Promote final-training DistilBERT outputs into the staged serving boundary safely

## Current Contents
- `package_serving_artifact.py` — packages and validates staged serving artifacts under `ml_model/model_registry/staging/`
- `promote_final_training_run.py` — strict archive-and-recreate promotion pipeline from final-training outputs into the active staged run

The maintained serving path packages native DistilBERT only. The CLI accepts
`--model-key distilbert`; MiniLM, BERT-base, and other historical custom-model
artifacts are preserved as reference material and are rejected by the native
packager. Native checkpoint keys remain the Hugging Face keys (`distilbert.*`,
`pre_classifier.*`, and `classifier.*`); the legacy custom-key mapping is never
applied to them.

## DistilBERT Promotion Workflow

Run a dry-run first:

```powershell
.venv\Scripts\python.exe -m ml_model.export.promote_final_training_run ^
	--source-run-dir "ml_model\results\training_runs\<run_name>\distilbert\loss_weighted_ce\seed_2026" ^
	--active-run-dir "ml_model\model_registry\staging\distilbert_v3_907k_cleaned_20260312_133755" ^
	--archive-root "ml_model\model_registry\archive" ^
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

Promotion and packaging require a complete `training-run-contract.v2` payload
embedded as `run_contract` and a valid lowercase SHA-256 `run_contract_sha256`
that recomputes to the same value. Legacy, incomplete, missing, malformed, or
inconsistent provenance is rejected.
The packager then loads the checkpoint with `weights_only=True`, performs a
strict state-dict load, saves the self-contained model, and verifies a local
reload plus logits output. Use the real CPU smoke and the offline packaging
test as the bounded validation path; do not turn legacy notebooks into a
second implementation or edit the active staged artifact during validation.

`package_serving_artifact()` is also the authoritative final provenance
boundary. It carries one captured `summary_metrics.json` snapshot through the
export, writes `summary_metrics_sha256` into `serving_manifest.json`, publishes
the final summary links, and verifies the result before returning. Promotion
and simulation callers pass the captured snapshot; they do not perform a
separate post-packaging binding step.

If a downstream step fails after archive, the script restores the archived run back to the active path.

## Architectural Role
Bridge between training output and production inference.
The packaged serving artifacts are stored in the model registry.
