"""Candidate-artifact contract checks for the retraining simulator."""

from __future__ import annotations

import hmac
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ml_model.retraining.experiment_contract import (
    ExperimentConfig,
    canonical_json_sha256,
    sha256_file,
)
from ml_model.training.run_contract import require_contract_hash

REQUIRED_TRAINING_SUMMARY_METRICS = (
    "test_accuracy",
    "test_macro_f1",
    "test_weighted_f1",
    "normal_false_positive_rate",
    "attack_escape_rate",
)
SUMMARY_METRICS_HASH_EXCLUDED_FIELDS = frozenset({"artifact_manifest_sha256"})


@dataclass(frozen=True)
class CandidateContractResult:
    passed: bool
    checks: dict[str, bool]
    failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "checks": self.checks,
            "failures": list(self.failures),
        }


def _load_json(path: Path) -> Mapping[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"candidate contract file is missing: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping):
        raise ValueError(f"candidate contract file must contain an object: {path}")
    return payload


def validate_training_summary_payload(payload: Any) -> dict[str, Any]:
    """Validate and normalize the required JSON numeric summary fields."""

    if not isinstance(payload, Mapping):
        raise ValueError("summary_metrics.json must contain an object")

    missing = [
        key
        for key in REQUIRED_TRAINING_SUMMARY_METRICS
        if key not in payload
    ]
    if missing:
        raise ValueError(
            "Training summary is missing required metrics: "
            f"{sorted(missing)}"
        )

    normalized = dict(payload)
    for key in REQUIRED_TRAINING_SUMMARY_METRICS:
        value = payload[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"Training summary metric {key!r} must be a JSON number"
            )
        numeric_value = float(value)
        if not math.isfinite(numeric_value):
            raise ValueError(
                f"Training summary metric {key!r} must be finite"
            )
        normalized[key] = numeric_value
    return normalized


def canonical_summary_metrics_sha256(payload: Mapping[str, Any]) -> str:
    """Hash summary content while excluding the non-cyclic manifest back-link."""

    unsigned = {
        key: value
        for key, value in payload.items()
        if key not in SUMMARY_METRICS_HASH_EXCLUDED_FIELDS
    }
    return canonical_json_sha256(unsigned)


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(
        character in "0123456789abcdefABCDEF" for character in value
    )


def _read_json_object(path: Path, description: str) -> Mapping[str, Any]:
    if not path.is_file():
        raise ValueError(f"{description} is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{description} is malformed: {path}") from exc
    if not isinstance(payload, Mapping):
        raise ValueError(f"{description} must contain an object")
    return payload


def verify_summary_metrics_provenance(
    *,
    artifact_dir: Path,
    manifest_path: Path,
    manifest: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Verify the immutable summary and its links to the packaged artifact."""

    del manifest
    artifact = Path(artifact_dir)
    trusted_manifest = _read_json_object(
        Path(manifest_path), "serving_manifest.json"
    )
    summary_path = artifact / "summary_metrics.json"
    payload = _read_json_object(summary_path, "summary_metrics.json")

    expected_summary_hash = trusted_manifest.get("summary_metrics_sha256")
    if not _is_sha256(expected_summary_hash):
        raise ValueError(
            "serving manifest is missing a valid summary metrics content hash"
        )
    actual_summary_hash = canonical_summary_metrics_sha256(payload)
    if not hmac.compare_digest(expected_summary_hash, actual_summary_hash):
        raise ValueError("summary metrics content hash does not match manifest")

    normalized_payload = validate_training_summary_payload(payload)
    source_summary_hash = normalized_payload.get("source_summary_sha256")
    if not _is_sha256(source_summary_hash):
        raise ValueError(
            "summary metrics source summary hash is missing or invalid"
        )

    checkpoint_name = trusted_manifest.get("checkpoint_file")
    if not isinstance(checkpoint_name, str) or not checkpoint_name:
        raise ValueError("serving_manifest.json is missing checkpoint_file")
    checkpoint_path = artifact / checkpoint_name
    if not checkpoint_path.is_file():
        raise ValueError("serving manifest checkpoint_file does not exist")
    checkpoint_hash = sha256_file(checkpoint_path)
    manifest_checkpoint_hash = trusted_manifest.get("checkpoint_sha256")
    if not isinstance(manifest_checkpoint_hash, str) or not hmac.compare_digest(
        manifest_checkpoint_hash, checkpoint_hash
    ):
        raise ValueError("staged checkpoint hash does not match manifest")
    summary_checkpoint_hash = normalized_payload.get("checkpoint_sha256")
    if not isinstance(summary_checkpoint_hash, str) or not hmac.compare_digest(
        summary_checkpoint_hash, checkpoint_hash
    ):
        raise ValueError("summary metrics checkpoint hash does not match artifact")

    manifest_hash = sha256_file(Path(manifest_path))
    summary_manifest_hash = normalized_payload.get("artifact_manifest_sha256")
    if not isinstance(summary_manifest_hash, str) or not hmac.compare_digest(
        summary_manifest_hash, manifest_hash
    ):
        raise ValueError(
            "summary metrics artifact manifest hash does not match artifact"
        )
    return normalized_payload


def _same_float_mapping(actual: Any, expected: Mapping[str, float]) -> bool:
    if not isinstance(actual, Mapping):
        return False
    try:
        return {key: float(value) for key, value in actual.items()} == {
            key: float(value) for key, value in expected.items()
        }
    except (TypeError, ValueError):
        return False


def validate_candidate_contract(
    *,
    config: ExperimentConfig,
    artifact_dir: Path | str,
    snapshot_manifest: Mapping[str, Any],
) -> CandidateContractResult:
    artifact = Path(artifact_dir).expanduser().resolve()
    checks = {
        "label_mapping_unchanged": False,
        "preprocessing_unchanged": False,
        "model_revision_unchanged": False,
        "thresholds_unchanged": False,
        "action_mapping_unchanged": False,
        "dataset_hash_verified": False,
        "tokenizer_identity_verified": False,
        "best_checkpoint_selected": False,
        "artifact_identity_verified": False,
    }
    failures: list[str] = []
    try:
        manifest = _load_json(artifact / "serving_manifest.json")
        config_used = _load_json(artifact / "config_used.json")
        checkpoint_path = artifact / "best_distilbert_ckpt.pt"
        run_contract_hash = require_contract_hash(config_used)
        run_contract = config_used["run_contract"]
        model_contract = run_contract["model_contracts"]["distilbert"]

        checks["label_mapping_unchanged"] = (
            list(manifest.get("label_names", [])) == list(config.label_names)
            and list(run_contract.get("label_names", [])) == list(config.label_names)
        )
        checks["preprocessing_unchanged"] = (
            manifest.get("preprocessing_version") == config.preprocessing_version
            and run_contract.get("preprocessing_version")
            == config.preprocessing_version
            and manifest.get("model_input_hash_policy")
            == "sha256(model_input_text)"
        )
        checks["model_revision_unchanged"] = (
            manifest.get("model_revision") == config.model_revision
            and model_contract.get("model_revision") == config.model_revision
            and model_contract.get("model_id") == config.model_id
        )
        checks["thresholds_unchanged"] = _same_float_mapping(
            manifest.get("confidence_thresholds"), config.confidence_thresholds
        )
        checks["action_mapping_unchanged"] = (
            manifest.get("response_actions") == config.response_actions
        )
        expected_dataset_hash = snapshot_manifest.get(
            "dataset_file_manifest_sha256"
        )
        checks["dataset_hash_verified"] = (
            isinstance(expected_dataset_hash, str)
            and run_contract.get("dataset_file_manifest_sha256")
            == expected_dataset_hash
            and manifest.get("dataset_file_manifest_sha256") == expected_dataset_hash
        )
        checks["tokenizer_identity_verified"] = (
            manifest.get("tokenizer_id") == config.model_id
            and manifest.get("tokenizer_revision") == config.model_revision
        )
        checks["best_checkpoint_selected"] = (
            manifest.get("checkpoint_file") == checkpoint_path.name
            and checkpoint_path.is_file()
        )
        checks["artifact_identity_verified"] = (
            manifest.get("run_contract_sha256") == run_contract_hash
            and manifest.get("local_reload_verified") is True
            and checkpoint_path.is_file()
            and manifest.get("checkpoint_sha256") == sha256_file(checkpoint_path)
            and manifest.get("config_used_sha256")
            == sha256_file(artifact / "config_used.json")
        )
    except (FileNotFoundError, KeyError, TypeError, ValueError, OSError) as exc:
        failures.append(str(exc))

    failures.extend(
        name for name, passed in checks.items() if not passed and name not in failures
    )
    return CandidateContractResult(
        passed=not failures,
        checks=checks,
        failures=tuple(failures),
    )
