"""Candidate-artifact contract checks for the retraining simulator."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from ml_model.retraining.experiment_contract import ExperimentConfig, sha256_file
from ml_model.training.run_contract import require_contract_hash


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
