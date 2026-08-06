"""Deterministic per-batch drift and validation-evidence summaries."""

from __future__ import annotations

from collections import Counter
from statistics import mean
from typing import Any, Iterable, Mapping
from urllib.parse import parse_qsl, urlsplit


def _distribution(values: Iterable[object]) -> dict[str, int]:
    return dict(sorted(Counter(str(value) for value in values).items()))


def _numeric_summary(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"status": "NOT_AVAILABLE", "count": 0}
    return {
        "status": "COMPUTED",
        "count": len(values),
        "min": round(min(values), 6),
        "max": round(max(values), 6),
        "mean": round(mean(values), 6),
    }


def _request_target(text: str) -> str:
    parts = text.split()
    return parts[1] if len(parts) > 1 else ""


def _error_category(reason: str) -> str:
    category_map = (
        ("unknown label", "unknown_label"),
        ("missing", "missing_field"),
        ("duplicate", "duplicate"),
        ("golden overlap", "golden_overlap"),
        ("preprocessing", "preprocessing"),
        ("batch_day", "batch_day"),
        ("model_input_hash", "model_input_hash"),
        ("simulation fixture", "simulation_fixture"),
        ("not approved", "review_status"),
    )
    for marker, category in category_map:
        if marker in reason:
            return category
    return "validation_error"


def build_batch_drift_summary(
    samples: Iterable[Mapping[str, Any]],
    rejected_samples: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    rows = [dict(sample) for sample in samples]
    texts = [str(row.get("model_input_text", "")) for row in rows]
    methods = [text.split(maxsplit=1)[0].upper() for text in texts if text]
    query_parameters: Counter[str] = Counter()
    for text in texts:
        target = _request_target(text)
        query_parameters.update(name for name, _ in parse_qsl(urlsplit(target).query))
    confidence_values = [
        float(row["confidence"])
        for row in rows
        if row.get("confidence") is not None
    ]
    duplicate_count = len(texts) - len(set(texts))
    rejection_categories = Counter(
        _error_category(str(row.get("reason", "")))
        for row in rejected_samples
    )
    return {
        "sample_count": len(rows),
        "http_method_distribution": _distribution(methods),
        "request_length_distribution": _numeric_summary(
            [float(len(text)) for text in texts]
        ),
        "query_parameter_frequency": dict(sorted(query_parameters.items())),
        "attack_category_distribution": _distribution(
            row.get("ground_truth_label", "UNKNOWN") for row in rows
        ),
        "confidence_distribution": _numeric_summary(confidence_values),
        "duplicate_rate": round(duplicate_count / len(texts), 6) if texts else 0.0,
        "source_distribution": _distribution(
            row.get("source_type", "UNKNOWN") for row in rows
        ),
        "validation_error_categories": dict(sorted(rejection_categories.items())),
    }
