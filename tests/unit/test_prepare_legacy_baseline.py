from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from ml_model.retraining.prepare_legacy_baseline import (
    LegacyBaselineError,
    build_legacy_summary,
)


def test_build_legacy_summary_links_metrics_to_exact_staged_artifact(tmp_path: Path):
    artifact = tmp_path / "staged"
    evaluation = tmp_path / "eval"
    artifact.mkdir()
    evaluation.mkdir()

    checkpoint = artifact / "best_distilbert_ckpt.pt"
    checkpoint.write_bytes(b"legacy-checkpoint")
    checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    manifest = {
        "model_version": "legacy-distilbert",
        "model_key": "distilbert",
        "temperature": 0.596868,
        "checkpoint_file": checkpoint.name,
        "checkpoint_sha256": checkpoint_hash,
        "calibration_eval_run_dir": str(
            Path("C:/original-training-host") / evaluation.name
        ),
        "local_reload_verified": True,
    }
    (artifact / "serving_manifest.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    (artifact / "eval_report.json").write_text(
        json.dumps(
            {
                "Normal": {"recall": 0.998},
                "Code Injection": {"recall": 0.99},
                "Other Attacks": {"recall": 0.98},
                "SQL Injection": {"recall": 0.97},
                "macro avg": {"recall": 0.98},
                "weighted avg": {"recall": 0.99},
            }
        ),
        encoding="utf-8",
    )
    evaluation_file = evaluation / "eval_results_distilbert_calibrated.json"
    evaluation_file.write_text(
        json.dumps(
            {
                "model": "distilbert",
                "temperature": 0.596868,
                "accuracy": 0.992,
                "macro_f1": 0.988,
                "weighted_f1": 0.991,
                "ece": 0.004,
                "operational": {
                    "benign_false_positive_rate": 0.002,
                    "attack_detection_rate": 0.997,
                },
            }
        ),
        encoding="utf-8",
    )

    output = tmp_path / "summary_metrics.json"
    summary = build_legacy_summary(
        artifact_dir=artifact,
        evaluation_file=evaluation_file,
        output_path=output,
    )

    assert summary["legacy_baseline"] is True
    assert summary["provenance_status"] == "legacy_evaluation_capture"
    assert summary["normal_false_positive_rate"] == pytest.approx(0.002)
    assert summary["attack_escape_rate"] == pytest.approx(0.003)
    assert summary["supported_attack_recall"] == {
        "Code Injection": 0.99,
        "Other Attacks": 0.98,
        "SQL Injection": 0.97,
    }
    assert json.loads(output.read_text(encoding="utf-8"))["checkpoint_sha256"] == (
        checkpoint_hash
    )


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -0.01, 1.01])
def test_build_legacy_summary_rejects_invalid_probability_metrics(
    tmp_path: Path, value: float
):
    artifact = tmp_path / "staged"
    evaluation = tmp_path / "eval"
    artifact.mkdir()
    evaluation.mkdir()
    checkpoint = artifact / "best_distilbert_ckpt.pt"
    checkpoint.write_bytes(b"legacy-checkpoint")
    checkpoint_hash = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    (artifact / "serving_manifest.json").write_text(
        json.dumps(
            {
                "model_key": "distilbert",
                "temperature": 1.0,
                "checkpoint_file": checkpoint.name,
                "checkpoint_sha256": checkpoint_hash,
                "calibration_eval_run_dir": str(evaluation.resolve()),
            }
        ),
        encoding="utf-8",
    )
    (artifact / "eval_report.json").write_text(
        json.dumps({"Normal": {"recall": 1.0}, "SQL Injection": {"recall": 1.0}}),
        encoding="utf-8",
    )
    evaluation_file = evaluation / "evaluation.json"
    evaluation_file.write_text(
        json.dumps(
            {
                "model": "distilbert",
                "temperature": 1.0,
                "accuracy": 1.0,
                "macro_f1": 1.0,
                "weighted_f1": 1.0,
                "ece": 0.0,
                "operational": {
                    "benign_false_positive_rate": value,
                    "attack_detection_rate": 1.0,
                },
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(LegacyBaselineError, match="finite|between"):
        build_legacy_summary(
            artifact_dir=artifact,
            evaluation_file=evaluation_file,
            output_path=tmp_path / "summary.json",
        )
