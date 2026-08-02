from __future__ import annotations

from pathlib import Path


def _source(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_training_uses_computed_split_hygiene_evidence():
    source = _source("ml_model/training/train.py")

    assert "build_split_hygiene_evidence" in source
    assert '"source": "upstream_verified_dataset_metadata"' not in source
    assert '"zero_cross_split_overlap": True' not in source


def test_resume_state_is_restored_outside_checkpoint_load_exception_handler():
    source = _source("ml_model/training/confirmatory_runner.py")

    incompatible_raise = source.index(
        'f"Resume checkpoint is incompatible with the selected model: {resume_path}"'
    )
    best_epoch_restore = source.index('best_epoch = int(resume_payload.get("best_epoch", 0))')

    assert best_epoch_restore > incompatible_raise
    assert "\n                except Exception as exc:\n                    raise RuntimeError(" in source
    assert "\n                best_epoch = int(resume_payload.get(\"best_epoch\", 0))" in source


def test_training_loads_local_checkpoints_with_explicit_trusted_policy():
    source = _source("ml_model/training/confirmatory_runner.py")

    assert "weights_only=False" in source


def test_seed_summary_emits_balanced_accuracy_and_brier_metrics():
    source = _source("ml_model/training/confirmatory_runner.py")

    for key in (
        '"val_balanced_accuracy"',
        '"val_brier_uncalibrated"',
        '"val_brier_calibrated"',
        '"test_balanced_accuracy"',
        '"test_brier_uncalibrated"',
        '"test_brier_calibrated"',
    ):
        assert key in source


def test_threshold_security_artifacts_use_calibrated_probabilities():
    source = _source("ml_model/training/confirmatory_runner.py")

    assert 'probs=test_cal["probs"]' in source
    assert 'confidence_band_summary_frame(test_labels, test_uncal["preds"], test_cal["probs"])' in source


def test_zero_completed_aggregates_raise_even_with_partial_aggregation():
    source = _source("ml_model/training/confirmatory_runner.py")

    assert "No completed model/loss aggregates available" in source
    assert "if all_loss_df.empty:" in source
    assert "and not self.ctx.allow_partial_aggregation" not in source


def test_partial_accumulation_window_uses_actual_microbatch_count():
    source = _source("ml_model/training/confirmatory_runner.py")

    assert "actual_accum_steps" in source
    assert "loss = criterion(logits, labels) / actual_accum_steps" in source


def test_model_resource_cache_is_evicted_after_model_run():
    source = _source("ml_model/training/confirmatory_runner.py")

    assert "self.model_resource_cache.pop(model_key, None)" in source


def test_training_can_find_latest_resumable_default_run_directory():
    source = _source("ml_model/training/train.py")

    assert "find_latest_resumable_run_dir" in source
    assert "last_*.pt" in source


def test_training_persists_evaluated_test_rows_for_followup_evaluation():
    source = _source("ml_model/training/train.py")

    assert 'evaluated_test_rows.csv' in source
    assert 'combined_payload' in source
    assert 'final_label' in source


def test_tinybert_bigru_uses_packed_sequences_for_padding():
    source = _source("ml_model/training/model_factory.py")

    assert "pack_padded_sequence" in source
    assert "pad_packed_sequence" in source
    assert "lengths = attention_mask.sum" in source
