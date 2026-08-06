from __future__ import annotations

import hashlib
import json
from pathlib import Path

from ml_model.retraining.drift import build_batch_drift_summary
from ml_model.retraining.experiment_contract import load_experiment_config
from ml_model.retraining.integrity import validate_candidate_contract
from ml_model.retraining.prediction_artifacts import (
    join_prediction_artifacts,
    load_prediction_artifact,
    write_prediction_artifact,
)
from ml_model.retraining.statistical_evidence import build_statistical_evidence
from ml_model.training.run_contract import build_training_run_contract, contract_sha256


def _candidate_fixture(tmp_path: Path) -> tuple[Path, object, dict]:
    root = Path(__file__).resolve().parents[2]
    config = load_experiment_config(root / "ml_model/configs/retraining_20_day_v1.toml")
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    checkpoint = artifact / "best_distilbert_ckpt.pt"
    checkpoint.write_bytes(b"checkpoint")
    contract = build_training_run_contract(
        dataset_version=config.historical_dataset_version,
        preprocessing_version=config.preprocessing_version,
        model_keys=["distilbert"],
        seed_list=[2026],
        loss_keys=["weighted_ce"],
        max_seq_len=128,
        batch_size=4,
        eval_batch_size=8,
        epochs=1,
        learning_rate=3e-5,
        gradient_accumulation_steps=1,
        dataset_file_manifest_sha256="f" * 64,
        label_names=list(config.label_names),
        class_mapping={label: index for index, label in enumerate(config.label_names)},
        model_contracts={
            "distilbert": {
                "model_id": config.model_id,
                "model_revision": config.model_revision,
                "architecture": "distilbert_sequence_classification",
            }
        },
    )
    contract_hash = contract_sha256(contract)
    config_used = {
        "run_contract": contract,
        "run_contract_sha256": contract_hash,
    }
    config_path = artifact / "config_used.json"
    config_path.write_text(json.dumps(config_used), encoding="utf-8")
    manifest = {
        "label_names": list(config.label_names),
        "preprocessing_version": config.preprocessing_version,
        "model_input_hash_policy": "sha256(model_input_text)",
        "model_revision": config.model_revision,
        "tokenizer_id": config.model_id,
        "tokenizer_revision": config.model_revision,
        "confidence_thresholds": config.confidence_thresholds,
        "response_actions": config.response_actions,
        "dataset_file_manifest_sha256": "f" * 64,
        "run_contract_sha256": contract_hash,
        "local_reload_verified": True,
        "checkpoint_file": checkpoint.name,
        "checkpoint_sha256": hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
        "config_used_sha256": hashlib.sha256(config_path.read_bytes()).hexdigest(),
    }
    (artifact / "serving_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    return artifact, config, {"dataset_file_manifest_sha256": "f" * 64}


def test_batch_drift_summary_reports_request_and_source_dimensions():
    summary = build_batch_drift_summary(
        [
            {
                "model_input_text": "GET /api/users?page=1&limit=10",
                "ground_truth_label": "Normal",
                "source_type": "curated_fixture",
            },
            {
                "model_input_text": "POST /api/items?q=books",
                "ground_truth_label": "SQL Injection",
                "source_type": "curated_fixture",
            },
        ],
        [{"reason": "unknown label: Other"}],
    )

    assert summary["http_method_distribution"] == {"GET": 1, "POST": 1}
    assert summary["query_parameter_frequency"] == {"limit": 1, "page": 1, "q": 1}
    assert summary["attack_category_distribution"] == {
        "Normal": 1,
        "SQL Injection": 1,
    }
    assert summary["validation_error_categories"] == {"unknown_label": 1}
    assert summary["confidence_distribution"]["status"] == "NOT_AVAILABLE"


def test_statistical_evidence_is_explicitly_not_run_without_paired_predictions():
    evidence = build_statistical_evidence({})

    assert evidence["status"] == "NOT_RUN"
    assert evidence["reason"] == "paired_predictions_not_supplied"


def test_statistical_evidence_reports_paired_errors_and_mcnemar_result():
    evidence = build_statistical_evidence(
        {
            "y_true": ["Normal", "SQL Injection", "Normal", "SQL Injection"],
            "baseline_predictions": [
                "Normal",
                "Normal",
                "SQL Injection",
                "SQL Injection",
            ],
            "candidate_predictions": [
                "SQL Injection",
                "SQL Injection",
                "SQL Injection",
                "SQL Injection",
            ],
        }
    )

    assert evidence["status"] == "COMPUTED"
    assert evidence["paired_error_counts"] == {
        "baseline_only": 1,
        "candidate_only": 1,
        "both_correct": 1,
        "both_wrong": 1,
    }
    assert evidence["mcnemar_exact"]["discordant_total"] == 2


def _prediction_records(labels: list[str], *, prefix: str = "sample") -> list[dict]:
    return [
        {
            "sample_id": f"{prefix}-{index}",
            "split": "golden",
            "y_true": label,
            "prediction": label if index % 2 == 0 else "Normal",
            "confidence": 0.91,
            "confidence_tier": "CRITICAL",
            "response_action": "BLOCKED",
        }
        for index, label in enumerate(labels)
    ]


def test_prediction_artifacts_are_provenance_bound_and_join_by_stable_ids(
    tmp_path: Path,
):
    baseline_path = tmp_path / "baseline_predictions.json"
    candidate_path = tmp_path / "candidate_predictions.json"
    baseline = write_prediction_artifact(
        baseline_path,
        _prediction_records(["Normal", "SQL Injection"]),
        model_version="baseline-v1",
        dataset_version="dataset-v1",
        golden_version="golden-v1",
        golden_manifest_sha256="d" * 64,
        model_artifact_sha256="a" * 64,
    )
    write_prediction_artifact(
        candidate_path,
        _prediction_records(["Normal", "SQL Injection"]),
        model_version="candidate-v1",
        dataset_version="dataset-v1",
        golden_version="golden-v1",
        golden_manifest_sha256="d" * 64,
        model_artifact_sha256="b" * 64,
    )

    loaded = load_prediction_artifact(baseline_path)
    joined = join_prediction_artifacts(baseline_path, candidate_path)
    evidence = build_statistical_evidence(
        {"baseline_artifact": baseline_path, "candidate_artifact": candidate_path}
    )

    assert baseline["provenance"]["dataset_version"] == "dataset-v1"
    assert loaded["records"][0]["sample_id"] == "sample-0"
    assert joined["sample_ids"] == ["sample-0", "sample-1"]
    assert evidence["status"] == "COMPUTED"
    assert evidence["provenance"]["golden_version"] == "golden-v1"
    assert evidence["provenance"]["golden_manifest_sha256"] == "d" * 64
    assert evidence["provenance"]["baseline_model_artifact_sha256"] == "a" * 64
    assert evidence["provenance"]["candidate_model_artifact_sha256"] == "b" * 64
    assert evidence["significance_claim"] == "NOT_CLAIMED"


def test_prediction_artifacts_reject_mismatched_ids_and_provenance(tmp_path: Path):
    baseline_path = tmp_path / "baseline.json"
    candidate_path = tmp_path / "candidate.json"
    write_prediction_artifact(
        baseline_path,
        _prediction_records(["Normal", "SQL Injection"]),
        model_version="baseline-v1",
        dataset_version="dataset-v1",
        golden_version="golden-v1",
        golden_manifest_sha256="d" * 64,
        model_artifact_sha256="a" * 64,
    )
    write_prediction_artifact(
        candidate_path,
        _prediction_records(["Normal", "SQL Injection"], prefix="other"),
        model_version="candidate-v1",
        dataset_version="dataset-v1",
        golden_version="golden-v1",
        golden_manifest_sha256="d" * 64,
        model_artifact_sha256="b" * 64,
    )
    mismatch = build_statistical_evidence(
        {"baseline_artifact": baseline_path, "candidate_artifact": candidate_path}
    )
    assert mismatch["status"] == "INVALID"
    assert mismatch["reason"] == "prediction_ids_do_not_match"

    write_prediction_artifact(
        candidate_path,
        _prediction_records(["Normal", "SQL Injection"]),
        model_version="candidate-v1",
        dataset_version="dataset-v2",
        golden_version="golden-v1",
        golden_manifest_sha256="d" * 64,
        model_artifact_sha256="b" * 64,
    )
    provenance_mismatch = build_statistical_evidence(
        {"baseline_artifact": baseline_path, "candidate_artifact": candidate_path}
    )
    assert provenance_mismatch["status"] == "INVALID"
    assert provenance_mismatch["reason"] == "prediction_provenance_mismatch"

    write_prediction_artifact(
        candidate_path,
        _prediction_records(["Normal", "SQL Injection"]),
        model_version="candidate-v1",
        dataset_version="dataset-v1",
        golden_version="golden-v1",
        golden_manifest_sha256="e" * 64,
        model_artifact_sha256="b" * 64,
    )
    golden_manifest_mismatch = build_statistical_evidence(
        {"baseline_artifact": baseline_path, "candidate_artifact": candidate_path}
    )
    assert golden_manifest_mismatch["status"] == "INVALID"
    assert golden_manifest_mismatch["reason"] == "prediction_provenance_mismatch"


def test_statistical_evidence_rejects_malformed_arrays_and_keeps_smoke_non_thesis(
    tmp_path: Path,
):
    assert (
        build_statistical_evidence(
            {"y_true": ["Normal"], "baseline_predictions": ["Normal"]}
        )["status"]
        == "NOT_RUN"
    )
    assert (
        build_statistical_evidence(
            {
                "y_true": ["Normal"],
                "baseline_predictions": ["Normal"],
                "candidate_predictions": [],
            }
        )["status"]
        == "INVALID"
    )

    smoke = build_statistical_evidence({"mode": "synthetic_orchestration_smoke"})
    assert smoke["status"] == "NOT_RUN"
    assert smoke["thesis_evidence"] is False


def test_candidate_contract_gate_reports_all_locked_identity_checks(tmp_path: Path):
    artifact, config, snapshot_manifest = _candidate_fixture(tmp_path)

    result = validate_candidate_contract(
        config=config,
        artifact_dir=artifact,
        snapshot_manifest=snapshot_manifest,
    )

    assert result.passed is True
    assert result.checks["label_mapping_unchanged"] is True
    assert result.checks["dataset_hash_verified"] is True


def test_candidate_contract_gate_rejects_policy_drift(tmp_path: Path):
    artifact, config, snapshot_manifest = _candidate_fixture(tmp_path)
    manifest_path = artifact / "serving_manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["response_actions"] = {**config.response_actions, "high": "ALLOWED"}
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    result = validate_candidate_contract(
        config=config,
        artifact_dir=artifact,
        snapshot_manifest=snapshot_manifest,
    )

    assert result.passed is False
    assert "action_mapping_unchanged" in result.failures
