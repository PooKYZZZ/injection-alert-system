from __future__ import annotations

import pytest

from ml_model.retraining.dashboard_compare import (
    build_operational_proxy_metric,
    calculate_ground_truth_metrics,
)
from ml_model.retraining.dashboard_contracts import EvidenceStatus, MetricKind


def test_verified_labels_distinguish_normal_false_positives_from_attack_escapes():
    metrics = calculate_ground_truth_metrics(
        verified_labels=["Normal", "SQL Injection"],
        predictions=["SQL Injection", "Normal"],
        evaluation_split="frozen_holdout",
        evaluation_digest="a" * 64,
    )

    normal_fpr = metrics["normal_false_positive_rate"]
    attack_escape = metrics["attack_escape_rate"]

    assert normal_fpr.numerator == 1
    assert normal_fpr.denominator == 1
    assert normal_fpr.value == 1.0
    assert normal_fpr.ground_truth_source == "verified_label"
    assert normal_fpr.metric_kind is MetricKind.GROUND_TRUTH
    assert attack_escape.numerator == 1
    assert attack_escape.denominator == 1
    assert attack_escape.value == 1.0
    assert attack_escape.ground_truth_source == "verified_label"
    assert attack_escape.evaluation_split == "frozen_holdout"
    assert metrics["macro_f1"].numerator is None
    assert metrics["macro_f1"].denominator == 2


def test_triage_status_cannot_be_used_as_a_training_or_evaluation_label():
    with pytest.raises(ValueError, match="canonical"):
        calculate_ground_truth_metrics(
            verified_labels=["false_positive"],
            predictions=["Normal"],
            evaluation_digest="a" * 64,
        )


def test_missing_or_insufficient_support_is_not_a_zero_passing_metric():
    metrics = calculate_ground_truth_metrics(
        verified_labels=["Normal"],
        predictions=["Normal"],
        min_attack_support=2,
        evaluation_digest="a" * 64,
    )

    attack_escape = metrics["attack_escape_rate"]
    assert attack_escape.value is None
    assert attack_escape.evidence_status is EvidenceStatus.NOT_ENOUGH_EVIDENCE
    assert attack_escape.denominator == 0
    assert attack_escape.support_count == 0

    empty_metrics = calculate_ground_truth_metrics([], [], evaluation_digest="a" * 64)
    assert empty_metrics["normal_false_positive_rate"].value is None
    assert (
        empty_metrics["normal_false_positive_rate"].evidence_status
        is EvidenceStatus.NOT_RUN
    )


def test_operational_proxy_is_explicitly_not_ground_truth_fpr():
    proxy = build_operational_proxy_metric(numerator=3, denominator=20)

    assert proxy.value == 0.15
    assert proxy.metric_kind is MetricKind.PROXY
    assert proxy.evidence_status is EvidenceStatus.PROXY
    assert proxy.ground_truth_source == "prediction_and_action_telemetry"
    assert proxy.ground_truth_source != "verified_label"
