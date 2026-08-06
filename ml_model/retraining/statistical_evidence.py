"""Paired comparison evidence for baseline-versus-candidate predictions."""

from __future__ import annotations

import math
import random
from typing import Any, Mapping, Sequence


def _exact_mcnemar(baseline_only: int, candidate_only: int) -> dict[str, Any]:
    discordant_total = baseline_only + candidate_only
    if discordant_total == 0:
        p_value = 1.0
    else:
        tail = sum(
            math.comb(discordant_total, index)
            for index in range(min(baseline_only, candidate_only) + 1)
        ) / (2**discordant_total)
        p_value = min(1.0, 2.0 * tail)
    return {
        "discordant_total": discordant_total,
        "exact_two_sided_p_value": round(p_value, 6),
    }


def _bootstrap_accuracy_difference(
    baseline_correct: Sequence[bool],
    candidate_correct: Sequence[bool],
    *,
    seed: int = 2026,
    iterations: int = 2000,
) -> dict[str, Any]:
    rng = random.Random(seed)
    sample_count = len(baseline_correct)
    differences: list[float] = []
    for _ in range(iterations):
        indexes = [rng.randrange(sample_count) for _ in range(sample_count)]
        baseline_accuracy = (
            sum(baseline_correct[index] for index in indexes) / sample_count
        )
        candidate_accuracy = (
            sum(candidate_correct[index] for index in indexes) / sample_count
        )
        differences.append(candidate_accuracy - baseline_accuracy)
    differences.sort()
    lower_index = int(0.025 * iterations)
    upper_index = int(0.975 * iterations) - 1
    return {
        "seed": seed,
        "iterations": iterations,
        "confidence_level": 0.95,
        "lower": round(differences[lower_index], 6),
        "upper": round(differences[upper_index], 6),
    }


def build_statistical_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = ("y_true", "baseline_predictions", "candidate_predictions")
    if any(key not in payload for key in required):
        return {
            "status": "NOT_RUN",
            "reason": "paired_predictions_not_supplied",
        }
    y_true = list(payload["y_true"])
    baseline_predictions = list(payload["baseline_predictions"])
    candidate_predictions = list(payload["candidate_predictions"])
    if not y_true or len(
        {len(y_true), len(baseline_predictions), len(candidate_predictions)}
    ) != 1:
        return {
            "status": "INVALID",
            "reason": "paired_prediction_lengths_do_not_match",
        }
    baseline_correct = [
        prediction == truth for prediction, truth in zip(baseline_predictions, y_true)
    ]
    candidate_correct = [
        prediction == truth for prediction, truth in zip(candidate_predictions, y_true)
    ]
    paired_counts = {
        "baseline_only": sum(
            base and not candidate
            for base, candidate in zip(baseline_correct, candidate_correct)
        ),
        "candidate_only": sum(
            not base and candidate
            for base, candidate in zip(baseline_correct, candidate_correct)
        ),
        "both_correct": sum(
            base and candidate
            for base, candidate in zip(baseline_correct, candidate_correct)
        ),
        "both_wrong": sum(
            not base and not candidate
            for base, candidate in zip(baseline_correct, candidate_correct)
        ),
    }
    return {
        "status": "COMPUTED",
        "sample_count": len(y_true),
        "paired_error_counts": paired_counts,
        "mcnemar_exact": _exact_mcnemar(
            paired_counts["baseline_only"], paired_counts["candidate_only"]
        ),
        "effect_size": {
            "accuracy_difference": round(
                sum(candidate_correct) / len(y_true)
                - sum(baseline_correct) / len(y_true),
                6,
            )
        },
        "bootstrap_accuracy_difference": _bootstrap_accuracy_difference(
            baseline_correct, candidate_correct
        ),
    }
