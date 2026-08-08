"""Portable, provenance-bound per-example prediction artifacts."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ml_model.retraining.experiment_contract import canonical_json_sha256

PREDICTION_ARTIFACT_VERSION = "paired-predictions.v1"
REQUIRED_RECORD_FIELDS = {
    "sample_id",
    "split",
    "y_true",
    "prediction",
    "confidence",
    "confidence_tier",
    "response_action",
    "model_version",
    "dataset_version",
    "golden_version",
}
PROVENANCE_FIELDS = {
    "dataset_version",
    "golden_version",
    "split",
    "comparison_set_hash",
    "golden_manifest_sha256",
    "model_artifact_sha256",
}


class PredictionArtifactError(ValueError):
    """Raised when a prediction artifact is malformed or cannot be paired."""


def _validate_sha256(value: object, *, field: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise PredictionArtifactError(f"{field} must be a lowercase SHA-256 hash")
    return value


def _comparison_set_hash(records: Sequence[Mapping[str, Any]]) -> str:
    return canonical_json_sha256(
        {
            "sample_ids": [str(record["sample_id"]) for record in records],
            "y_true": [str(record["y_true"]) for record in records],
        }
    )


def _normalize_record(
    record: Mapping[str, Any],
    *,
    model_version: str,
    dataset_version: str,
    golden_version: str,
    split: str,
) -> dict[str, Any]:
    sample_id = str(record.get("sample_id", "")).strip()
    if not sample_id:
        raise PredictionArtifactError("prediction record is missing sample_id")
    prediction = str(record.get("prediction", "")).strip()
    y_true = str(record.get("y_true", "")).strip()
    if not prediction or not y_true:
        raise PredictionArtifactError(
            f"prediction record {sample_id} is missing y_true or prediction"
        )
    try:
        confidence = float(record.get("confidence"))
    except (TypeError, ValueError) as exc:
        raise PredictionArtifactError(
            f"prediction record {sample_id} has invalid confidence"
        ) from exc
    if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
        raise PredictionArtifactError(
            f"prediction record {sample_id} confidence is outside 0..1"
        )
    normalized = {
        "sample_id": sample_id,
        "split": str(record.get("split", split)),
        "y_true": y_true,
        "prediction": prediction,
        "confidence": round(confidence, 6),
        "confidence_tier": str(record.get("confidence_tier", "")),
        "response_action": str(
            record.get("response_action", record.get("predicted_action", ""))
        ),
        "model_version": str(record.get("model_version", model_version)),
        "dataset_version": str(record.get("dataset_version", dataset_version)),
        "golden_version": str(record.get("golden_version", golden_version)),
    }
    if normalized["split"] != split:
        raise PredictionArtifactError(
            f"prediction record {sample_id} split does not match artifact split"
        )
    if normalized["dataset_version"] != dataset_version:
        raise PredictionArtifactError(
            f"prediction record {sample_id} dataset version does not match artifact"
        )
    if normalized["golden_version"] != golden_version:
        raise PredictionArtifactError(
            f"prediction record {sample_id} golden version does not match artifact"
        )
    return normalized


def write_prediction_artifact(
    path: Path | str,
    records: Iterable[Mapping[str, Any]],
    *,
    model_version: str,
    dataset_version: str,
    golden_version: str,
    split: str = "golden",
    golden_manifest_sha256: str,
    model_artifact_sha256: str,
) -> dict[str, Any]:
    normalized_records = sorted(
        (
            _normalize_record(
                record,
                model_version=model_version,
                dataset_version=dataset_version,
                golden_version=golden_version,
                split=split,
            )
            for record in records
        ),
        key=lambda record: record["sample_id"],
    )
    sample_ids = [record["sample_id"] for record in normalized_records]
    if len(sample_ids) != len(set(sample_ids)):
        raise PredictionArtifactError(
            "prediction artifact contains duplicate sample_id"
        )
    if not normalized_records:
        raise PredictionArtifactError("prediction artifact must contain records")
    provenance = {
        "dataset_version": dataset_version,
        "golden_version": golden_version,
        "split": split,
        "comparison_set_hash": _comparison_set_hash(normalized_records),
        "golden_manifest_sha256": _validate_sha256(
            golden_manifest_sha256, field="golden_manifest_sha256"
        ),
        "model_artifact_sha256": _validate_sha256(
            model_artifact_sha256, field="model_artifact_sha256"
        ),
    }
    unsigned = {
        "artifact_version": PREDICTION_ARTIFACT_VERSION,
        "provenance": provenance,
        "records": normalized_records,
    }
    payload = {**unsigned, "artifact_sha256": canonical_json_sha256(unsigned)}
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return payload


def _validate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    if payload.get("artifact_version") != PREDICTION_ARTIFACT_VERSION:
        raise PredictionArtifactError("unsupported prediction artifact version")
    provenance = payload.get("provenance")
    records = payload.get("records")
    if not isinstance(provenance, Mapping) or not isinstance(records, list):
        raise PredictionArtifactError(
            "prediction artifact is missing provenance or records"
        )
    missing = sorted(PROVENANCE_FIELDS - set(provenance))
    if missing:
        raise PredictionArtifactError(
            "prediction artifact provenance is missing: " + ", ".join(missing)
        )
    _validate_sha256(
        provenance["golden_manifest_sha256"], field="golden_manifest_sha256"
    )
    _validate_sha256(
        provenance["model_artifact_sha256"], field="model_artifact_sha256"
    )
    if payload.get("artifact_sha256") != canonical_json_sha256(
        {key: payload[key] for key in ("artifact_version", "provenance", "records")}
    ):
        raise PredictionArtifactError("prediction artifact hash mismatch")
    normalized_records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for record in records:
        if not isinstance(record, Mapping):
            raise PredictionArtifactError(
                "prediction artifact record must be an object"
            )
        missing_record = sorted(REQUIRED_RECORD_FIELDS - set(record))
        if missing_record:
            raise PredictionArtifactError(
                "prediction artifact record is missing: " + ", ".join(missing_record)
            )
        sample_id = str(record["sample_id"])
        if sample_id in seen_ids:
            raise PredictionArtifactError(
                "prediction artifact contains duplicate sample_id"
            )
        seen_ids.add(sample_id)
        normalized_records.append(dict(record))
    normalized_records.sort(key=lambda record: str(record["sample_id"]))
    if [record["sample_id"] for record in normalized_records] != [
        record["sample_id"] for record in records
    ]:
        raise PredictionArtifactError(
            "prediction artifact records are not deterministically sorted"
        )
    if provenance["comparison_set_hash"] != _comparison_set_hash(normalized_records):
        raise PredictionArtifactError(
            "prediction artifact comparison set hash mismatch"
        )
    for record in normalized_records:
        for key in ("split", "dataset_version", "golden_version"):
            if record[key] != provenance[key]:
                raise PredictionArtifactError(
                    f"prediction record {record['sample_id']} {key} does not "
                    "match provenance"
                )
    return {
        **dict(payload),
        "provenance": dict(provenance),
        "records": normalized_records,
    }


def load_prediction_artifact(path: Path | str) -> dict[str, Any]:
    source = Path(path).expanduser().resolve()
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PredictionArtifactError(f"invalid prediction artifact: {source}") from exc
    if not isinstance(payload, Mapping):
        raise PredictionArtifactError("prediction artifact must be a JSON object")
    return _validate_payload(payload)


def join_prediction_artifacts(
    baseline_path: Path | str,
    candidate_path: Path | str,
) -> dict[str, Any]:
    baseline = load_prediction_artifact(baseline_path)
    candidate = load_prediction_artifact(candidate_path)
    baseline_records = {record["sample_id"]: record for record in baseline["records"]}
    candidate_records = {record["sample_id"]: record for record in candidate["records"]}
    if set(baseline_records) != set(candidate_records):
        raise PredictionArtifactError("prediction_ids_do_not_match")
    baseline_provenance = baseline["provenance"]
    candidate_provenance = candidate["provenance"]
    for key in (
        "dataset_version",
        "golden_version",
        "split",
        "comparison_set_hash",
        "golden_manifest_sha256",
    ):
        if baseline_provenance[key] != candidate_provenance[key]:
            raise PredictionArtifactError("prediction_provenance_mismatch")
    sample_ids = sorted(baseline_records)
    return {
        "sample_ids": sample_ids,
        "y_true": [baseline_records[sample_id]["y_true"] for sample_id in sample_ids],
        "baseline_predictions": [
            baseline_records[sample_id]["prediction"] for sample_id in sample_ids
        ],
        "candidate_predictions": [
            candidate_records[sample_id]["prediction"] for sample_id in sample_ids
        ],
        "provenance": {
            "dataset_version": baseline_provenance["dataset_version"],
            "golden_version": baseline_provenance["golden_version"],
            "split": baseline_provenance["split"],
            "comparison_set_hash": baseline_provenance["comparison_set_hash"],
            "golden_manifest_sha256": baseline_provenance[
                "golden_manifest_sha256"
            ],
            "baseline_model_artifact_sha256": baseline_provenance[
                "model_artifact_sha256"
            ],
            "candidate_model_artifact_sha256": candidate_provenance[
                "model_artifact_sha256"
            ],
        },
        "baseline_model_version": baseline["records"][0]["model_version"],
        "candidate_model_version": candidate["records"][0]["model_version"],
    }


def records_from_golden_evaluation(
    controls: Iterable[Mapping[str, Any]],
    evaluation: Mapping[str, Any],
    *,
    model_version: str,
    dataset_version: str,
    golden_version: str,
) -> list[dict[str, Any]]:
    results = evaluation.get("cases")
    if not isinstance(results, list):
        raise PredictionArtifactError(
            "golden evaluation does not contain per-example cases"
        )
    by_id = {str(result.get("case_id")): result for result in results}
    records: list[dict[str, Any]] = []
    for control in controls:
        sample_id = str(control["case_id"])
        result = by_id.get(sample_id)
        if result is None:
            raise PredictionArtifactError(
                f"golden evaluation is missing case {sample_id}"
            )
        records.append(
            {
                "sample_id": sample_id,
                "split": "golden",
                "y_true": str(control["expected_label"]),
                "prediction": str(result.get("predicted_label", "")),
                "confidence": result.get(
                    "confidence", result.get("predicted_probability")
                ),
                "confidence_tier": str(result.get("confidence_tier", "")),
                "response_action": str(result.get("predicted_action", "")),
            }
        )
    return records
