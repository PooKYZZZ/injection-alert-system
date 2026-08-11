from __future__ import annotations

from ml_model.retraining.dashboard_compare import compare_candidate_metrics
from ml_model.retraining.dashboard_contracts import (
    EvaluationProvenance,
    EvidenceStatus,
    GateStatus,
    MetricDefinition,
    MetricKind,
    ModelReference,
)


def _metric(
    name: str,
    value: float | None,
    *,
    numerator: int | None = None,
    denominator: int | None = 100,
    support_count: int | None = 100,
    evidence_status: EvidenceStatus = EvidenceStatus.VERIFIED,
    metric_kind: MetricKind = MetricKind.GROUND_TRUTH,
    evaluation_digest: str = "c" * 64,
    evaluation_split: str = "frozen_holdout",
) -> MetricDefinition:
    return MetricDefinition(
        name=name,
        value=value,
        numerator=numerator
        if numerator is not None
        else (
            round(value * denominator) if value is not None and denominator else None
        ),
        denominator=denominator,
        numerator_definition=f"numerator for {name}",
        denominator_definition=f"denominator for {name}",
        ground_truth_source="verified_label"
        if metric_kind is MetricKind.GROUND_TRUTH
        else "prediction_and_action_telemetry",
        evaluation_split=evaluation_split,
        support_count=support_count,
        evidence_status=evidence_status,
        metric_kind=metric_kind,
        evaluation_digest=evaluation_digest,
    )


def _provenance(active_digest: str = "a" * 64) -> EvaluationProvenance:
    return EvaluationProvenance(
        dataset_version="dataset-v1",
        dataset_digest="b" * 64,
        evaluation_digest="c" * 64,
        evaluation_split="frozen_holdout",
        active_model_digest=active_digest,
        candidate_model_digest="d" * 64,
    )


def _models(active_digest: str = "a" * 64) -> tuple[ModelReference, ModelReference]:
    return (
        ModelReference(version="active-v1", digest=active_digest),
        ModelReference(version="candidate-v1", digest="d" * 64),
    )


def test_metric_deltas_report_candidate_direction():
    active, candidate = _models()
    response = compare_candidate_metrics(
        active_metrics={"macro_f1": _metric("macro_f1", 0.80)},
        candidate_metrics={"macro_f1": _metric("macro_f1", 0.90)},
        active_model=active,
        candidate_model=candidate,
        provenance=_provenance(),
    )

    comparison = response.metric_comparisons["macro_f1"]
    assert comparison.delta == 0.10
    assert comparison.direction == "IMPROVED"


def test_macro_f1_improvement_cannot_hide_worse_verified_normal_fpr():
    active, candidate = _models()
    response = compare_candidate_metrics(
        active_metrics={
            "macro_f1": _metric("macro_f1", 0.80),
            "normal_false_positive_rate": _metric(
                "normal_false_positive_rate", 0.10, numerator=10
            ),
            "normal_recall": _metric("normal_recall", 0.99, numerator=99),
            "attack_escape_rate": _metric("attack_escape_rate", 0.05, numerator=5),
            "attack_recall": _metric("attack_recall", 0.95, numerator=95),
        },
        candidate_metrics={
            "macro_f1": _metric("macro_f1", 0.90),
            "normal_false_positive_rate": _metric(
                "normal_false_positive_rate", 0.20, numerator=20
            ),
            "normal_recall": _metric("normal_recall", 0.99, numerator=99),
            "attack_escape_rate": _metric("attack_escape_rate", 0.05, numerator=5),
            "attack_recall": _metric("attack_recall", 0.95, numerator=95),
        },
        active_model=active,
        candidate_model=candidate,
        provenance=_provenance(),
    )

    assert response.gate_results["security_regression"].status is GateStatus.FAIL
    assert response.gate_results["quality"].status is GateStatus.PASS
    assert response.overall_status is GateStatus.FAIL
    assert response.decision_allowed is False


def test_stale_active_model_binding_fails_comparison():
    active, candidate = _models(active_digest="e" * 64)
    response = compare_candidate_metrics(
        active_metrics={"macro_f1": _metric("macro_f1", 0.80)},
        candidate_metrics={"macro_f1": _metric("macro_f1", 0.90)},
        active_model=active,
        candidate_model=candidate,
        provenance=_provenance(active_digest="a" * 64),
    )

    assert response.gate_results["active_model_binding"].status is GateStatus.FAIL
    assert response.overall_status is GateStatus.FAIL
    assert response.decision_allowed is False


def test_evaluation_digest_and_split_are_bound_before_comparison_can_pass():
    active, candidate = _models()
    response = compare_candidate_metrics(
        active_metrics={"macro_f1": _metric("macro_f1", 0.80, evaluation_digest="e" * 64)},
        candidate_metrics={"macro_f1": _metric("macro_f1", 0.90)},
        active_model=active,
        candidate_model=candidate,
        provenance=_provenance(),
    )

    assert response.gate_results["evaluation_binding"].status is GateStatus.FAIL
    assert response.overall_status is GateStatus.FAIL
    assert response.decision_allowed is False


def test_proxy_or_insufficient_evidence_never_passes_security_gate():
    active, candidate = _models()
    response = compare_candidate_metrics(
        active_metrics={
            "normal_false_positive_rate": _metric(
                "normal_false_positive_rate",
                0.01,
                metric_kind=MetricKind.PROXY,
                evidence_status=EvidenceStatus.PROXY,
            )
        },
        candidate_metrics={
            "normal_false_positive_rate": _metric(
                "normal_false_positive_rate",
                0.00,
                metric_kind=MetricKind.PROXY,
                evidence_status=EvidenceStatus.PROXY,
            )
        },
        active_model=active,
        candidate_model=candidate,
        provenance=_provenance(),
    )

    assert response.gate_results["evidence"].status is GateStatus.NOT_ENOUGH_EVIDENCE
    assert (
        response.gate_results["security_regression"].status
        is GateStatus.NOT_ENOUGH_EVIDENCE
    )
    assert response.decision_allowed is False
