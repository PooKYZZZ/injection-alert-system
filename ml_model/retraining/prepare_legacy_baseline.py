"""Capture metrics for an existing legacy staged artifact.

The current serving artifact predates the retraining run contract and does
not contain ``summary_metrics.json``. This command does not retrain or alter
model weights. It verifies that the existing calibration evidence belongs to
the exact staged artifact, then writes a provenance-marked summary file that
the baseline evaluator can consume.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Mapping

from ml_model.retraining.experiment_contract import sha256_file


class LegacyBaselineError(ValueError):
    """Raised when legacy evaluation evidence cannot be linked safely."""


def _load_json(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise LegacyBaselineError(f"required JSON file is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise LegacyBaselineError(f"JSON file must contain an object: {path}")
    return payload


def _float(payload: Mapping[str, Any], key: str, *, context: str) -> float:
    value = payload.get(key)
    if isinstance(value, bool) or value is None:
        raise LegacyBaselineError(f"{context} is missing numeric field {key!r}")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise LegacyBaselineError(
            f"{context} field {key!r} must be numeric"
        ) from exc


def _relative_source_path(path: Path) -> str:
    repo_root = Path(__file__).resolve().parents[2]
    try:
        return path.resolve().relative_to(repo_root).as_posix()
    except ValueError:
        return path.name


def build_legacy_summary(
    *,
    artifact_dir: Path | str,
    evaluation_file: Path | str,
    output_path: Path | str,
    dataset_version: str = "v3_907k_cleaned",
    preprocessing_version: str = "http-preprocessor-v1",
) -> dict[str, Any]:
    artifact = Path(artifact_dir).expanduser().resolve()
    evaluation_path = Path(evaluation_file).expanduser().resolve()
    output = Path(output_path).expanduser().resolve()
    manifest_path = artifact / "serving_manifest.json"
    manifest = _load_json(manifest_path)
    evaluation = _load_json(evaluation_path)
    eval_report = _load_json(artifact / "eval_report.json")

    model_key = str(manifest.get("model_key", ""))
    if model_key != "distilbert" or evaluation.get("model") != model_key:
        raise LegacyBaselineError(
            "legacy evaluation model does not match the staged DistilBERT artifact"
        )

    calibration_dir = manifest.get("calibration_eval_run_dir")
    if isinstance(calibration_dir, str) and calibration_dir.strip():
        if Path(calibration_dir).expanduser().resolve() != evaluation_path.parent:
            raise LegacyBaselineError(
                "evaluation file is outside the artifact's calibration_eval_run_dir"
            )

    manifest_temperature = _float(
        manifest, "temperature", context="serving manifest"
    )
    evaluation_temperature = _float(
        evaluation, "temperature", context="evaluation file"
    )
    if abs(manifest_temperature - evaluation_temperature) > 1e-6:
        raise LegacyBaselineError(
            "calibration temperature does not match the staged artifact"
        )

    checkpoint_name = manifest.get("checkpoint_file")
    if not isinstance(checkpoint_name, str) or not checkpoint_name:
        raise LegacyBaselineError("serving manifest is missing checkpoint_file")
    checkpoint_path = artifact / checkpoint_name
    checkpoint_hash = sha256_file(checkpoint_path)
    if manifest.get("checkpoint_sha256") != checkpoint_hash:
        raise LegacyBaselineError("staged checkpoint hash does not match manifest")

    operational = evaluation.get("operational")
    if not isinstance(operational, Mapping):
        raise LegacyBaselineError("evaluation file is missing operational metrics")
    normal_false_positive_rate = _float(
        operational, "benign_false_positive_rate", context="operational metrics"
    )
    if "attack_escape_rate" in operational:
        attack_escape_rate = _float(
            operational, "attack_escape_rate", context="operational metrics"
        )
    else:
        attack_detection_rate = _float(
            operational, "attack_detection_rate", context="operational metrics"
        )
        attack_escape_rate = 1.0 - attack_detection_rate

    per_class = eval_report.get("per_class")
    if not isinstance(per_class, Mapping):
        per_class = {
            label: values
            for label, values in eval_report.items()
            if label not in {"accuracy", "macro avg", "weighted avg"}
            and isinstance(values, Mapping)
        }
    normal = per_class.get("Normal")
    if not isinstance(normal, Mapping):
        raise LegacyBaselineError("eval_report is missing Normal metrics")
    supported_attack_recall: dict[str, float] = {}
    for label, values in per_class.items():
        if label == "Normal" or not isinstance(values, Mapping):
            continue
        supported_attack_recall[str(label)] = _float(
            values, "recall", context=f"eval_report[{label}]"
        )

    summary = {
        "legacy_baseline": True,
        "provenance_status": "legacy_evaluation_capture",
        "provenance_note": (
            "Metrics were captured from the calibration evaluation explicitly "
            "referenced by the existing staged artifact; no model weights were changed."
        ),
        "model_key": model_key,
        "model_version": manifest.get("model_version", artifact.name),
        "dataset_version": dataset_version,
        "preprocessing_version": preprocessing_version,
        "checkpoint_sha256": checkpoint_hash,
        "artifact_manifest_sha256": sha256_file(manifest_path),
        "source_evaluation_file": _relative_source_path(evaluation_path),
        "source_evaluation_sha256": sha256_file(evaluation_path),
        "test_accuracy": _float(evaluation, "accuracy", context="evaluation file"),
        "test_macro_f1": _float(evaluation, "macro_f1", context="evaluation file"),
        "test_weighted_f1": _float(
            evaluation, "weighted_f1", context="evaluation file"
        ),
        "test_ece_calibrated": _float(evaluation, "ece", context="evaluation file"),
        "normal_false_positive_rate": normal_false_positive_rate,
        "attack_escape_rate": attack_escape_rate,
        "normal_recall": _float(normal, "recall", context="eval_report[Normal]"),
        "supported_attack_recall": supported_attack_recall,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--evaluation-file", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--dataset-version", default="v3_907k_cleaned")
    parser.add_argument("--preprocessing-version", default="http-preprocessor-v1")
    args = parser.parse_args(argv)
    summary = build_legacy_summary(
        artifact_dir=args.artifact_dir,
        evaluation_file=args.evaluation_file,
        output_path=args.output,
        dataset_version=args.dataset_version,
        preprocessing_version=args.preprocessing_version,
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
