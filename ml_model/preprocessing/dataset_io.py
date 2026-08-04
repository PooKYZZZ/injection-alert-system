from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np
import pandas as pd
from sklearn.preprocessing import LabelEncoder

from ml_model.preprocessing.model_input import (
    LEGACY_MODEL_INPUT_VERSION,
    MODEL_INPUT_HASH_POLICY,
    MODEL_INPUT_TEXT_COLUMN,
    MODEL_INPUT_VERSION,
    validate_model_input_version,
)
from ml_model.training.paths import default_training_output_dir, resolve_project_root

REPO_ROOT = resolve_project_root()
DEFAULT_RUNS_DIR = default_training_output_dir(project_root=REPO_ROOT)

_SPLIT_FILENAMES = ("train.parquet", "validation.parquet", "test.parquet")


def ensure_dir(path: Path) -> Path:
    path = Path(path)
    path.mkdir(parents=True, exist_ok=True)
    return path


def results_root(base_dir: Path | None = None) -> Path:
    root = DEFAULT_RUNS_DIR if base_dir is None else Path(base_dir)
    return ensure_dir(root)


def _split_files_exist(directory: Path) -> bool:
    directory = Path(directory)
    return all((directory / split_name).exists() for split_name in _SPLIT_FILENAMES)


def _resolve_split_root(data_dir: Path) -> Path:
    data_dir = Path(data_dir)
    if _split_files_exist(data_dir):
        return data_dir

    if data_dir.exists() and data_dir.is_dir():
        for child in sorted((child for child in data_dir.iterdir() if child.is_dir()), key=lambda path: path.name):
            if _split_files_exist(child):
                return child

    return data_dir


def load_dataset_metadata(data_dir: Path) -> dict[str, Any]:
    """Load the metadata next to a processed dataset, without fallback."""

    root = _resolve_split_root(Path(data_dir))
    metadata_path = root / "metadata_preprocessing.json"
    if not metadata_path.is_file():
        raise ValueError(f"Dataset is missing required preprocessing metadata: {metadata_path}")
    try:
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read dataset preprocessing metadata: {metadata_path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"Dataset preprocessing metadata must be an object: {metadata_path}")
    return payload


def validate_dataset_preprocessing(
    data_dir: Path,
    *,
    expected_dataset_version: str,
    expected_preprocessing_version: str = MODEL_INPUT_VERSION,
    expected_text_column: str = MODEL_INPUT_TEXT_COLUMN,
) -> dict[str, Any]:
    """Fail before training if dataset and model-input contracts differ."""

    metadata = load_dataset_metadata(data_dir)
    actual_dataset_version = metadata.get("dataset_version")
    legacy_dataset = expected_dataset_version == "v3_907k_cleaned" and (
        actual_dataset_version in {None, "SRBH_clean_v3.1.0", "v3_907k_cleaned"}
    )
    if actual_dataset_version != expected_dataset_version and not legacy_dataset:
        raise ValueError(
            f"Dataset version mismatch: requested {expected_dataset_version!r}, "
            f"metadata declares {actual_dataset_version!r}"
        )
    actual_preprocessing_version = metadata.get("preprocessing_version")
    if actual_preprocessing_version is None and legacy_dataset:
        actual_preprocessing_version = LEGACY_MODEL_INPUT_VERSION
        metadata = {
            **metadata,
            "dataset_version": expected_dataset_version,
            "preprocessing_version": actual_preprocessing_version,
            "text_column": expected_text_column,
            "model_input_hash_policy": MODEL_INPUT_HASH_POLICY,
        }
    if actual_preprocessing_version == LEGACY_MODEL_INPUT_VERSION and not legacy_dataset:
        raise ValueError("Legacy preprocessing is only supported for the known v3 dataset")
    if actual_preprocessing_version != expected_preprocessing_version:
        validate_model_input_version(
            actual_preprocessing_version, context="dataset"
        )
    if actual_preprocessing_version != expected_preprocessing_version:
        raise ValueError(
            f"Dataset preprocessing_version={metadata.get('preprocessing_version')!r} "
            f"does not match expected {expected_preprocessing_version!r}"
        )
    if metadata.get("text_column") != expected_text_column:
        raise ValueError(
            f"Dataset text_column={metadata.get('text_column')!r} does not match "
            f"expected {expected_text_column!r}"
        )
    if metadata.get("model_input_hash_policy") != MODEL_INPUT_HASH_POLICY:
        raise ValueError("Dataset model_input_hash_policy does not match the shared contract")
    return metadata


def resolve_data_dir(
    dataset_version: str,
    extra_candidates: Iterable[Path] | None = None,
    *,
    project_root: Path | None = None,
) -> Path:
    project_root = project_root or REPO_ROOT
    env_data_dir = os.environ.get("IAS_DATA_DIR")
    env_data_path = Path(env_data_dir).expanduser() if env_data_dir else None
    if env_data_path is not None and not env_data_path.is_absolute():
        env_data_path = project_root / env_data_path
    candidates = [
        (env_data_path / dataset_version) if env_data_path else None,
        env_data_path,
        project_root / "data" / "processed" / dataset_version,
        project_root / "ml_model" / "data" / "processed" / dataset_version,
        project_root / dataset_version,
    ]

    if extra_candidates is not None:
        candidates.extend(
            candidate if candidate.is_absolute() else project_root / candidate
            for candidate in extra_candidates
        )

    for candidate in [candidate for candidate in candidates if candidate is not None]:
        if candidate.exists():
            return candidate.resolve()

    raise FileNotFoundError(
        f"Could not locate dataset directory for {dataset_version}. Tried: "
        + ", ".join(str(c) for c in candidates)
    )


def make_output_dir(dataset_version: str, base_dir: Path | None = None) -> Path:
    base_dir = results_root(base_dir)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_dir = Path(base_dir) / f"{dataset_version}_{timestamp}"
    return ensure_dir(out_dir)


def latest_run_dir(base_dir: Path | None = None, dataset_version: str | None = None) -> Path:
    base_dir = results_root(base_dir)

    candidates = [p for p in base_dir.iterdir() if p.is_dir()]
    if dataset_version:
        candidates = [p for p in candidates if p.name.startswith(dataset_version)]

    if not candidates:
        raise FileNotFoundError(f"No benchmark run directories found in: {base_dir}")

    return sorted(candidates, key=lambda p: p.stat().st_mtime, reverse=True)[0]


def model_run_dir(run_dir: Path, model_key: str) -> Path:
    model_dir = Path(run_dir) / model_key
    return ensure_dir(model_dir)


def loss_variant_dir(model_dir: Path, loss_key: str) -> Path:
    return ensure_dir(Path(model_dir) / f"loss_{loss_key}")


def seed_run_dir(parent_dir: Path, seed: int) -> Path:
    return ensure_dir(Path(parent_dir) / f"seed_{int(seed):04d}")


def evaluation_dir(run_dir: Path) -> Path:
    return ensure_dir(Path(run_dir) / "evaluation")


def checkpoint_dir(model_dir: Path) -> Path:
    return ensure_dir(Path(model_dir) / "checkpoint")


def _json_default(value: Any):
    if isinstance(value, (np.integer, np.floating)):
        return value.item()
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def save_json(path: Path, payload: Any) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=_json_default)


def save_csv(df: pd.DataFrame, path: Path, *, index: bool = False) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    df.to_csv(path, index=index)


def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_numpy_artifacts(path: Path, **arrays: np.ndarray) -> None:
    path = Path(path)
    ensure_dir(path.parent)
    np.savez_compressed(path, **arrays)


def load_numpy_artifacts(path: Path) -> dict[str, np.ndarray]:
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key] for key in data.files}


def validate_required_columns(df: pd.DataFrame, split_name: str, required_columns: Sequence[str]):
    missing = [col for col in required_columns if col not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {split_name}: {missing}")


def load_data_splits(data_dir: Path, text_col: str, label_col: str):
    data_dir = _resolve_split_root(data_dir)
    split_paths = {
        "train": data_dir / "train.parquet",
        "validation": data_dir / "validation.parquet",
        "test": data_dir / "test.parquet",
    }
    for split_name, path in split_paths.items():
        if not path.exists():
            raise FileNotFoundError(f"Expected split file not found: {path}")

    df_train = pd.read_parquet(split_paths["train"]).copy()
    df_val = pd.read_parquet(split_paths["validation"]).copy()
    df_test = pd.read_parquet(split_paths["test"]).copy()

    required_columns = [text_col, label_col]
    validate_required_columns(df_train, "train", required_columns)
    validate_required_columns(df_val, "validation", required_columns)
    validate_required_columns(df_test, "test", required_columns)

    for split_name, df_split in {
        "train": df_train,
        "validation": df_val,
        "test": df_test,
    }.items():
        if df_split[text_col].isna().any():
            raise ValueError(f"NaN text values found in {split_name} split")
        if df_split[label_col].isna().any():
            raise ValueError(f"NaN labels found in {split_name} split")

    return df_train, df_val, df_test


def encode_labels(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
    label_col: str,
    expected_classes: Sequence[str],
):
    label_encoder = LabelEncoder()
    label_encoder.fit(df_train[label_col])

    label_names = list(label_encoder.classes_)
    if set(label_names) != set(expected_classes):
        raise ValueError(f"Label mismatch. Found={set(label_names)} | Expected={set(expected_classes)}")

    for df_split in (df_train, df_val, df_test):
        df_split["label_id"] = label_encoder.transform(df_split[label_col])

    return label_encoder, label_names


def split_size_and_distribution(df_split: pd.DataFrame, label_col: str) -> dict[str, Any]:
    distribution = df_split[label_col].value_counts().to_dict()
    return {
        "size": int(len(df_split)),
        "class_distribution": {str(label): int(count) for label, count in distribution.items()},
    }


def build_split_summaries(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
    label_col: str,
) -> dict[str, dict[str, Any]]:
    return {
        "train": split_size_and_distribution(df_train, label_col),
        "validation": split_size_and_distribution(df_val, label_col),
        "test": split_size_and_distribution(df_test, label_col),
    }


def _hash_text_column(df_split: pd.DataFrame, text_col: str) -> np.ndarray:
    text_series = df_split[text_col].astype(str)
    return pd.util.hash_pandas_object(text_series, index=False).values.astype(np.uint64, copy=False)


def compute_cross_split_overlap_counts(
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
    text_col: str,
) -> dict[str, int]:
    train_hash = np.unique(_hash_text_column(df_train, text_col))
    val_hash = np.unique(_hash_text_column(df_val, text_col))
    test_hash = np.unique(_hash_text_column(df_test, text_col))

    return {
        "train_validation_overlap": int(np.intersect1d(train_hash, val_hash).size),
        "train_test_overlap": int(np.intersect1d(train_hash, test_hash).size),
        "validation_test_overlap": int(np.intersect1d(val_hash, test_hash).size),
    }


def _try_load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = load_json(path)
    except Exception:
        return None
    if isinstance(payload, dict):
        return payload
    return {"raw_payload": payload}


def load_existing_split_hygiene_metadata(data_dir: Path) -> dict[str, Any]:
    data_dir = Path(data_dir)
    candidates = [
        data_dir / "split_metadata.json",
        data_dir / "split_hygiene.json",
        data_dir / "hygiene_metadata.json",
        data_dir / "preprocessing_metadata.json",
        data_dir / "dataset_metadata.json",
    ]

    discovered: dict[str, Any] = {}
    for candidate in candidates:
        if not candidate.exists():
            continue
        loaded = _try_load_json(candidate)
        if loaded is None:
            continue
        discovered[str(candidate)] = loaded

    return discovered


def build_split_hygiene_evidence(
    data_dir: Path,
    split_summaries: dict[str, dict[str, Any]],
    df_train: pd.DataFrame,
    df_val: pd.DataFrame,
    df_test: pd.DataFrame,
    text_col: str,
) -> dict[str, Any]:
    metadata_sources = load_existing_split_hygiene_metadata(data_dir)
    overlap_counts = compute_cross_split_overlap_counts(df_train, df_val, df_test, text_col)
    has_zero_overlap = all(value == 0 for value in overlap_counts.values())

    evidence = {
        "split_strategy": "precomputed train/validation/test parquet splits loaded from processed dataset directory",
        "split_sizes": {
            split_name: int(split_info["size"]) for split_name, split_info in split_summaries.items()
        },
        "class_distributions": {
            split_name: split_info["class_distribution"] for split_name, split_info in split_summaries.items()
        },
        "deduplication_status": "unknown",
        "near_duplicate_handling_status": "unknown",
        "label_cleaning_or_quarantine_notes": "unknown",
        "cross_split_overlap_counts": overlap_counts,
        "zero_cross_split_overlap": bool(has_zero_overlap),
        "metadata_sources": metadata_sources,
        "evidence_gaps": [],
    }

    if metadata_sources:
        evidence["deduplication_status"] = "documented_upstream"
        evidence["near_duplicate_handling_status"] = "documented_upstream_or_noted_in_metadata"
        evidence["label_cleaning_or_quarantine_notes"] = "refer_to_metadata_sources"
    else:
        evidence["evidence_gaps"].extend(
            [
                "Upstream split metadata was not found in the processed dataset directory.",
                "Near-duplicate handling evidence is not available in current artifacts.",
                "Label cleaning/quarantine notes are not available in current artifacts.",
            ]
        )

    if not has_zero_overlap:
        evidence["evidence_gaps"].append(
            "Cross-split overlap counts are non-zero and require upstream deduplication review."
        )

    return evidence
