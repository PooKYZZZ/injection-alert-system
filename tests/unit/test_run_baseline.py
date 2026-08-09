from __future__ import annotations

import json
from pathlib import Path

from ml_model.evaluation.golden_controls import load_golden_controls
from ml_model.retraining.run_baseline import (
    _missing_baseline_metrics,
    build_baseline_report,
    evaluate_baseline_gate,
    extract_baseline_metrics,
)


def _complete_metrics() -> dict[str, object]:
    return {
        "normal_false_positive_rate": 0.01,
        "attack_escape_rate": 0.02,
        "macro_f1": 0.91,
        "normal_recall": 0.99,
        "supported_attack_recall": {
            "Code Injection": 0.9,
            "Other Attacks": 0.9,
            "SQL Injection": 0.9,
        },
    }


def test_baseline_gate_requires_complete_operational_controls():
    common = {
        "metrics": _complete_metrics(),
        "label_names": (
            "Code Injection",
            "Normal",
            "Other Attacks",
            "SQL Injection",
        ),
        "service_loaded": True,
        "golden_passed": True,
        "reload_verified": True,
    }

    assert evaluate_baseline_gate(**common)["passed"] is True
    for field in ("service_loaded", "golden_passed", "reload_verified"):
        failed = dict(common, **{field: False})
        assert evaluate_baseline_gate(**failed)["passed"] is False

    incomplete = dict(_complete_metrics())
    incomplete["attack_escape_rate"] = None
    failed = dict(common, metrics=incomplete)
    assert evaluate_baseline_gate(**failed)["passed"] is False


def test_baseline_metric_extraction_reads_security_rates_from_summary_metrics():
    metrics = extract_baseline_metrics(
        {"macro avg": {"f1-score": 0.91}, "Normal": {"recall": 0.99}},
        summary_metrics={
            "normal_false_positive_rate": 0.001,
            "attack_escape_rate": 0.002,
            "test_macro_f1": 0.903,
        },
    )

    assert metrics["normal_false_positive_rate"] == 0.001
    assert metrics["attack_escape_rate"] == 0.002
    assert metrics["macro_f1"] == 0.91


def test_baseline_with_unloadable_artifact_remains_requires_laptop(tmp_path: Path):
    artifact_dir = tmp_path / "artifact"
    artifact_dir.mkdir()
    report = build_baseline_report(
        artifact_dir=artifact_dir,
        config_path=Path("ml_model/configs/retraining_20_day_v1.toml"),
        output_path=tmp_path / "baseline.json",
    )

    assert report["status"] == "PARTIAL"
    assert report["baseline_status"] == "REQUIRES_LAPTOP"
    assert report["model_quality_conclusion"] == "NOT_PERMITTED"
    assert report["baseline_gate"]["checks"]["model_loaded"] is False
    assert report["prediction_artifact_status"] == "NOT_WRITTEN"


def test_baseline_metric_extraction_preserves_unknown_operational_rates():
    metrics = extract_baseline_metrics(
        {
            "macro avg": {"f1-score": 0.91},
            "Normal": {"recall": 0.99},
            "SQL Injection": {"recall": 0.98},
        }
    )

    assert metrics["macro_f1"] == 0.91
    assert metrics["normal_recall"] == 0.99
    assert metrics["supported_attack_recall"] == {"SQL Injection": 0.98}
    assert metrics["normal_false_positive_rate"] is None
    assert metrics["attack_escape_rate"] is None


def test_baseline_requires_every_supported_attack_recall():
    missing = _missing_baseline_metrics(
        {
            "normal_false_positive_rate": 0.01,
            "attack_escape_rate": 0.02,
            "macro_f1": 0.98,
            "normal_recall": 0.99,
            "supported_attack_recall": {"SQL Injection": 0.97},
        },
        ("Code Injection", "Normal", "Other Attacks", "SQL Injection"),
    )

    assert missing == ["supported_attack_recall:Code Injection,Other Attacks"]


def test_baseline_report_separates_target_route_and_legacy_regression(
    tmp_path: Path, monkeypatch
):
    root = Path(__file__).resolve().parents[2]
    controls = load_golden_controls(
        root
        / "data/experiments/retraining_20_day_v1/golden/golden-v2/golden_manifest.json"
    )
    expected = {
        case["model_input_text"]: case["expected_label"] for case in controls.cases
    }

    class FakeModelService:
        loaded = True
        model_version = "baseline-test"

        def __init__(self, _settings):
            pass

        def predict(self, request_text: str) -> dict[str, object]:
            return {"prediction": expected[request_text], "confidence": 0.99}

    from web_app.services import model_service

    monkeypatch.setattr(model_service, "ModelService", FakeModelService)
    artifact = tmp_path / "artifact"
    artifact.mkdir()
    (artifact / "serving_manifest.json").write_text(
        json.dumps({"model_version": "baseline-test", "local_reload_verified": True}),
        encoding="utf-8",
    )
    (artifact / "eval_report.json").write_text(
        json.dumps(
            {
                "macro avg": {"f1-score": 0.99},
                "Normal": {"recall": 1.0},
                "per_class": {
                    "Code Injection": {"recall": 1.0},
                    "Other Attacks": {"recall": 1.0},
                    "SQL Injection": {"recall": 1.0},
                },
            }
        ),
        encoding="utf-8",
    )
    (artifact / "summary_metrics.json").write_text(
        json.dumps(
            {
                "normal_false_positive_rate": 0.0,
                "attack_escape_rate": 0.0,
                "test_macro_f1": 0.99,
            }
        ),
        encoding="utf-8",
    )

    report = build_baseline_report(
        artifact_dir=artifact,
        config_path=root / "ml_model/configs/retraining_20_day_v1.toml",
        output_path=tmp_path / "baseline.json",
    )

    assert report["golden"]["passed"] is True
    assert report["target_route_controls"]["route"] == "/records/search"
    assert report["target_route_controls"]["case_count"] == 28
    assert report["target_route_controls"]["passed"] is True
    assert report["legacy_regression"]["case_id"] == (
        "legacy-api-users-pagination-regression"
    )
    assert report["exact_pagination"]["case_id"] == (
        "legacy-api-users-pagination-regression"
    )
