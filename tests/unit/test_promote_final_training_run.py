import json
from pathlib import Path

import pytest
import torch

from ml_model.export.promote_final_training_run import (
    PromotionError,
    archive_existing_run,
    build_model_card,
    build_config_used,
    build_eval_report,
    build_provenance_payload,
    create_fresh_active_run_dir,
    extract_calibration_temperature,
    extract_state_dict_checkpoint,
    parse_args,
    promote_final_training_run,
    restore_archived_run,
    run_packager,
    validate_final_training_source,
    validate_label_names,
    write_eval_provenance_files,
)


def make_minimal_final_training_fixture(source_dir: Path) -> Path:
    source_dir.mkdir(parents=True, exist_ok=True)
    (source_dir / "config_metadata.json").write_text(
        json.dumps(
            {
                "model_key": "distilbert",
                "model_id": "distilbert-base-uncased",
                "dataset_version": "v3_907k_cleaned",
                "max_seq_len": 128,
                "seed": 2026,
            }
        ),
        encoding="utf-8",
    )
    (source_dir / "summary_metrics.json").write_text(
        json.dumps(
            {
                "test_accuracy": 0.99,
                "test_macro_f1": 0.98,
                "test_weighted_f1": 0.991,
            }
        ),
        encoding="utf-8",
    )
    (source_dir / "per_class_metrics.json").write_text(
        json.dumps(
            [
                {
                    "label_name": "Code Injection",
                    "precision": 0.95,
                    "recall": 1.0,
                    "f1": 0.97,
                    "support": 837,
                },
                {
                    "label_name": "Normal",
                    "precision": 0.99,
                    "recall": 0.99,
                    "f1": 0.99,
                    "support": 3658,
                },
                {
                    "label_name": "Other Attacks",
                    "precision": 0.98,
                    "recall": 0.99,
                    "f1": 0.99,
                    "support": 6035,
                },
                {
                    "label_name": "SQL Injection",
                    "precision": 0.99,
                    "recall": 0.99,
                    "f1": 0.99,
                    "support": 8975,
                },
            ]
        ),
        encoding="utf-8",
    )
    (source_dir / "calibration.json").write_text(
        json.dumps({"temperature": 1.3780944347381592}),
        encoding="utf-8",
    )

    checkpoint_dir = source_dir / "checkpoint"
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"model_state_dict": {"encoder.weight": torch.tensor([1.0])}},
        checkpoint_dir / "best_distilbert_weighted_ce_seed2026.pt",
    )
    return source_dir


def make_existing_packaged_run_fixture(run_dir: Path) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "serving_manifest.json").write_text("{}", encoding="utf-8")
    return run_dir


def test_extracts_raw_model_state_dict_from_notebook_checkpoint(tmp_path: Path):
    source = tmp_path / "best_distilbert_weighted_ce_seed2026.pt"
    torch.save(
        {
            "model_state_dict": {"encoder.weight": torch.tensor([1.0])},
            "epoch": 4,
            "best_val_macro_f1": 0.99,
        },
        source,
    )

    target = tmp_path / "best_distilbert_ckpt.pt"
    extract_state_dict_checkpoint(source, target)

    saved = torch.load(target, map_location="cpu", weights_only=True)
    assert saved == {"encoder.weight": torch.tensor([1.0])}


def test_checkpoint_extraction_uses_weights_only_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = tmp_path / "source.pt"
    target = tmp_path / "target.pt"
    calls: list[dict[str, object]] = []

    def safe_load(path, **kwargs):
        calls.append(kwargs)
        return {"model_state_dict": {"encoder.weight": torch.tensor([1.0])}}

    monkeypatch.setattr(
        "ml_model.export.promote_final_training_run.torch.load",
        safe_load,
    )

    extract_state_dict_checkpoint(source, target)

    assert calls == [{"map_location": "cpu", "weights_only": True}]


def test_extract_state_dict_checkpoint_normalizes_final_training_keys_for_packager(
    tmp_path: Path,
):
    source = tmp_path / "best_distilbert_weighted_ce_seed2026.pt"
    torch.save(
        {
            "model_state_dict": {
                "encoder.embeddings.word_embeddings.weight": torch.tensor([1.0]),
                "classifier_dense.weight": torch.tensor([2.0]),
                "classifier_dense.bias": torch.tensor([3.0]),
                "output.weight": torch.tensor([4.0]),
                "output.bias": torch.tensor([5.0]),
                "layer_norm.weight": torch.tensor([6.0]),
                "layer_norm.bias": torch.tensor([7.0]),
            }
        },
        source,
    )

    target = tmp_path / "best_distilbert_ckpt.pt"
    extract_state_dict_checkpoint(source, target, normalize_for_packager=True)

    saved = torch.load(target, map_location="cpu", weights_only=True)
    assert "distilbert.embeddings.word_embeddings.weight" in saved
    assert "pre_classifier.weight" in saved
    assert "pre_classifier.bias" in saved
    assert "classifier.weight" in saved
    assert "classifier.bias" in saved
    assert "layer_norm.weight" not in saved
    assert "layer_norm.bias" not in saved


def test_builds_config_used_from_final_training_metadata():
    payload = build_config_used(
        config_metadata={
            "model_key": "distilbert",
            "model_id": "distilbert-base-uncased",
            "dataset_version": "v3_907k_cleaned",
            "max_seq_len": 128,
            "seed": 2026,
        },
        model_version="distilbert_v3_907k_cleaned_20260312_133755",
    )

    assert payload["model_key"] == "distilbert"
    assert payload["model_id"] == "distilbert-base-uncased"
    assert payload["dataset_version"] == "v3_907k_cleaned"
    assert payload["max_seq_len"] == 128
    assert payload["label_names"] == [
        "Code Injection",
        "Normal",
        "Other Attacks",
        "SQL Injection",
    ]


def test_builds_eval_report_from_summary_and_per_class_metrics():
    eval_report = build_eval_report(
        summary_metrics={
            "test_accuracy": 0.99,
            "test_macro_f1": 0.98,
            "test_weighted_f1": 0.991,
        },
        per_class_metrics=[
            {
                "label_name": "Code Injection",
                "precision": 0.95,
                "recall": 1.0,
                "f1": 0.97,
                "support": 837,
            },
            {
                "label_name": "Normal",
                "precision": 0.99,
                "recall": 0.99,
                "f1": 0.99,
                "support": 3658,
            },
            {
                "label_name": "Other Attacks",
                "precision": 0.98,
                "recall": 0.99,
                "f1": 0.99,
                "support": 6035,
            },
            {
                "label_name": "SQL Injection",
                "precision": 0.99,
                "recall": 0.99,
                "f1": 0.99,
                "support": 8975,
            },
        ],
    )

    assert eval_report["accuracy"] == 0.99
    assert eval_report["macro avg"]["f1-score"] == 0.98
    assert eval_report["Code Injection"]["support"] == 837.0


def test_preflight_fails_when_required_final_training_files_are_missing(tmp_path: Path):
    source_dir = tmp_path / "seed_2026"
    source_dir.mkdir()

    with pytest.raises(PromotionError, match="Missing required final-training file"):
        validate_final_training_source(source_dir)


def test_preflight_fails_when_label_names_do_not_match_serving_contract():
    with pytest.raises(PromotionError, match="label names"):
        validate_label_names(["Normal", "Code Injection", "Other Attacks", "SQL Injection"])


def test_preflight_fails_when_calibration_temperature_is_missing():
    with pytest.raises(PromotionError, match="temperature"):
        extract_calibration_temperature({"method": "temperature_scaling"})


def test_archive_existing_run_moves_active_folder_to_archive_location(tmp_path: Path):
    active = tmp_path / "staging" / "distilbert_v3_907k_cleaned_20260312_133755"
    active.mkdir(parents=True)
    (active / "serving_manifest.json").write_text("{}", encoding="utf-8")

    archive_root = tmp_path / "archive"
    archived_path = archive_existing_run(
        active_run_dir=active,
        archive_root=archive_root,
        archive_suffix="pre_20260420",
    )

    assert not active.exists()
    assert archived_path.exists()
    assert (archived_path / "serving_manifest.json").exists()


def test_archive_existing_run_refuses_when_archive_target_already_exists(tmp_path: Path):
    active = tmp_path / "staging" / "distilbert_v3_907k_cleaned_20260312_133755"
    active.mkdir(parents=True)
    archive_root = tmp_path / "archive"
    existing = archive_root / "distilbert_v3_907k_cleaned_20260312_133755_pre_20260420"
    existing.mkdir(parents=True)

    with pytest.raises(PromotionError, match="already exists"):
        archive_existing_run(
            active_run_dir=active,
            archive_root=archive_root,
            archive_suffix="pre_20260420",
        )


def test_create_fresh_active_run_directory_starts_empty(tmp_path: Path):
    active = tmp_path / "staging" / "distilbert_v3_907k_cleaned_20260312_133755"
    active.mkdir(parents=True)

    with pytest.raises(FileExistsError):
        create_fresh_active_run_dir(active)


def test_build_provenance_payload_records_checkpoint_archive_and_gates():
    checkpoint_sha256 = "a" * 64
    payload = build_provenance_payload(
        model_name="distilbert-injection-detector",
        promoted_version="distilbert_v3_907k_cleaned_20260312_133755",
        checkpoint_sha256=checkpoint_sha256,
        archived_path="ml_model/model_registry/archive/run_old",
        repo_commit="deadbeef",
        calibration_temperature=1.3780944347381592,
        validation_gates={
            "artifact_packaging_pipeline_passed": True,
            "local_reload_validated": True,
            "quality_gates_passed": False,
        },
    )

    assert payload["checkpoint_identity"]["checkpoint_sha256"] == checkpoint_sha256
    assert payload["previous_version_archived_to"] == "ml_model/model_registry/archive/run_old"
    assert payload["artifact_packaging_ready"] is True
    assert payload["quality_gates_passed"] is False
    assert payload["ready_for_promotion"] is False


def test_build_provenance_payload_requires_packaging_reload_and_quality_gates():
    common = {
        "model_name": "distilbert-injection-detector",
        "promoted_version": "distilbert_test",
        "checkpoint_sha256": "a" * 64,
        "archived_path": "ml_model/model_registry/archive/run_old",
        "repo_commit": "deadbeef",
        "calibration_temperature": 1.2,
        "label_names": [
            "Code Injection",
            "Normal",
            "Other Attacks",
            "SQL Injection",
        ],
    }

    ready = build_provenance_payload(
        **common,
        validation_gates={
            "source_validation_passed": True,
            "artifact_packaging_pipeline_passed": True,
            "local_reload_validated": True,
            "quality_gates_passed": True,
        },
    )
    missing_reload = build_provenance_payload(
        **common,
        validation_gates={
            "source_validation_passed": True,
            "artifact_packaging_pipeline_passed": True,
            "local_reload_validated": False,
            "quality_gates_passed": True,
        },
    )

    assert ready["ready_for_promotion"] is True
    assert missing_reload["artifact_packaging_ready"] is False
    assert missing_reload["ready_for_promotion"] is False

    missing_source_validation = build_provenance_payload(
        **common,
        validation_gates={
            "artifact_packaging_pipeline_passed": True,
            "local_reload_validated": True,
            "quality_gates_passed": True,
        },
    )
    missing_checksum = build_provenance_payload(
        **{**common, "checkpoint_sha256": ""},
        validation_gates={
            "source_validation_passed": True,
            "artifact_packaging_pipeline_passed": True,
            "local_reload_validated": True,
            "quality_gates_passed": True,
        },
    )

    assert missing_source_validation["ready_for_promotion"] is False
    assert missing_checksum["checkpoint_hash_recorded"] is False
    assert missing_checksum["ready_for_promotion"] is False


def test_eval_provenance_does_not_claim_quality_readiness_without_gates(
    tmp_path: Path,
):
    eval_dir = write_eval_provenance_files(
        eval_root=tmp_path,
        model_key="distilbert",
        run_dir_name="distilbert_test",
        temperature=1.2,
        repo_commit="deadbeef",
        dataset_version="v3",
        artifact_packaging_pipeline_passed=True,
        local_reload_validated=True,
        quality_gates_passed=False,
    )

    summary = json.loads(
        (eval_dir / "promotion_summary.json").read_text(encoding="utf-8")
    )
    model_summary = summary["promotion_summary"]["distilbert"]
    assert model_summary["artifact_packaging_ready"] is True
    assert model_summary["quality_gates_passed"] is False
    assert model_summary["ready_for_promotion"] is False


def test_build_model_card_mentions_metrics_and_version_history():
    text = build_model_card(
        model_version="distilbert_v3_907k_cleaned_20260312_133755",
        archived_version="distilbert_v3_907k_cleaned_20260312_133755_pre_20260420",
        summary_metrics={"test_macro_f1": 0.9892772003963323},
        label_names=["Code Injection", "Normal", "Other Attacks", "SQL Injection"],
    )

    assert "test_macro_f1" in text
    assert "Version history" in text
    assert "Code Injection" in text


def test_run_packager_invokes_existing_package_serving_artifact(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
):
    calls: list[dict[str, object]] = []

    def fake_package_serving_artifact(**kwargs):
        calls.append(kwargs)
        return tmp_path / "staging" / "distilbert_v3_907k_cleaned_20260312_133755"

    monkeypatch.setattr(
        "ml_model.export.promote_final_training_run.package_serving_artifact",
        fake_package_serving_artifact,
    )

    run_packager(
        model_key="distilbert",
        run_dir_name="distilbert_v3_907k_cleaned_20260312_133755",
        notes=None,
    )

    assert calls[0]["model_key"] == "distilbert"
    assert calls[0]["run_dir_name"] == "distilbert_v3_907k_cleaned_20260312_133755"
    assert calls[0]["strict"] is True


def test_restore_archive_reinstates_old_active_run_after_failure(tmp_path: Path):
    archive = tmp_path / "archive" / "run_old"
    archive.mkdir(parents=True)
    (archive / "serving_manifest.json").write_text("{}", encoding="utf-8")
    active = tmp_path / "staging" / "distilbert_v3_907k_cleaned_20260312_133755"

    restore_archived_run(archived_run_dir=archive, active_run_dir=active)

    assert active.exists()
    assert not archive.exists()


def test_promote_final_training_run_executes_archive_convert_package_and_verify(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source_dir = make_minimal_final_training_fixture(tmp_path / "source")
    active_run_dir = make_existing_packaged_run_fixture(
        tmp_path
        / "ml_model"
        / "model_registry"
        / "staging"
        / "distilbert_v3_907k_cleaned_20260312_133755"
    )

    monkeypatch.setattr(
        "ml_model.export.promote_final_training_run.validate_local_reload",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "ml_model.export.promote_final_training_run.run_packager",
        lambda **kwargs: active_run_dir,
    )

    result = promote_final_training_run(
        source_dir=source_dir,
        active_run_dir=active_run_dir,
        archive_root=tmp_path / "ml_model" / "model_registry" / "archive",
        repo_root=tmp_path,
        checkpoint_filename="best_distilbert_weighted_ce_seed2026.pt",
    )

    assert result.active_run_dir.exists()
    assert (result.active_run_dir / "provenance.json").exists()
    assert (result.active_run_dir / "MODEL_CARD.md").exists()


def test_promote_final_training_run_does_not_archive_or_write_when_preflight_fails(
    tmp_path: Path,
):
    source_dir = tmp_path / "source"
    source_dir.mkdir()
    active_run_dir = tmp_path / "staging" / "distilbert_v3_907k_cleaned_20260312_133755"
    active_run_dir.mkdir(parents=True)

    with pytest.raises(PromotionError):
        promote_final_training_run(
            source_dir=source_dir,
            active_run_dir=active_run_dir,
            archive_root=tmp_path / "archive",
            repo_root=tmp_path,
            checkpoint_filename="best_distilbert_weighted_ce_seed2026.pt",
        )

    assert active_run_dir.exists()


def test_parse_args_supports_explicit_source_active_archive_and_dry_run():
    args = parse_args(
        [
            "--source-run-dir",
            "G:/repo/ml_model/notebooks/.../seed_2026",
            "--active-run-dir",
            "G:/repo/ml_model/model_registry/staging/distilbert_v3_907k_cleaned_20260312_133755",
            "--archive-root",
            "G:/repo/ml_model/model_registry/archive",
            "--checkpoint-filename",
            "best_distilbert_weighted_ce_seed2026.pt",
            "--dry-run",
        ]
    )
    assert args.dry_run is True


def test_dry_run_reports_actions_without_changing_disk(tmp_path: Path):
    source_dir = make_minimal_final_training_fixture(tmp_path / "source")
    active_run_dir = make_existing_packaged_run_fixture(
        tmp_path / "staging" / "distilbert_v3_907k_cleaned_20260312_133755"
    )

    plan = promote_final_training_run(
        source_dir=source_dir,
        active_run_dir=active_run_dir,
        archive_root=tmp_path / "archive",
        repo_root=tmp_path,
        checkpoint_filename="best_distilbert_weighted_ce_seed2026.pt",
        dry_run=True,
    )

    assert active_run_dir.exists()
    assert plan.dry_run is True
