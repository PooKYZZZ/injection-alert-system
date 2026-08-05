"""Deterministic provenance contract for resumable training runs."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from typing import Any

CONTRACT_VERSION = "training-run-contract.v2"
CONTRACT_HASH_FIELD = "run_contract_sha256"

_REQUIRED_CONTRACT_FIELDS = frozenset(
    {
        "contract_version",
        "dataset_version",
        "preprocessing_version",
        "model_keys",
        "model_contracts",
        "training_settings_by_model",
        "seed_list",
        "loss_keys",
        "max_seq_len",
        "batch_size",
        "eval_batch_size",
        "epochs",
        "learning_rate",
        "gradient_accumulation_steps",
        "dataset_file_manifest_sha256",
        "label_names",
        "class_mapping",
        "loss_contracts",
        "weight_decay",
        "warmup_ratio",
        "sample_limits",
        "precision",
        "training_implementation_version",
    }
)


def canonical_json(payload: Mapping[str, Any]) -> str:
    """Serialize a contract deterministically without machine-specific noise."""

    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def contract_sha256(payload: Mapping[str, Any]) -> str:
    """Return the SHA-256 identity of a canonical contract payload."""

    canonical = canonical_json(payload).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _require_non_empty_string(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"model contract requires non-empty {key}")
    return value.strip()


def _normalize_model_contracts(
    model_keys: Sequence[str],
    model_contracts: Mapping[str, Mapping[str, Any]] | None,
    *,
    model_id: str | None,
    model_revision: str | None,
    architecture: str | None,
) -> dict[str, dict[str, str]]:
    if model_contracts is None:
        if len(model_keys) != 1:
            raise ValueError(
                "model_contracts are required when more than one model is selected"
            )
        if not all(
            isinstance(value, str) and value.strip()
            for value in (model_id, model_revision, architecture)
        ):
            raise ValueError(
                "single-model contract requires model_id, model_revision, "
                "and architecture"
            )
        model_contracts = {
            model_keys[0]: {
                "model_id": model_id,
                "model_revision": model_revision,
                "architecture": architecture,
            }
        }

    normalized: dict[str, dict[str, str]] = {}
    for model_key in model_keys:
        if not isinstance(model_key, str) or not model_key.strip():
            raise ValueError("model_keys must contain non-empty strings")
        raw = model_contracts.get(model_key)
        if not isinstance(raw, Mapping):
            raise ValueError(f"missing model contract for {model_key!r}")
        normalized[model_key] = {
            "model_id": _require_non_empty_string(raw, "model_id"),
            "model_revision": _require_non_empty_string(raw, "model_revision"),
            "architecture": _require_non_empty_string(raw, "architecture"),
        }
    if set(normalized) != set(model_contracts):
        raise ValueError("model_contracts must match model_keys exactly")
    return normalized


def _normalize_label_contract(
    label_names: Sequence[str],
    class_mapping: Mapping[str, Any] | None,
) -> tuple[list[str], dict[str, int]]:
    normalized_labels = [str(value).strip() for value in label_names]
    if not normalized_labels or any(not value for value in normalized_labels):
        raise ValueError("label_names must contain non-empty strings")
    if len(set(normalized_labels)) != len(normalized_labels):
        raise ValueError("label_names must be unique and ordered")
    if class_mapping is None:
        class_mapping = {
            label: index for index, label in enumerate(normalized_labels)
        }
    if set(class_mapping) != set(normalized_labels):
        raise ValueError("class_mapping must match label_names exactly")
    raw_mapping = {str(label): int(index) for label, index in class_mapping.items()}
    normalized_mapping = {label: raw_mapping[label] for label in normalized_labels}
    if sorted(normalized_mapping.values()) != list(range(len(normalized_labels))):
        raise ValueError("class_mapping values must be contiguous class ids")
    return normalized_labels, normalized_mapping


def _normalize_loss_contracts(
    loss_keys: Sequence[str],
    loss_contracts: Mapping[str, Mapping[str, Any]] | None,
) -> dict[str, dict[str, Any]]:
    normalized_loss_keys = [str(value).strip() for value in loss_keys]
    if any(not value for value in normalized_loss_keys):
        raise ValueError("loss_keys must contain non-empty strings")
    if loss_contracts is None:
        loss_contracts = {
            loss_key: {"focal_gamma": None} for loss_key in normalized_loss_keys
        }
    if set(loss_contracts) != set(normalized_loss_keys):
        raise ValueError("loss_contracts must match loss_keys exactly")
    normalized: dict[str, dict[str, Any]] = {}
    for loss_key in normalized_loss_keys:
        raw = loss_contracts[loss_key]
        if not isinstance(raw, Mapping):
            raise ValueError(f"loss contract for {loss_key!r} must be an object")
        normalized[loss_key] = dict(raw)
    return normalized


def _normalize_sample_limits(
    sample_limits: Mapping[str, Any] | None,
) -> dict[str, int | None]:
    sample_limits = sample_limits or {"train": None, "validation": None, "test": None}
    expected_splits = {"train", "validation", "test"}
    if set(sample_limits) != expected_splits:
        raise ValueError("sample_limits must contain train, validation, and test")
    normalized: dict[str, int | None] = {}
    for split in ("train", "validation", "test"):
        value = sample_limits[split]
        if value is not None and int(value) < 1:
            raise ValueError(f"sample_limits[{split!r}] must be positive or null")
        normalized[split] = None if value is None else int(value)
    return normalized


def _normalize_training_settings_by_model(
    model_keys: Sequence[str],
    training_settings_by_model: Mapping[str, Mapping[str, Any]] | None,
    *,
    learning_rate: float,
    batch_size: int,
    eval_batch_size: int,
    gradient_accumulation_steps: int,
    weight_decay: float,
    warmup_ratio: float,
    max_seq_len: int,
    epochs: int,
) -> dict[str, dict[str, Any]]:
    """Preserve the resolved settings for every selected model."""

    if training_settings_by_model is None:
        fallback = {
            "learning_rate": float(learning_rate),
            "per_device_train_batch_size": int(batch_size),
            "eval_batch_size": int(eval_batch_size),
            "gradient_accumulation_steps": int(gradient_accumulation_steps),
            "weight_decay": float(weight_decay),
            "warmup_ratio": float(warmup_ratio),
            "max_seq_len": int(max_seq_len),
            "num_train_epochs": int(epochs),
        }
        return {model_key: dict(fallback) for model_key in model_keys}

    if not isinstance(training_settings_by_model, Mapping):
        raise ValueError("training_settings_by_model must be an object")
    if set(training_settings_by_model) != set(model_keys):
        raise ValueError("training_settings_by_model must match model_keys exactly")

    normalized: dict[str, dict[str, Any]] = {}
    for model_key in model_keys:
        raw = training_settings_by_model[model_key]
        if not isinstance(raw, Mapping) or not raw:
            raise ValueError(
                f"training settings for {model_key!r} must be a non-empty object"
            )
        normalized[model_key] = dict(raw)
    return normalized


def build_training_run_contract(
    *,
    dataset_version: str,
    preprocessing_version: str,
    model_keys: Sequence[str],
    seed_list: Sequence[int],
    loss_keys: Sequence[str],
    max_seq_len: int,
    batch_size: int,
    eval_batch_size: int,
    epochs: int,
    learning_rate: float,
    gradient_accumulation_steps: int,
    dataset_file_manifest_sha256: str,
    label_names: Sequence[str] = ("unresolved",),
    class_mapping: Mapping[str, Any] | None = None,
    loss_contracts: Mapping[str, Mapping[str, Any]] | None = None,
    weight_decay: float = 0.0,
    warmup_ratio: float = 0.0,
    sample_limits: Mapping[str, Any] | None = None,
    precision: str = "unresolved",
    training_implementation_version: str = "training-implementation.v1",
    model_contracts: Mapping[str, Mapping[str, Any]] | None = None,
    training_settings_by_model: Mapping[str, Mapping[str, Any]] | None = None,
    model_id: str | None = None,
    model_revision: str | None = None,
    architecture: str | None = None,
) -> dict[str, Any]:
    """Build only the stable inputs that determine a training run's identity."""

    if not isinstance(dataset_version, str) or not dataset_version.strip():
        raise ValueError("dataset_version must be non-empty")
    if not isinstance(preprocessing_version, str) or not preprocessing_version.strip():
        raise ValueError("preprocessing_version must be non-empty")
    if not model_keys:
        raise ValueError("model_keys must not be empty")
    if not seed_list:
        raise ValueError("seed_list must not be empty")
    if not loss_keys:
        raise ValueError("loss_keys must not be empty")

    normalized_model_keys = [str(value).strip() for value in model_keys]
    normalized_contracts = _normalize_model_contracts(
        normalized_model_keys,
        model_contracts,
        model_id=model_id,
        model_revision=model_revision,
        architecture=architecture,
    )
    if not isinstance(dataset_file_manifest_sha256, str) or not re.fullmatch(
        r"[0-9a-f]{64}", dataset_file_manifest_sha256
    ):
        raise ValueError("dataset_file_manifest_sha256 must be a lowercase SHA-256 digest")
    if not isinstance(precision, str) or not precision.strip():
        raise ValueError("precision must be non-empty")
    if not isinstance(training_implementation_version, str) or not training_implementation_version.strip():
        raise ValueError("training_implementation_version must be non-empty")
    normalized_labels, normalized_class_mapping = _normalize_label_contract(
        label_names, class_mapping
    )
    normalized_loss_contracts = _normalize_loss_contracts(loss_keys, loss_contracts)
    normalized_sample_limits = _normalize_sample_limits(sample_limits)
    normalized_training_settings = _normalize_training_settings_by_model(
        normalized_model_keys,
        training_settings_by_model,
        learning_rate=float(learning_rate),
        batch_size=int(batch_size),
        eval_batch_size=int(eval_batch_size),
        gradient_accumulation_steps=int(gradient_accumulation_steps),
        weight_decay=float(weight_decay),
        warmup_ratio=float(warmup_ratio),
        max_seq_len=int(max_seq_len),
        epochs=int(epochs),
    )
    contract: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "dataset_version": dataset_version.strip(),
        "preprocessing_version": preprocessing_version.strip(),
        "model_keys": normalized_model_keys,
        "model_contracts": normalized_contracts,
        "training_settings_by_model": normalized_training_settings,
        "seed_list": [int(value) for value in seed_list],
        "loss_keys": [str(value).strip() for value in loss_keys],
        "max_seq_len": int(max_seq_len),
        "batch_size": int(batch_size),
        "eval_batch_size": int(eval_batch_size),
        "epochs": int(epochs),
        "learning_rate": float(learning_rate),
        "gradient_accumulation_steps": int(gradient_accumulation_steps),
        "dataset_file_manifest_sha256": dataset_file_manifest_sha256.strip(),
        "label_names": normalized_labels,
        "class_mapping": normalized_class_mapping,
        "loss_contracts": normalized_loss_contracts,
        "weight_decay": float(weight_decay),
        "warmup_ratio": float(warmup_ratio),
        "sample_limits": normalized_sample_limits,
        "precision": precision.strip(),
        "training_implementation_version": training_implementation_version.strip(),
    }
    if len(normalized_contracts) == 1:
        single = next(iter(normalized_contracts.values()))
        contract.update(single)
    return contract


def validate_training_run_contract(contract: Mapping[str, Any]) -> None:
    """Validate the persisted v2 contract before accepting its hash."""

    if not isinstance(contract, Mapping):
        raise ValueError("run_contract must be an object")
    if contract.get("contract_version") != CONTRACT_VERSION:
        raise ValueError(
            "run_contract contract_version must be "
            f"{CONTRACT_VERSION!r}"
        )
    missing = sorted(_REQUIRED_CONTRACT_FIELDS - set(contract))
    if missing:
        raise ValueError(
            "run_contract is missing required fields: " + ", ".join(missing)
        )

    model_keys = contract["model_keys"]
    if (
        not isinstance(model_keys, Sequence)
        or isinstance(model_keys, (str, bytes))
        or not model_keys
    ):
        raise ValueError("run_contract model_keys must be a non-empty list")
    if not isinstance(contract["model_contracts"], Mapping):
        raise ValueError("run_contract model_contracts must be an object")
    _normalize_model_contracts(
        model_keys,
        contract["model_contracts"],
        model_id=None,
        model_revision=None,
        architecture=None,
    )
    _normalize_training_settings_by_model(
        model_keys,
        contract["training_settings_by_model"],
        learning_rate=float(contract["learning_rate"]),
        batch_size=int(contract["batch_size"]),
        eval_batch_size=int(contract["eval_batch_size"]),
        gradient_accumulation_steps=int(contract["gradient_accumulation_steps"]),
        weight_decay=float(contract["weight_decay"]),
        warmup_ratio=float(contract["warmup_ratio"]),
        max_seq_len=int(contract["max_seq_len"]),
        epochs=int(contract["epochs"]),
    )
    if not isinstance(contract["dataset_file_manifest_sha256"], str) or not re.fullmatch(
        r"[0-9a-f]{64}", contract["dataset_file_manifest_sha256"]
    ):
        raise ValueError("run_contract dataset_file_manifest_sha256 is invalid")
    _normalize_label_contract(contract["label_names"], contract["class_mapping"])
    _normalize_loss_contracts(contract["loss_keys"], contract["loss_contracts"])
    _normalize_sample_limits(contract["sample_limits"])


def _validate_persisted_contract(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    contract = payload.get("run_contract")
    if not isinstance(contract, Mapping):
        raise ValueError("metadata is missing a complete run_contract")
    validate_training_run_contract(contract)
    return contract


def require_contract_hash(payload: Mapping[str, Any]) -> str:
    """Return a stored hash only for a complete, current contract."""

    value = payload.get(CONTRACT_HASH_FIELD)
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ValueError(f"metadata is missing a valid {CONTRACT_HASH_FIELD}")
    contract = _validate_persisted_contract(payload)
    if contract_sha256(contract) != value:
        raise ValueError(f"metadata has an inconsistent {CONTRACT_HASH_FIELD}")
    return value
