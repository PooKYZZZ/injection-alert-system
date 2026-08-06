"""Deterministic cumulative training snapshots for the offline experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import pandas as pd

from ml_model.retraining.experiment_contract import canonical_json_sha256, sha256_file


@dataclass(frozen=True)
class SnapshotResult:
    snapshot_dir: Path
    train_rows: int
    validation_rows: int
    test_rows: int
    input_hash: str
    output_hash: str
    manifest: dict[str, Any]


def _safe_output_root(
    output_root: Path, historical_data_dir: Path, dataset_version: str
) -> None:
    output_root = output_root.resolve()
    historical = historical_data_dir.resolve()
    if output_root == historical or historical in output_root.parents:
        raise ValueError("snapshot output must not be inside the historical dataset")
    established = (historical.parent / dataset_version).resolve()
    if output_root == established or established in output_root.parents:
        raise ValueError("snapshot output must not overwrite the established dataset")


def _load_split(root: Path, split: str) -> pd.DataFrame:
    path = root / f"{split}.parquet"
    if not path.is_file():
        raise FileNotFoundError(f"historical {split} split is missing: {path}")
    frame = pd.read_parquet(path).copy()
    required = {"combined_payload", "final_label"}
    missing = sorted(required - set(frame.columns))
    if missing:
        raise ValueError(f"historical {split} split is missing columns: {missing}")
    return frame


def _daily_frame(samples: Sequence[Mapping[str, Any]]) -> pd.DataFrame:
    rows = []
    for sample in sorted(samples, key=lambda row: str(row.get("sample_id", ""))):
        rows.append(
            {
                "combined_payload": str(sample["model_input_text"]),
                "final_label": str(sample["ground_truth_label"]),
                "sample_id": str(sample["sample_id"]),
                "source_type": str(sample["source_type"]),
                "batch_day": int(sample["batch_day"]),
                "is_synthetic": bool(sample["is_synthetic"]),
                "provenance_id": str(sample["provenance_id"]),
                "preprocessing_version": str(sample["preprocessing_version"]),
            }
        )
    return pd.DataFrame(rows)


def _validate_daily_samples(
    samples: Sequence[Mapping[str, Any]],
    historical_frames: Sequence[pd.DataFrame],
) -> None:
    historical_texts: dict[str, str] = {}
    for frame in historical_frames:
        for text, label in zip(
            frame["combined_payload"].astype(str), frame["final_label"].astype(str)
        ):
            historical_texts.setdefault(text, label)
    seen_ids: set[str] = set()
    seen_texts: dict[str, str] = {}
    for sample in samples:
        sample_id = str(sample["sample_id"])
        text = str(sample["model_input_text"])
        label = str(sample["ground_truth_label"])
        if sample_id in seen_ids:
            raise ValueError(f"duplicate daily sample_id: {sample_id}")
        seen_ids.add(sample_id)
        if text in historical_texts:
            raise ValueError(f"daily sample overlaps historical data: {sample_id}")
        if text in seen_texts:
            if seen_texts[text] != label:
                raise ValueError(f"conflicting daily label for: {sample_id}")
            raise ValueError(f"duplicate daily text for: {sample_id}")
        seen_texts[text] = label


def build_cumulative_snapshot(
    *,
    historical_data_dir: Path | str,
    cumulative_samples: Sequence[Mapping[str, Any]],
    output_root: Path | str,
    day: int,
    dataset_version: str,
    preprocessing_version: str,
) -> SnapshotResult:
    if not 1 <= int(day) <= 20:
        raise ValueError("simulation day must be between 1 and 20")
    historical_root = Path(historical_data_dir).expanduser().resolve()
    output_root = Path(output_root).expanduser().resolve()
    _safe_output_root(output_root, historical_root, dataset_version)
    historical = [
        _load_split(historical_root, split) for split in ("train", "validation", "test")
    ]
    _validate_daily_samples(cumulative_samples, historical)
    daily = _daily_frame(cumulative_samples)
    train = pd.concat([historical[0], daily], ignore_index=True, sort=False)
    snapshot_dir = output_root / f"day_{int(day):02d}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    split_frames = {"train": train, "validation": historical[1], "test": historical[2]}
    for split, frame in split_frames.items():
        frame.to_parquet(snapshot_dir / f"{split}.parquet", index=False)

    input_files = {
        split: sha256_file(historical_root / f"{split}.parquet")
        for split in ("train", "validation", "test")
    }
    input_hash = canonical_json_sha256(
        {
            "historical_files": input_files,
            "cumulative_samples": list(cumulative_samples),
            "dataset_version": dataset_version,
            "preprocessing_version": preprocessing_version,
        }
    )
    output_files = {
        split: sha256_file(snapshot_dir / f"{split}.parquet")
        for split in ("train", "validation", "test")
    }
    manifest: dict[str, Any] = {
        "snapshot_version": "retraining-snapshot.v1",
        "day": int(day),
        "dataset_version": dataset_version,
        "preprocessing_version": preprocessing_version,
        "historical_data_dir": "data/processed/" + dataset_version,
        "cumulative_sample_count": len(cumulative_samples),
        "train_rows": int(len(train)),
        "validation_rows": int(len(historical[1])),
        "test_rows": int(len(historical[2])),
        "input_hash": input_hash,
        "output_files": output_files,
        "class_distribution": {
            str(label): int(count)
            for label, count in train["final_label"].value_counts().sort_index().items()
        },
        "source_distribution": {
            str(source): int(count)
            for source, count in (
                train["source_type"]
                if "source_type" in train.columns
                else pd.Series(["historical"] * len(train))
            )
            .fillna("historical")
            .value_counts()
            .sort_index()
            .items()
        },
    }
    manifest["manifest_sha256"] = canonical_json_sha256(manifest)
    (snapshot_dir / "snapshot_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    output_hash = canonical_json_sha256(output_files)
    return SnapshotResult(
        snapshot_dir=snapshot_dir,
        train_rows=int(len(train)),
        validation_rows=int(len(historical[1])),
        test_rows=int(len(historical[2])),
        input_hash=input_hash,
        output_hash=output_hash,
        manifest=manifest,
    )
