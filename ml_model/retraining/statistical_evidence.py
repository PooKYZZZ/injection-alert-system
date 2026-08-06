"""Paired comparison evidence for baseline-versus-candidate predictions."""

from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any, Mapping, Sequence

from ml_model.retraining.prediction_artifacts import (
    PredictionArtifactError,
    join_prediction_artifacts,
)


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


def _computed_evidence(
    *,
    y_true: Sequence[Any],
    baseline_predictions: Sequence[Any],
    candidate_predictions: Sequence[Any],
    provenance: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
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
    result: dict[str, Any] = {
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
        "significance_claim": "NOT_CLAIMED",
        "thesis_evidence": False,
        "limitations": [
            "paired evidence is limited to the supplied locked comparison set",
            "a p-value is reported descriptively and is not a claim of significance",
            "sample size and predeclared study interpretation remain required",
        ],
    }
    if provenance is not None:
        result["provenance"] = dict(provenance)
    return result


def _build_from_arrays(payload: Mapping[str, Any]) -> dict[str, Any]:
    try:
        y_true = list(payload["y_true"])
        baseline_predictions = list(payload["baseline_predictions"])
        candidate_predictions = list(payload["candidate_predictions"])
    except (KeyError, TypeError):
        return {
            "status": "INVALID",
            "reason": "paired_predictions_malformed",
        }
    if (
        not y_true
        or len({len(y_true), len(baseline_predictions), len(candidate_predictions)})
        != 1
    ):
        return {
            "status": "INVALID",
            "reason": "paired_prediction_lengths_do_not_match",
        }
    provenance = payload.get("provenance")
    return _computed_evidence(
        y_true=y_true,
        baseline_predictions=baseline_predictions,
        candidate_predictions=candidate_predictions,
        provenance=provenance if isinstance(provenance, Mapping) else None,
    )


def build_statistical_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    artifact_keys = ("baseline_artifact", "candidate_artifact")
    if any(key in payload for key in artifact_keys):
        if not all(key in payload for key in artifact_keys):
            return {
                "status": "NOT_RUN",
                "reason": "prediction_artifacts_not_supplied",
                "incomplete_evaluation": True,
                "thesis_evidence": False,
            }
        try:
            joined = join_prediction_artifacts(
                Path(payload["baseline_artifact"]),
                Path(payload["candidate_artifact"]),
            )
        except (PredictionArtifactError, TypeError, ValueError) as exc:
            reason = str(exc)
            if reason not in {
                "prediction_ids_do_not_match",
                "prediction_provenance_mismatch",
            }:
                reason = "prediction_artifact_invalid"
            return {"status": "INVALID", "reason": reason}
        return _computed_evidence(
            y_true=joined["y_true"],
            baseline_predictions=joined["baseline_predictions"],
            candidate_predictions=joined["candidate_predictions"],
            provenance=joined["provenance"],
        )

    required = ("y_true", "baseline_predictions", "candidate_predictions")
    if any(key not in payload for key in required):
        return {
            "status": "NOT_RUN",
            "reason": "paired_predictions_not_supplied",
            "incomplete_evaluation": True,
            "thesis_evidence": False,
        }
    return _build_from_arrays(payload)
