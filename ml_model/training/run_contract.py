"""Deterministic provenance contract for resumable training runs."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from typing import Any

CONTRACT_VERSION = "training-run-contract.v1"
CONTRACT_HASH_FIELD = "run_contract_sha256"


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
            raise ValueError("model_contracts are required when more than one model is selected")
        if not all(isinstance(value, str) and value.strip() for value in (model_id, model_revision, architecture)):
            raise ValueError(
                "single-model contract requires model_id, model_revision, and architecture"
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
    model_contracts: Mapping[str, Mapping[str, Any]] | None = None,
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
    contract: dict[str, Any] = {
        "contract_version": CONTRACT_VERSION,
        "dataset_version": dataset_version.strip(),
        "preprocessing_version": preprocessing_version.strip(),
        "model_keys": normalized_model_keys,
        "model_contracts": normalized_contracts,
        "seed_list": [int(value) for value in seed_list],
        "loss_keys": [str(value).strip() for value in loss_keys],
        "max_seq_len": int(max_seq_len),
        "batch_size": int(batch_size),
        "eval_batch_size": int(eval_batch_size),
        "epochs": int(epochs),
        "learning_rate": float(learning_rate),
        "gradient_accumulation_steps": int(gradient_accumulation_steps),
    }
    if len(normalized_contracts) == 1:
        single = next(iter(normalized_contracts.values()))
        contract.update(single)
    return contract


def require_contract_hash(payload: Mapping[str, Any]) -> str:
    """Return a stored contract hash, rejecting metadata from legacy runs."""

    value = payload.get(CONTRACT_HASH_FIELD)
    if not isinstance(value, str) or len(value) != 64:
        raise ValueError(f"metadata is missing a valid {CONTRACT_HASH_FIELD}")
    try:
        int(value, 16)
    except ValueError as exc:
        raise ValueError(f"metadata is missing a valid {CONTRACT_HASH_FIELD}") from exc
    return value
