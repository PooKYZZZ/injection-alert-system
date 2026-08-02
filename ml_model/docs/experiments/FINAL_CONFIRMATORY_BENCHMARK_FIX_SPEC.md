# Final Confirmatory Benchmark Fix Specification

## 1. Fix Strategy

- Use the benchmark notebook as the experiment-facing orchestration surface, but make the shared code in `ml_model\training`, `ml_model\preprocessing`, and `ml_model\evaluation` the only canonical module source.
- Repurpose the current training notebook from screening mode into a fixed final confirmatory benchmark runner.
- Repurpose the current evaluation notebook into a final aggregation/reporting consumer for one completed confirmatory run.
- Remove duplicate local support modules in `Final training` because they are byte-for-byte duplicates of the canonical shared modules and currently create maintenance ambiguity without being imported.
- Keep the smallest realistic scope:
  - no new model architectures
  - no new losses
  - no repo-wide redesign
  - no robustness suite in first-pass final confirmatory benchmark
- Implement the missing final-stage requirements directly:
  - fixed 3-model final roster
  - fixed `weighted_ce`
  - minimum 3 seeds
  - reduced epoch budget for practical final execution
  - explicit post-hoc calibration reporting
  - explicit inference latency benchmarking as a separate step
  - multi-seed aggregation with mean/std and 95% CI
  - per-class aggregate summary
  - unambiguous manifest and artifact naming

## 2. Exact File Decisions

- `ml_model\stale_review\01_train_models_lightweight_screening_ch3.ipynb`
  - `rename + edit`
  - new filename: `ml_model\notebooks\benchmarks\01_train_models_final_confirmatory.ipynb`
  - purpose after fix: final multi-seed confirmatory training runner for the 3 fixed shortlisted models

- `ml_model\notebooks\legacy\02_evaluate_models.ipynb`
  - `rename + edit`
  - new filename: `ml_model\notebooks\reports\02_evaluate_final_confirmatory.ipynb`
  - purpose after fix: consume one finished confirmatory run and generate final comparison and aggregated reporting artifacts

- `ml_model\evaluation\metrics.py`
  - `remove`
  - exact purpose after fix: none; canonical shared module is `ml_model\evaluation\metrics.py`

- `ml_model\training\losses.py`
  - `remove`
  - exact purpose after fix: none; canonical shared module is `ml_model\training\losses.py`

- `ml_model\preprocessing\dataset_io.py`
  - `remove`
  - exact purpose after fix: none; canonical shared module is `ml_model\preprocessing\dataset_io.py`

- `ml_model\training\model_factory.py`
  - `remove`
  - exact purpose after fix: none; canonical shared module is `ml_model\training\model_factory.py`

- `ml_model\evaluation\metrics.py`
  - `edit`
  - purpose after fix: shared metric/calibration/latency/aggregation utilities used by both final notebooks

- `ml_model\training\losses.py`
  - `keep`
  - purpose after fix: shared loss builder; final notebook will constrain usage to `weighted_ce`

- `ml_model\preprocessing\dataset_io.py`
  - `edit minimally`
  - purpose after fix: shared run/artifact path helpers and data-loading helpers; final notebooks will use it with an explicit final-results base directory

- `ml_model\training\model_factory.py`
  - `keep`
  - purpose after fix: shared model factory; ALBERT stays available globally but is removed from the final benchmark config

## 3. Exact Notebook Changes

### `01_train_models_final_confirmatory.ipynb`

- config variables to change:
  - `DATASET_VERSION = "v3_907k_cleaned"`
  - `BENCHMARK_SEEDS = [42, 1337, 2026]`
  - `N_EPOCHS = 4`
  - `EARLY_STOP_PATIENCE = 2`
  - `MAX_SEQ_LEN = 128`
  - `RUN_MODEL_KEYS = ["distilbert", "minilm_l6", "tinybert_bigru_attn"]`
  - `RUN_LOSS_KEYS = ["weighted_ce"]`
  - `LOSS_KEYS_BY_MODEL = {model_key: ["weighted_ce"] for model_key in RUN_MODEL_KEYS}`
  - `ENABLE_CALIBRATION = True`
  - `ENABLE_RELIABILITY_DIAGRAMS = True`
  - `ENABLE_THRESHOLD_SECURITY_ARTIFACTS = True`
  - `ENABLE_LATENCY_BENCHMARK = True`
  - `LIGHTWEIGHT_MODE = False`
  - `CONFIDENCE_THRESHOLDS = [0.5, 0.7, 0.8, 0.9]`
  - add `FINAL_RESULTS_BASE_DIR = REPO_ROOT / "ml_model" / "notebooks" / "training done" / "Final training" / "results"`
  - add `RUN_KIND = "final_confirmatory_benchmark"`
  - add `FIXED_LOSS_KEY = "weighted_ce"`
  - add `RUN_NAME = f"{DATASET_VERSION}_final_confirmatory_{FIXED_LOSS_KEY}_{len(BENCHMARK_SEEDS)}seed"`
  - change `RUN_OUTPUT_DIR = make_output_dir(RUN_NAME, base_dir=FINAL_RESULTS_BASE_DIR)`

- logic to remove:
  - the screening framing in the title markdown
  - all language stating `lightweight screening`, `broad screening`, `shortlist`, `fast screening`, `screening winners`
  - hard guard `if BENCHMARK_SEEDS != [42]: raise ...`
  - hard guard `if N_EPOCHS != 3: raise ...`
  - hard guard `if MAX_SEQ_LEN != 128: raise ...`
  - `RUN_MODEL_KEYS` entry `albert_cnn`
  - manual per-model execution cells:
    - `# Model run 1/4: distilbert`
    - `# Model run 2/4: minilm_l6`
    - `# Model run 3/4: tinybert_bigru_attn`
    - `# Model run 4/4: albert_cnn`
  - `run_screening_model(...)`
  - `screening_seed`
  - `selected_variant_rows` as winner logic
  - screening-only filenames:
    - `all_loss_variant_screening.csv`
    - `model_screening_winners.csv`
  - screening manifest fields:
    - `mode: "lightweight_screening"`
    - `completed_model_keys`
    - `skipped_model_keys`
    - `model_selection_rule`
    - `selection_guardrail`
    - `model_selection_manifest`

- logic to keep:
  - repo-root discovery
  - imports from the canonical `ml_model.preprocessing`, `ml_model.training`, and `ml_model.evaluation` packages
  - split loading and label encoding
  - split hygiene evidence
  - tokenizer caching and pre-tokenization
  - dataset class and dataloaders
  - optimizer/scheduler setup
  - training loop with early stopping by validation macro F1 and validation loss tie-break
  - checkpoint save/load
  - temperature scaling
  - saving validation/test logits and probabilities
  - saving confusion matrix and calibration artifacts
  - saving per-class metrics and security summary artifacts

- logic to add:
  - one full automatic execution cell that loops all 3 models and all 3 seeds
  - per-seed summary rows accumulated for every `model_key + loss_key`
  - per-loss aggregate summary even though only one loss is used
  - per-model per-class aggregation across seeds
  - explicit 95% CI generation for numeric aggregate metrics
  - explicit latency benchmark as a separate post-training step using the best checkpoint
  - separate latency protocol payload
  - explicit distinction between:
    - training workflow runtime
    - inference latency benchmark
  - metric schema block in the manifest

- output naming changes:
  - `all_loss_variant_screening.csv` -> `all_loss_variant_aggregates.csv`
  - `model_screening_winners.csv` -> `model_benchmark_summary.csv`
  - `deployment_metrics.json` -> `latency_summary.json`
  - `total_runtime_sec` -> `training_workflow_runtime_sec`
  - `mean_epoch_time_sec` -> `mean_epoch_training_time_sec`
  - keep `summary_metrics.json` but expand fields
  - keep `aggregate_summary.json`
  - add `per_class_summary_aggregated.csv` per model/loss

- manifest changes:
  - exact top-level fields to add:
    - `artifact_schema_version`
    - `run_kind`
    - `run_name`
    - `dataset_version`
    - `text_col`
    - `label_col`
    - `label_names`
    - `n_seeds`
    - `seed_list`
    - `fixed_loss_key`
    - `model_keys`
    - `max_seq_len`
    - `ece_n_bins`
    - `confidence_thresholds`
    - `checkpoint_selection_rule`
    - `analysis_flags`
    - `latency_protocol`
    - `metric_schema`
    - `training_runtime_fields`
    - `split_summaries`
    - `split_hygiene_evidence`
    - `model_truncation_overview`
    - `models`
    - `created_at`
    - `run_output_dir`
    - `evaluation_output_dir`
  - exact top-level fields to remove:
    - `mode`
    - `completed_model_keys`
    - `skipped_model_keys`
    - `loss_keys_by_model`
    - `model_selection_rule`
    - `variant_selection_sort_keys`
    - `selection_guardrail`
    - `model_selection_manifest`

### `02_evaluate_final_confirmatory.ipynb`

- config variables to change:
  - keep `DATASET_VERSION = "v3_907k_cleaned"`
  - keep `ECE_N_BINS = 15`
  - keep `CONFIDENCE_THRESHOLDS = [0.5, 0.7, 0.8, 0.9]`
  - set `EVAL_ENABLE_ROBUSTNESS = False` by default
  - add `EXPECTED_RUN_KIND = "final_confirmatory_benchmark"`
  - add `FINAL_RESULTS_BASE_DIR = REPO_ROOT / "ml_model" / "notebooks" / "training done" / "Final training" / "results"`
  - change default run-dir discovery to `latest_run_dir(base_dir=FINAL_RESULTS_BASE_DIR, dataset_version=DATASET_VERSION)`

- logic to remove:
  - robustness suite from the first-pass final benchmark
  - `selected_loss_key_for_model(...)` logic that assumes a loss search stage
  - regeneration of seed-level confusion/calibration/security artifacts in evaluation
  - any implication that evaluation still has to reconstruct artifacts already saved during training
  - robustness outputs:
    - `robustness_summary.csv`
    - `robustness_aggregated.csv`
    - `*_robustness_failures.csv`

- logic to keep:
  - manifest loading
  - run-dir override support
  - loading saved per-seed logits and calibration temperature
  - recomputing calibrated and uncalibrated metrics from saved outputs
  - seed-level table build
  - model-level aggregation across seeds
  - evaluation summary JSON

- logic to add:
  - assert `manifest["run_kind"] == "final_confirmatory_benchmark"`
  - replace selected-loss resolution with fixed-loss resolution:
    - use `manifest["fixed_loss_key"]`
    - fall back only if one `loss_*` dir exists
  - aggregate per-class metrics across seeds by reading each seed’s `per_class_metrics.json`
  - aggregate latency outputs across seeds by reading each seed’s `latency_summary.json`
  - add CI columns to the main model comparison output
  - generate explicit latency comparison output
  - generate explicit aggregated per-class summary output

- output naming changes:
  - `model_comparison.csv` -> `final_model_comparison.csv`
  - add `aggregated_per_class_summary.csv`
  - add `latency_comparison.csv`
  - keep `evaluation_summary.json` with updated generated-output list

- manifest changes:
  - evaluation summary exact fields:
    - `evaluation_kind`
    - `source_run_kind`
    - `source_run_dir`
    - `evaluation_output_dir`
    - `dataset_version`
    - `metric_schema_version`
    - `model_count`
    - `generated_outputs`
    - `consumed_artifacts`
    - `created_at`
  - remove from evaluation summary:
    - robustness-specific counts
    - robustness-specific generated outputs

## 4. Exact Module Changes

### `ml_model\evaluation\metrics.py`

- what stays:
  - `expected_calibration_error`
  - `softmax_np`
  - `negative_log_likelihood_from_logits`
  - `calibration_bins_frame`
  - `save_reliability_diagram_artifacts`
  - `top_label_calibration_frame`
  - `collect_logits_labels_loss`
  - `collect_logits_from_texts`
  - `TemperatureScaler`
  - `fit_temperature_scaling`
  - `compute_per_class_metrics`
  - `confusion_matrix_frame`
  - `save_confusion_matrix_artifacts`
  - `attack_to_normal_false_negative_frame`
  - `normal_false_positive_metrics`
  - `confidence_band_summary_frame`
  - `per_class_recall_at_threshold_frame`
  - `threshold_security_summary`
  - `model_size_megabytes`

- what must be extended:
  - `evaluate_from_logits`
    - add `balanced_accuracy`
    - add `macro_recall`
    - add `brier_score`
  - `estimate_inference_latency_ms`
    - keep for backward compatibility only
    - do not use as the final benchmark output function

- exact new functions or outputs to add:
  - `multiclass_brier_score(probs: np.ndarray, labels: np.ndarray) -> float`
  - `mean_std_ci95(values: Sequence[float]) -> dict[str, float | int]`
    - output keys:
      - `n`
      - `mean`
      - `std`
      - `ci95_lower`
      - `ci95_upper`
  - `append_summary_stats(prefix: str, values: Sequence[float]) -> dict[str, float | int]`
    - output keys:
      - `"{prefix}_mean"`
      - `"{prefix}_std"`
      - `"{prefix}_ci95_lower"`
      - `"{prefix}_ci95_upper"`
  - `aggregate_numeric_columns(df: pd.DataFrame, exclude: Sequence[str]) -> dict[str, float | int]`
  - `aggregate_per_class_metrics(seed_rows: list[pd.DataFrame]) -> pd.DataFrame`
    - grouped by:
      - `label_id`
      - `label_name`
    - aggregate columns:
      - `precision_mean`
      - `precision_std`
      - `precision_ci95_lower`
      - `precision_ci95_upper`
      - `recall_mean`
      - `recall_std`
      - `recall_ci95_lower`
      - `recall_ci95_upper`
      - `f1_mean`
      - `f1_std`
      - `f1_ci95_lower`
      - `f1_ci95_upper`
      - `support_mean`
      - `support_std`
  - `benchmark_inference_latency(...) -> dict[str, float | int | str | bool]`
    - exact output keys:
      - `latency_mean_ms`
      - `latency_std_ms`
      - `latency_p50_ms`
      - `latency_p95_ms`
      - `latency_min_ms`
      - `latency_max_ms`
      - `n_measurements`
      - `batch_size`
      - `sequence_length`
      - `device`
      - `autocast_bf16`

- any duplication/path issue that must be resolved:
  - the duplicate helper copies must remain outside the canonical source packages for historical reference only
  - notebooks must import metrics only from `ml_model.evaluation.metrics`

### `ml_model\training\losses.py`

- what stays:
  - `LOSS_ABLATION_GRID`
  - `compute_class_weights`
  - `FocalLoss`
  - `build_loss`

- what must be extended:
  - nothing for first pass

- exact new functions or outputs to add:
  - none

- any duplication/path issue that must be resolved:
  - remove the duplicate local `losses.py` in `Final training`

### `ml_model\preprocessing\dataset_io.py`

- what stays:
  - all current data split helpers
  - all current JSON/CSV/NPZ save/load helpers
  - `make_output_dir`
  - `latest_run_dir`
  - `model_run_dir`
  - `loss_variant_dir`
  - `seed_run_dir`
  - `evaluation_dir`

- what must be extended:
  - keep changes minimal
  - add one helper only if desired for naming clarity

- exact new functions or outputs to add:
  - optional helper:
    - `def make_run_name(dataset_version: str, run_kind: str, loss_key: str, n_seeds: int) -> str`
    - output example:
      - `v3_907k_cleaned_final_confirmatory_weighted_ce_3seed`

- any duplication/path issue that must be resolved:
  - `DEFAULT_RUNS_DIR` currently points to generic training results
  - final notebooks must pass `base_dir=FINAL_RESULTS_BASE_DIR` explicitly so final outputs stay inside `Final training/results`
  - remove the duplicate local `io.py`

### `ml_model\training\model_factory.py`

- what stays:
  - `build_activation`
  - `get_hidden_size`
  - `infer_head_type`
  - `infer_architecture_family`
  - `TransformerClassifier`
  - `TinyBERTBiGRUAttentionClassifier`
  - `ALBERTCNNClassifier`
  - `build_model`

- what must be extended:
  - none for first pass

- exact new functions or outputs to add:
  - none

- any duplication/path issue that must be resolved:
  - do not remove ALBERT from the shared module
  - remove ALBERT only from the final notebook config
  - remove the duplicate local `models.py`

## 5. Mandatory Final Metrics

- exact final metric list:
  - `accuracy`
  - `balanced_accuracy`
  - `macro_f1`
  - `weighted_f1`
  - `per-class precision`
  - `per-class recall`
  - `per-class f1`
  - `per-class support`
  - `confusion_matrix`
  - `ece_uncalibrated`
  - `ece_calibrated`
  - `nll_uncalibrated`
  - `nll_calibrated`
  - `brier_uncalibrated`
  - `brier_calibrated`
  - `normal_false_positive_rate`
  - `attack_escape_rate`
  - `inference latency summary`
  - `multi-seed mean/std`
  - `95% CI for key metrics`

- exact naming to use in code and outputs:
  - validation:
    - `val_accuracy`
    - `val_balanced_accuracy`
    - `val_macro_f1`
    - `val_weighted_f1`
    - `val_ece_uncalibrated`
    - `val_ece_calibrated`
    - `val_nll_uncalibrated`
    - `val_nll_calibrated`
    - `val_brier_uncalibrated`
    - `val_brier_calibrated`
  - test:
    - `test_accuracy`
    - `test_balanced_accuracy`
    - `test_macro_f1`
    - `test_weighted_f1`
    - `test_ece_uncalibrated`
    - `test_ece_calibrated`
    - `test_nll_uncalibrated`
    - `test_nll_calibrated`
    - `test_brier_uncalibrated`
    - `test_brier_calibrated`
  - security:
    - `normal_false_positive_rate`
    - `attack_escape_rate`
  - latency:
    - `inference_latency_mean_ms`
    - `inference_latency_std_ms`
    - `inference_latency_p50_ms`
    - `inference_latency_p95_ms`
  - workflow runtime:
    - `training_workflow_runtime_sec`
    - `mean_epoch_training_time_sec`
  - multi-seed aggregates:
    - `<metric>_mean`
    - `<metric>_std`
    - `<metric>_ci95_lower`
    - `<metric>_ci95_upper`

## 6. Mandatory Final Artifacts

- exact filenames or artifact types that should exist after a successful run:
  - run root:
    - `run_manifest.json`
    - `all_loss_variant_aggregates.csv`
    - `model_benchmark_summary.csv`
  - per model:
    - `<model_key>/truncation_evidence.json`
    - `<model_key>/loss_variant_aggregates.csv`
  - per model/loss:
    - `<model_key>/loss_weighted_ce/seed_summaries.csv`
    - `<model_key>/loss_weighted_ce/aggregate_summary.json`
    - `<model_key>/loss_weighted_ce/per_class_summary_aggregated.csv`
  - per seed:
    - `<model_key>/loss_weighted_ce/seed_0042/config_metadata.json`
    - `<model_key>/loss_weighted_ce/seed_0042/summary_metrics.json`
    - `<model_key>/loss_weighted_ce/seed_0042/per_class_metrics.json`
    - `<model_key>/loss_weighted_ce/seed_0042/confusion_matrix.csv`
    - `<model_key>/loss_weighted_ce/seed_0042/confusion_matrix.png`
    - `<model_key>/loss_weighted_ce/seed_0042/calibration.json`
    - `<model_key>/loss_weighted_ce/seed_0042/reliability_uncalibrated.csv`
    - `<model_key>/loss_weighted_ce/seed_0042/reliability_uncalibrated.png`
    - `<model_key>/loss_weighted_ce/seed_0042/reliability_calibrated.csv`
    - `<model_key>/loss_weighted_ce/seed_0042/reliability_calibrated.png`
    - `<model_key>/loss_weighted_ce/seed_0042/top_label_calibration_uncalibrated.csv`
    - `<model_key>/loss_weighted_ce/seed_0042/top_label_calibration_calibrated.csv`
    - `<model_key>/loss_weighted_ce/seed_0042/validation_outputs.npz`
    - `<model_key>/loss_weighted_ce/seed_0042/test_outputs.npz`
    - `<model_key>/loss_weighted_ce/seed_0042/attack_to_normal_fn.csv`
    - `<model_key>/loss_weighted_ce/seed_0042/confidence_band_summary.csv`
    - `<model_key>/loss_weighted_ce/seed_0042/per_class_recall_at_threshold.csv`
    - `<model_key>/loss_weighted_ce/seed_0042/security_summary.json`
    - `<model_key>/loss_weighted_ce/seed_0042/latency_summary.json`
    - `<model_key>/loss_weighted_ce/seed_0042/train_history.json`
    - `<model_key>/loss_weighted_ce/seed_0042/checkpoint/best_<model_key>_weighted_ce_seed0042.pt`
  - evaluation dir:
    - `evaluation/final_model_comparison.csv`
    - `evaluation/aggregated_per_class_summary.csv`
    - `evaluation/latency_comparison.csv`
    - `evaluation/evaluation_summary.json`

## 7. Minimal First-Pass Final Configuration

- exact models:
  - `distilbert`
  - `minilm_l6`
  - `tinybert_bigru_attn`

- exact loss:
  - `weighted_ce`

- exact seeds:
  - `[42, 1337, 2026]`

- exact calibration handling:
  - fit `temperature_scaling` on validation logits for each seed
  - save `temperature` per seed
  - report both uncalibrated and calibrated:
    - `ECE`
    - `NLL`
    - `Brier`

- exact latency handling:
  - latency benchmarking must be a separate explicit post-training step
  - benchmark on the best saved checkpoint
  - protocol for first pass:
    - `batch_size = 1`
    - `warmup_steps = 20`
    - `measure_steps = 200`
    - report `mean/std/p50/p95/min/max`
  - do not use training workflow runtime as inference speed

- exact remaining fixed settings:
  - `TEXT_COL = "combined_payload"`
  - `LABEL_COL = "final_label"`
  - `EXPECTED_CLASSES = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]`
  - `MAX_SEQ_LEN = 128`
  - `N_EPOCHS = 4`
  - `EARLY_STOP_PATIENCE = 2`

## 8. Implementation Sequence

- edit `ml_model\evaluation\metrics.py`
  - add balanced accuracy
  - add Brier score
  - add CI helpers
  - add per-class aggregation helper
  - add full latency benchmark helper

- edit `ml_model\preprocessing\dataset_io.py`
  - only if needed for final run naming convenience
  - otherwise leave logic intact and pass `base_dir` from notebooks

- rename and rewrite `01_train_models_lightweight_screening_ch3.ipynb`
  - replace screening config with fixed confirmatory config
  - remove ALBERT from roster
  - remove single-seed logic
  - remove manual per-model cells
  - add one full multi-seed execution flow
  - add final manifest schema
  - add latency summary output
  - add per-class multi-seed aggregate output

- rename and rewrite `02_evaluate_models.ipynb`
  - point to final results base dir
  - require confirmatory-run manifest
  - remove robustness from first-pass final pipeline
  - remove loss-selection logic
  - add per-class aggregate output
  - add latency comparison output
  - add final comparison output with CI columns

- remove duplicate local modules from `Final training`
  - `metrics.py`
  - `losses.py`
  - `io.py`
  - `models.py`

- run the fixed final pipeline
  - training notebook first
  - evaluation notebook second

- verify required artifacts exist
  - per-seed metrics
  - per-seed confusion matrices
  - per-seed calibration outputs
  - per-seed latency outputs
  - aggregated multi-seed summary
  - aggregated per-class summary
  - final manifest

## 9. Final Verdict

- moderate refactor
