from __future__ import annotations

import numpy as np

from ml_model.evaluation.metrics import (
    CONFIDENCE_BANDS,
    confidence_band_summary_frame,
    per_class_recall_at_threshold_frame,
)


def _probability_row(confidence: float) -> list[float]:
    if confidence == 0.0:
        return [0.0, 0.0, 0.0, 0.0]
    return [confidence, *([(1.0 - confidence) / 3.0] * 3)]


def test_evaluation_bands_cover_exact_plan_boundaries_once() -> None:
    confidences = [0.0, 0.25, 0.3999, 0.40, 0.6999, 0.70, 0.8999, 0.90, 1.0]
    probabilities = np.asarray([_probability_row(value) for value in confidences])
    labels = np.zeros(len(confidences), dtype=int)
    predictions = labels.copy()

    summary = confidence_band_summary_frame(labels, predictions, probabilities)

    assert [band[0] for band in CONFIDENCE_BANDS] == [
        "INFORMATIONAL",
        "LOW",
        "MEDIUM",
        "HIGH",
        "CRITICAL",
    ]
    assert summary["count"].tolist() == [1, 2, 2, 2, 2]
    assert sum(summary["count"]) == len(confidences)


def test_per_class_recall_reports_the_three_project_cutoffs() -> None:
    confidences = [0.0, 0.25, 0.3999, 0.40, 0.6999, 0.70, 0.8999, 0.90, 1.0]
    probabilities = np.asarray([_probability_row(value) for value in confidences])
    labels = np.zeros(len(confidences), dtype=int)
    predictions = labels.copy()

    recall = per_class_recall_at_threshold_frame(
        labels,
        predictions,
        probabilities,
        ["SQL Injection"],
    )

    assert recall["threshold"].tolist() == [0.4, 0.7, 0.9]
    assert recall["correct_and_confident"].tolist() == [6, 4, 2]
