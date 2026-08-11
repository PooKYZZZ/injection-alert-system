"""Pure metric semantics and candidate-versus-active comparison gates."""

from __future__ import annotations

from collections import Counter
from typing import Mapping, Sequence

from ml_model.retraining.dashboard_contracts import (
    CANONICAL_LABELS,
    ComparisonResponse,
    ComparisonTolerances,
    EvaluationProvenance,
    EvidenceStatus,
    GateResult,
    GateStatus,
    MetricComparison,
    MetricDefinition,
    MetricKind,
    ModelReference,
)


def _support_status(support: int, minimum: int, observed_rows: int) -> EvidenceStatus:
    if support == 0:
        return (
            EvidenceStatus.NOT_ENOUGH_EVIDENCE
            if observed_rows
            else EvidenceStatus.NOT_RUN
        )
    if support < minimum:
        return EvidenceStatus.NOT_ENOUGH_EVIDENCE
    return EvidenceStatus.VERIFIED


def _unavailable_metric(
    *,
    name: str,
    numerator_definition: str,
    denominator_definition: str,
    denominator: int,
    support_count: int,
    evidence_status: EvidenceStatus,
    evaluation_split: str,
    evaluation_digest: str,
) -> MetricDefinition:
    return MetricDefinition(
        name=name,
        value=None,
        numerator=None,
        denominator=denominator,
        numerator_definition=numerator_definition,
        denominator_definition=denominator_definition,
        ground_truth_source="verified_label",
        evaluation_split=evaluation_split,
        support_count=support_count,
        evidence_status=evidence_status,
        metric_kind=MetricKind.GROUND_TRUTH,
        evaluation_digest=evaluation_digest,
    )


def _rate_metric(
    *,
    name: str,
    numerator: int,
    denominator: int,
    numerator_definition: str,
    denominator_definition: str,
    evaluation_split: str,
    minimum_support: int,
    observed_rows: int,
    evaluation_digest: str,
) -> MetricDefinition:
    status = _support_status(denominator, minimum_support, observed_rows)
    if status is not EvidenceStatus.VERIFIED:
        return _unavailable_metric(
            name=name,
            numerator_definition=numerator_definition,
            denominator_definition=denominator_definition,
            denominator=denominator,
            support_count=denominator,
            evidence_status=status,
            evaluation_split=evaluation_split,
            evaluation_digest=evaluation_digest,
        )
    return MetricDefinition(
        name=name,
        value=numerator / denominator,
        numerator=numerator,
        denominator=denominator,
        numerator_definition=numerator_definition,
        denominator_definition=denominator_definition,
        ground_truth_source="verified_label",
        evaluation_split=evaluation_split,
        support_count=denominator,
        evidence_status=status,
        metric_kind=MetricKind.GROUND_TRUTH,
        evaluation_digest=evaluation_digest,
    )


def build_operational_proxy_metric(
    *, numerator: int, denominator: int
) -> MetricDefinition:
    """Describe the current dashboard telemetry proxy without calling it FPR."""

    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError("proxy numerator and denominator must form a valid count")
    if denominator == 0:
        return MetricDefinition(
            name="allowed_non_normal_prediction_rate_proxy",
            value=None,
            numerator=None,
            denominator=0,
            numerator_definition="allowed requests with a non-Normal prediction",
            denominator_definition="all completed requests in the operational window",
            ground_truth_source="prediction_and_action_telemetry",
            evaluation_split="operational_window",
            support_count=0,
            evidence_status=EvidenceStatus.NOT_RUN,
            metric_kind=MetricKind.PROXY,
        )
    return MetricDefinition(
        name="allowed_non_normal_prediction_rate_proxy",
        value=numerator / denominator,
        numerator=numerator,
        denominator=denominator,
        numerator_definition="allowed requests with a non-Normal prediction",
        denominator_definition="all completed requests in the operational window",
        ground_truth_source="prediction_and_action_telemetry",
        evaluation_split="operational_window",
        support_count=denominator,
        evidence_status=EvidenceStatus.PROXY,
        metric_kind=MetricKind.PROXY,
    )


def _f1_metric(
    *,
    name: str,
    true_positive: int,
    false_positive: int,
    false_negative: int,
    support: int,
    evaluation_split: str,
    minimum_support: int,
    observed_rows: int,
    evaluation_digest: str,
) -> MetricDefinition:
    status = _support_status(support, minimum_support, observed_rows)
    numerator_definition = f"F1 numerator for {name}"
    denominator_definition = f"F1 denominator for {name}"
    if status is not EvidenceStatus.VERIFIED:
        return _unavailable_metric(
            name=name,
            numerator_definition=numerator_definition,
            denominator_definition=denominator_definition,
            denominator=support,
            support_count=support,
            evidence_status=status,
            evaluation_split=evaluation_split,
            evaluation_digest=evaluation_digest,
        )
    f1_denominator = 2 * true_positive + false_positive + false_negative
    value = (2 * true_positive / f1_denominator) if f1_denominator else 0.0
    return MetricDefinition(
        name=name,
        value=value,
        numerator=2 * true_positive,
        denominator=f1_denominator,
        numerator_definition=numerator_definition,
        denominator_definition=denominator_definition,
        ground_truth_source="verified_label",
        evaluation_split=evaluation_split,
        support_count=support,
        evidence_status=status,
        metric_kind=MetricKind.GROUND_TRUTH,
        evaluation_digest=evaluation_digest,
    )


def calculate_ground_truth_metrics(
    verified_labels: Sequence[str],
    predictions: Sequence[str],
    *,
    evaluation_split: str = "evaluation",
    evaluation_digest: str,
    min_normal_support: int = 1,
    min_attack_support: int = 1,
    min_class_support: int = 1,
) -> dict[str, MetricDefinition]:
    """Calculate security metrics from verified labels, never triage status."""

    labels = list(verified_labels)
    predicted = list(predictions)
    if len(labels) != len(predicted):
        raise ValueError("verified labels and predictions must have equal lengths")
    for label in labels:
        if label not in CANONICAL_LABELS:
            raise ValueError("verified labels must use the canonical label vocabulary")
    for label in predicted:
        if label not in CANONICAL_LABELS:
            raise ValueError("predictions must use the canonical label vocabulary")

    normal_support = sum(label == "Normal" for label in labels)
    attack_support = len(labels) - normal_support
    normal_false_positives = sum(
        truth == "Normal" and prediction != "Normal"
        for truth, prediction in zip(labels, predicted)
    )
    attack_escapes = sum(
        truth != "Normal" and prediction == "Normal"
        for truth, prediction in zip(labels, predicted)
    )
    normal_true_positives = normal_support - normal_false_positives
    attack_true_positives = attack_support - attack_escapes

    metrics: dict[str, MetricDefinition] = {
        "normal_false_positive_rate": _rate_metric(
            name="normal_false_positive_rate",
            numerator=normal_false_positives,
            denominator=normal_support,
            numerator_definition="actual Normal rows predicted as a non-Normal class",
            denominator_definition="all rows with verified_label=Normal",
            evaluation_split=evaluation_split,
            minimum_support=min_normal_support,
            observed_rows=len(labels),
            evaluation_digest=evaluation_digest,
        ),
        "normal_recall": _rate_metric(
            name="normal_recall",
            numerator=normal_true_positives,
            denominator=normal_support,
            numerator_definition="actual Normal rows predicted as Normal",
            denominator_definition="all rows with verified_label=Normal",
            evaluation_split=evaluation_split,
            minimum_support=min_normal_support,
            observed_rows=len(labels),
            evaluation_digest=evaluation_digest,
        ),
        "attack_escape_rate": _rate_metric(
            name="attack_escape_rate",
            numerator=attack_escapes,
            denominator=attack_support,
            numerator_definition="actual attack rows predicted as Normal",
            denominator_definition="all rows with a non-Normal verified label",
            evaluation_split=evaluation_split,
            minimum_support=min_attack_support,
            observed_rows=len(labels),
            evaluation_digest=evaluation_digest,
        ),
        "attack_recall": _rate_metric(
            name="attack_recall",
            numerator=attack_true_positives,
            denominator=attack_support,
            numerator_definition="actual attack rows predicted as a non-Normal class",
            denominator_definition="all rows with a non-Normal verified label",
            evaluation_split=evaluation_split,
            minimum_support=min_attack_support,
            observed_rows=len(labels),
            evaluation_digest=evaluation_digest,
        ),
    }

    class_f1_values: list[float] = []
    class_metrics: dict[str, MetricDefinition] = {}
    counts = Counter(labels)
    for label in CANONICAL_LABELS:
        true_positive = sum(
            truth == label and prediction == label
            for truth, prediction in zip(labels, predicted)
        )
        false_positive = sum(
            truth != label and prediction == label
            for truth, prediction in zip(labels, predicted)
        )
        false_negative = sum(
            truth == label and prediction != label
            for truth, prediction in zip(labels, predicted)
        )
        class_metric = _f1_metric(
            name=f"per_class.{label}.f1",
            true_positive=true_positive,
            false_positive=false_positive,
            false_negative=false_negative,
            support=counts[label],
            evaluation_split=evaluation_split,
            minimum_support=min_class_support,
            observed_rows=len(labels),
            evaluation_digest=evaluation_digest,
        )
        class_metrics[class_metric.name] = class_metric
        recall_metric = _rate_metric(
            name=f"per_class.{label}.recall",
            numerator=true_positive,
            denominator=counts[label],
            numerator_definition=f"{label} rows predicted as {label}",
            denominator_definition=f"all rows with verified_label={label}",
            evaluation_split=evaluation_split,
            minimum_support=min_class_support,
            observed_rows=len(labels),
            evaluation_digest=evaluation_digest,
        )
        class_metrics[recall_metric.name] = recall_metric
        if class_metric.value is not None:
            class_f1_values.append(class_metric.value)

    metrics.update(class_metrics)
    total_support = len(labels)
    if len(class_f1_values) == len(CANONICAL_LABELS) and total_support:
        macro_f1 = sum(class_f1_values) / len(class_f1_values)
        metrics["macro_f1"] = MetricDefinition(
            name="macro_f1",
            value=macro_f1,
            numerator=None,
            denominator=total_support,
            numerator_definition="mean of the four canonical per-class F1 values",
            denominator_definition="all rows in the evaluation split",
            ground_truth_source="verified_label",
            evaluation_split=evaluation_split,
            support_count=total_support,
            evidence_status=EvidenceStatus.VERIFIED,
            metric_kind=MetricKind.GROUND_TRUTH,
            evaluation_digest=evaluation_digest,
        )
    else:
        metrics["macro_f1"] = _unavailable_metric(
            name="macro_f1",
            numerator_definition="mean of the four canonical per-class F1 values",
            denominator_definition="all rows in the evaluation split",
            denominator=total_support,
            support_count=total_support,
            evidence_status=(
                EvidenceStatus.NOT_RUN
                if not labels
                else EvidenceStatus.NOT_ENOUGH_EVIDENCE
            ),
            evaluation_split=evaluation_split,
            evaluation_digest=evaluation_digest,
        )
    return metrics


def _metric_direction(name: str, delta: float | None) -> str:
    if delta is None:
        return "UNKNOWN"
    lower_is_better = {
        "normal_false_positive_rate",
        "attack_escape_rate",
        "latency_ms",
    }
    if abs(delta) < 1e-12:
        return "UNCHANGED"
    if name in lower_is_better:
        return "IMPROVED" if delta < 0 else "REGRESSED"
    return "IMPROVED" if delta > 0 else "REGRESSED"


def _build_metric_comparisons(
    active_metrics: Mapping[str, MetricDefinition],
    candidate_metrics: Mapping[str, MetricDefinition],
) -> dict[str, MetricComparison]:
    comparisons: dict[str, MetricComparison] = {}
    for name in sorted(set(active_metrics) | set(candidate_metrics)):
        active = active_metrics.get(name)
        candidate = candidate_metrics.get(name)
        delta = None
        if active is not None and candidate is not None:
            if active.value is not None and candidate.value is not None:
                delta = round(candidate.value - active.value, 6)
        comparisons[name] = MetricComparison(
            metric_name=name,
            active=active,
            candidate=candidate,
            delta=delta,
            direction=_metric_direction(name, delta),
        )
    return comparisons


def _split_per_class(
    comparisons: Mapping[str, MetricComparison],
) -> dict[str, dict[str, MetricComparison]]:
    result: dict[str, dict[str, MetricComparison]] = {}
    for name, comparison in comparisons.items():
        if not name.startswith("per_class."):
            continue
        _, label, metric = name.split(".", 2)
        result.setdefault(label, {})[metric] = comparison
    return result


def _available_metric(metric: MetricDefinition | None) -> bool:
    return bool(
        metric is not None
        and metric.value is not None
        and metric.denominator
        and metric.support_count
        and metric.evaluation_digest
        and metric.evidence_status in {EvidenceStatus.VERIFIED, EvidenceStatus.NATIVE}
        and metric.metric_kind is not MetricKind.PROXY
    )


def _critical_metric_names() -> tuple[str, ...]:
    return (
        "normal_false_positive_rate",
        "normal_recall",
        "attack_escape_rate",
        "attack_recall",
        "macro_f1",
        *(
            f"per_class.{label}.recall"
            for label in CANONICAL_LABELS
            if label != "Normal"
        ),
    )


def _gate(
    name: str,
    status: GateStatus,
    reason: str,
    metric_names: tuple[str, ...] = (),
) -> GateResult:
    return GateResult(
        name=name, status=status, reason=reason, metric_names=metric_names
    )


def compare_candidate_metrics(
    *,
    active_metrics: Mapping[str, MetricDefinition],
    candidate_metrics: Mapping[str, MetricDefinition],
    active_model: ModelReference,
    candidate_model: ModelReference,
    provenance: EvaluationProvenance,
    tolerances: ComparisonTolerances | None = None,
) -> ComparisonResponse:
    """Compare one candidate against the exact active model it was evaluated with."""

    policy = tolerances or ComparisonTolerances()
    comparisons = _build_metric_comparisons(active_metrics, candidate_metrics)
    per_class_metrics = _split_per_class(comparisons)
    gates: dict[str, GateResult] = {}
    critical_names = _critical_metric_names()

    binding_ok = (
        provenance.active_model_digest == active_model.digest
        and provenance.candidate_model_digest == candidate_model.digest
    )
    gates["active_model_binding"] = _gate(
        "active_model_binding",
        GateStatus.PASS if binding_ok else GateStatus.FAIL,
        "evaluation is bound to the active and candidate artifact digests"
        if binding_ok
        else "evaluation was produced against a different active or candidate digest",
    )

    mismatched_evidence: list[str] = []
    missing_evidence_binding: list[str] = []
    for name in critical_names:
        for metrics in (active_metrics, candidate_metrics):
            metric = metrics.get(name)
            if metric is None or metric.evaluation_digest is None:
                missing_evidence_binding.append(name)
            elif (
                metric.evaluation_digest != provenance.evaluation_digest
                or metric.evaluation_split != provenance.evaluation_split
            ):
                mismatched_evidence.append(name)
    if mismatched_evidence:
        gates["evaluation_binding"] = _gate(
            "evaluation_binding",
            GateStatus.FAIL,
            "metric evidence was produced from a different evaluation digest or split",
            tuple(sorted(set(mismatched_evidence))),
        )
    elif missing_evidence_binding:
        gates["evaluation_binding"] = _gate(
            "evaluation_binding",
            GateStatus.NOT_ENOUGH_EVIDENCE,
            "critical metric evidence is not bound to the reviewed evaluation split",
            tuple(sorted(set(missing_evidence_binding))),
        )
    else:
        gates["evaluation_binding"] = _gate(
            "evaluation_binding",
            GateStatus.PASS,
            "critical metrics are bound to the reviewed evaluation digest and split",
            critical_names,
        )

    unavailable = tuple(
        name
        for name in critical_names
        if not _available_metric(active_metrics.get(name))
        or not _available_metric(candidate_metrics.get(name))
    )
    if unavailable:
        gates["evidence"] = _gate(
            "evidence",
            GateStatus.NOT_ENOUGH_EVIDENCE,
            "critical metrics lack verified-label values and positive support",
            unavailable,
        )
    else:
        gates["evidence"] = _gate(
            "evidence",
            GateStatus.PASS,
            "critical metrics include verified-label values and positive support",
            critical_names,
        )

    security_names = (
        "normal_false_positive_rate",
        "normal_recall",
        "attack_escape_rate",
        "attack_recall",
    )
    unavailable_security = tuple(
        name
        for name in security_names
        if not _available_metric(active_metrics.get(name))
        or not _available_metric(candidate_metrics.get(name))
    )
    unavailable_per_class = tuple(
        name
        for name in critical_names
        if name.startswith("per_class.")
        and (
            not _available_metric(active_metrics.get(name))
            or not _available_metric(candidate_metrics.get(name))
        )
    )
    if unavailable_security:
        gates["security_regression"] = _gate(
            "security_regression",
            GateStatus.NOT_ENOUGH_EVIDENCE,
            (
                "security regression cannot be evaluated without sufficient "
                "ground-truth support"
            ),
            unavailable_security,
        )
    else:
        security_failures: list[str] = []
        fpr_delta = comparisons["normal_false_positive_rate"].delta
        if fpr_delta is not None and fpr_delta > policy.normal_fpr_max_increase:
            security_failures.append(
                "normal_false_positive_rate increased beyond tolerance"
            )
        normal_recall = candidate_metrics["normal_recall"].value
        if normal_recall is not None and normal_recall < policy.normal_recall_minimum:
            security_failures.append("candidate normal recall is below the minimum")
        escape_delta = comparisons["attack_escape_rate"].delta
        if (
            escape_delta is not None
            and escape_delta > policy.attack_escape_max_increase
        ):
            security_failures.append("attack_escape_rate increased beyond tolerance")
        attack_recall_delta = comparisons["attack_recall"].delta
        if (
            attack_recall_delta is not None
            and attack_recall_delta < -policy.supported_attack_recall_drop
        ):
            security_failures.append(
                "aggregate attack recall regressed beyond tolerance"
            )
        for name, comparison in comparisons.items():
            if not name.startswith("per_class.") or not name.endswith(".recall"):
                continue
            if (
                comparison.delta is not None
                and comparison.delta < -policy.supported_attack_recall_drop
            ):
                security_failures.append(f"{name} regressed beyond tolerance")
        security_status = (
            GateStatus.FAIL
            if security_failures
            else GateStatus.NOT_ENOUGH_EVIDENCE
            if unavailable_per_class
            else GateStatus.PASS
        )
        gates["security_regression"] = _gate(
            "security_regression",
            security_status,
            "; ".join(security_failures)
            if security_failures
            else "per-class security recall evidence is incomplete"
            if unavailable_per_class
            else "no configured security-critical regression exceeded tolerance",
            security_names + unavailable_per_class,
        )

    active_macro = active_metrics.get("macro_f1")
    candidate_macro = candidate_metrics.get("macro_f1")
    if not _available_metric(active_macro) or not _available_metric(candidate_macro):
        gates["quality"] = _gate(
            "quality",
            GateStatus.NOT_ENOUGH_EVIDENCE,
            "macro F1 is not supported by verified evaluation evidence",
            ("macro_f1",),
        )
        gates["improvement"] = _gate(
            "improvement",
            GateStatus.NOT_ENOUGH_EVIDENCE,
            "meaningful improvement cannot be assessed without macro F1",
            ("macro_f1",),
        )
    else:
        macro_delta = comparisons["macro_f1"].delta or 0.0
        gates["quality"] = _gate(
            "quality",
            GateStatus.PASS
            if macro_delta >= -policy.macro_f1_max_drop
            else GateStatus.FAIL,
            "macro F1 is within the configured drop tolerance"
            if macro_delta >= -policy.macro_f1_max_drop
            else "macro F1 dropped beyond the configured tolerance",
            ("macro_f1",),
        )
        gates["improvement"] = _gate(
            "improvement",
            GateStatus.PASS if macro_delta > 0.0 else GateStatus.FAIL,
            "candidate macro F1 is meaningfully higher"
            if macro_delta > 0.0
            else "candidate macro F1 is not higher than the active model",
            ("macro_f1",),
        )

    statuses = [gate.status for gate in gates.values()]
    if GateStatus.FAIL in statuses:
        overall = GateStatus.FAIL
    elif GateStatus.NOT_ENOUGH_EVIDENCE in statuses:
        overall = GateStatus.NOT_ENOUGH_EVIDENCE
    elif GateStatus.NOT_RUN in statuses:
        overall = GateStatus.NOT_RUN
    else:
        overall = GateStatus.PASS

    return ComparisonResponse(
        active_model=active_model,
        candidate_model=candidate_model,
        provenance=provenance,
        active_metrics=active_metrics,
        candidate_metrics=candidate_metrics,
        metric_comparisons=comparisons,
        per_class_metrics=per_class_metrics,
        gate_results=gates,
        overall_status=overall,
        decision_allowed=overall is GateStatus.PASS,
    )
