from __future__ import annotations

from ml_model.retraining.run_baseline import (
    _missing_baseline_metrics,
    extract_baseline_metrics,
)


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
