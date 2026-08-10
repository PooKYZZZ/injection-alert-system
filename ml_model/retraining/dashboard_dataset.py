"""Versioned local dataset snapshots for dashboard retraining runs."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Sequence

import pandas as pd

from ml_model.evaluation.golden_controls import (
    GoldenControlError,
    find_golden_overlap,
    load_golden_controls,
)
from ml_model.preprocessing.dataset_io import (
    load_data_splits,
    load_dataset_file_manifest,
    validate_dataset_preprocessing,
)
from ml_model.preprocessing.model_input import (
    MODEL_INPUT_BUILDER,
    MODEL_INPUT_HASH_POLICY,
    MODEL_INPUT_TEXT_COLUMN,
    MODEL_INPUT_VERSION,
)
from ml_model.retraining.dashboard_contracts import (
    CANONICAL_LABELS,
    DATASET_MANIFEST_VERSION,
    ExportedSample,
    canonical_json,
    get_run_artifact_directory,
)
from ml_model.retraining.snapshots import (
    ContaminationIndex,
    SnapshotContaminationError,
    capture_historical_file_hashes,
    load_historical_frames,
)

DATASET_VERSION_PREFIX = "dashboard"
DEFAULT_GOLDEN_MANIFEST = (
    Path(__file__).resolve().parents[2]
    / "data"
    / "experiments"
    / "retraining_20_day_v1"
    / "golden"
    / "golden-v2"
    / "golden_manifest.json"
)


class DashboardDatasetError(ValueError):
    """Raised when a run-local dataset cannot satisfy the serving contract."""


class DashboardDatasetContaminationError(DashboardDatasetError):
    """Raised when an approved row overlaps frozen or newly appended data."""


class DashboardDatasetResult:
    def __init__(
        self, *, dataset_dir: Path, dataset_version: str, manifest: dict[str, Any]
    ):
        self.dataset_dir = dataset_dir
        self.dataset_version = dataset_version
        self.manifest = manifest

    @property
    def train_rows(self) -> int:
        return int(self.manifest["row_counts"]["train"])

    @property
    def validation_rows(self) -> int:
        return int(self.manifest["row_counts"]["validation"])

    @property
    def test_rows(self) -> int:
        return int(self.manifest["row_counts"]["test"])


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_output_root(output_root: Path, historical_root: Path) -> None:
    output_root = output_root.resolve()
    historical_root = historical_root.resolve()
    if output_root == historical_root or historical_root in output_root.parents:
        raise DashboardDatasetError("dataset output must not be inside historical data")


def _validate_historical_labels(frames: Sequence[tuple[str, pd.DataFrame]]) -> None:
    for split, frame in frames:
        unknown = sorted(set(frame["final_label"].dropna()) - set(CANONICAL_LABELS))
        if unknown:
            raise DashboardDatasetError(
                f"historical {split} split contains unsupported labels: {unknown}"
            )


def _validate_exported_sample(
    sample: ExportedSample, expected_preprocessing_version: str
) -> None:
    if sample.preprocessing_version != expected_preprocessing_version:
        raise DashboardDatasetError(
            f"sample {sample.sample_id} has unsupported preprocessing metadata"
        )
    if sample.verified_label not in CANONICAL_LABELS:
        raise DashboardDatasetError(
            f"sample {sample.sample_id} has an unsupported verified label"
        )
    actual_hash = hashlib.sha256(sample.model_input_text.encode("utf-8")).hexdigest()
    if actual_hash != sample.model_input_hash:
        raise DashboardDatasetError(
            f"sample {sample.sample_id} model-input hash does not match text"
        )
    if not sample.source_provenance or not sample.source_verification_status:
        raise DashboardDatasetError(
            f"sample {sample.sample_id} is missing source lineage metadata"
        )
    if sample.ingest_event_hash is None:
        raise DashboardDatasetError(
            f"sample {sample.sample_id} is missing source event hash"
        )


def _new_sample_mapping(sample: ExportedSample) -> dict[str, Any]:
    reviewed_at = sample.reviewed_at or ""
    try:
        reviewed_day = datetime.fromisoformat(reviewed_at.replace("Z", "+00:00")).date()
    except ValueError as exc:
        raise DashboardDatasetError(
            f"sample {sample.sample_id} has invalid review timestamp"
        ) from exc
    # The controlled 20-day adapter consumes these fields; dashboard snapshots
    # retain the same meaning without exposing a dashboard day to the API.
    return {
        "sample_id": sample.sample_id,
        "model_input_text": sample.model_input_text,
        "model_input_hash": sample.model_input_hash,
        "ground_truth_label": sample.verified_label,
        "source_type": sample.source_provenance,
        "source_family": sample.source_provenance,
        "is_synthetic": False,
        "provenance_id": sample.ingest_event_hash,
        "preprocessing_version": sample.preprocessing_version,
        "reviewed_at": reviewed_at,
        "reviewed_date": reviewed_day.isoformat(),
    }


def _source_coverage(
    frames: Sequence[tuple[str, pd.DataFrame]], samples: Sequence[ExportedSample]
) -> dict[str, dict[str, int]]:
    historical = Counter()
    for _split, frame in frames:
        column = (
            "source_provenance"
            if "source_provenance" in frame.columns
            else "source_type"
        )
        if column in frame.columns:
            historical.update(str(value) for value in frame[column].fillna("UNKNOWN"))
        else:
            historical.update({"HISTORICAL_UNKNOWN": len(frame)})
    additions = Counter(str(sample.source_provenance) for sample in samples)
    return {
        "historical": dict(sorted(historical.items())),
        "approved_additions": dict(sorted(additions.items())),
    }


def _temporal_coverage(samples: Sequence[ExportedSample]) -> dict[str, Any]:
    timestamps = sorted(sample.reviewed_at for sample in samples if sample.reviewed_at)
    return {
        "count": len(timestamps),
        "earliest_reviewed_at": timestamps[0] if timestamps else None,
        "latest_reviewed_at": timestamps[-1] if timestamps else None,
        "distinct_review_dates": sorted(
            {timestamp[:10] for timestamp in timestamps if len(timestamp) >= 10}
        ),
    }


def build_dashboard_dataset_snapshot(
    *,
    run_id: str,
    exported_samples: Sequence[ExportedSample],
    historical_data_dir: Path | str,
    output_root: Path | str,
    source_dataset_version: str,
    expected_preprocessing_version: str = MODEL_INPUT_VERSION,
    near_duplicate_threshold: float = 0.90,
    golden_manifest_path: Path | str | None = None,
) -> DashboardDatasetResult:
    """Copy frozen splits and append approved rows to a run-local train split."""

    historical_root = Path(historical_data_dir).expanduser().resolve()
    output_root_path = Path(output_root).expanduser().resolve()
    _safe_output_root(output_root_path, historical_root)
    validate_dataset_preprocessing(
        historical_root,
        expected_dataset_version=source_dataset_version,
        expected_preprocessing_version=expected_preprocessing_version,
        expected_text_column=MODEL_INPUT_TEXT_COLUMN,
    )
    load_dataset_file_manifest(historical_root)
    historical_frames = load_historical_frames(historical_root)
    _validate_historical_labels(historical_frames)
    captured_hashes = capture_historical_file_hashes(historical_root)

    samples = sorted(exported_samples, key=lambda sample: sample.sample_id)
    seen_ids: set[str] = set()
    for sample in samples:
        if sample.sample_id in seen_ids:
            raise DashboardDatasetError(
                f"duplicate approved sample id: {sample.sample_id}"
            )
        seen_ids.add(sample.sample_id)
        _validate_exported_sample(sample, expected_preprocessing_version)

    golden_path = (
        DEFAULT_GOLDEN_MANIFEST
        if golden_manifest_path is None
        else Path(golden_manifest_path).expanduser().resolve()
    )
    try:
        golden_controls = load_golden_controls(golden_path)
        golden_overlaps = find_golden_overlap(
            golden_controls,
            [_new_sample_mapping(sample) for sample in samples],
            near_duplicate_threshold=near_duplicate_threshold,
        )
    except (GoldenControlError, OSError, ValueError) as exc:
        raise DashboardDatasetError(
            "golden holdout metadata could not be verified"
        ) from exc
    if golden_overlaps:
        raise DashboardDatasetContaminationError(
            f"dashboard dataset overlaps locked golden controls: {golden_overlaps}"
        )

    contamination_index = ContaminationIndex.from_historical_frames(historical_frames)
    try:
        contamination_report = contamination_index.validate_new_samples(
            [_new_sample_mapping(sample) for sample in samples],
            threshold=near_duplicate_threshold,
        )
    except (SnapshotContaminationError, ValueError) as exc:
        if isinstance(exc, SnapshotContaminationError):
            report = exc.report
        else:
            report = {"error": str(exc)}
        raise DashboardDatasetContaminationError(
            f"dashboard dataset contamination detected: {report}"
        ) from exc

    dataset_identity = {
        "run_id": run_id,
        "source_dataset_version": source_dataset_version,
        "preprocessing_version": expected_preprocessing_version,
        "historical_file_hashes": captured_hashes,
        "samples": [sample.to_dict() for sample in samples],
    }
    content_hash = hashlib.sha256(
        canonical_json(dataset_identity).encode("utf-8")
    ).hexdigest()
    dataset_version = f"{DATASET_VERSION_PREFIX}-{run_id}-{content_hash[:12]}"
    run_dir = get_run_artifact_directory(output_root_path, run_id)
    dataset_dir = run_dir / "dataset"
    if dataset_dir.exists():
        raise DashboardDatasetError("dataset artifact directory already exists")
    dataset_dir.mkdir(parents=True, exist_ok=False)

    historical_by_split = {split: frame for split, frame in historical_frames}
    train = historical_by_split["train"].copy()
    if samples:
        rows: list[dict[str, Any]] = []
        for sample in samples:
            row = {column: None for column in train.columns}
            row[MODEL_INPUT_TEXT_COLUMN] = sample.model_input_text
            row["final_label"] = sample.verified_label
            metadata_values = {
                "sample_id": sample.sample_id,
                "model_input_hash": sample.model_input_hash,
                "source_type": sample.source_provenance,
                "source_provenance": sample.source_provenance,
                "source_verification_status": sample.source_verification_status,
                "reviewer_id": sample.reviewer_id,
                "reviewed_at": sample.reviewed_at,
                "preprocessing_version": sample.preprocessing_version,
                "provenance_id": sample.ingest_event_hash,
            }
            for column, value in metadata_values.items():
                if column in row:
                    row[column] = value
            rows.append(row)
        train = pd.concat(
            [train, pd.DataFrame(rows, columns=train.columns)], ignore_index=True
        )

    train.to_parquet(dataset_dir / "train.parquet", index=False)
    for split in ("validation", "test"):
        shutil.copyfile(
            historical_root / f"{split}.parquet", dataset_dir / f"{split}.parquet"
        )

    output_hashes = {
        split: _sha256_file(dataset_dir / f"{split}.parquet")
        for split in ("train", "validation", "test")
    }
    (dataset_dir / "checksums.txt").write_text(
        "".join(
            f"{output_hashes[split]}  {split}.parquet\n"
            for split in ("train", "validation", "test")
        ),
        encoding="utf-8",
    )
    metadata = {
        "dataset_version": dataset_version,
        "source_dataset_version": source_dataset_version,
        "preprocessing_version": expected_preprocessing_version,
        "text_column": MODEL_INPUT_TEXT_COLUMN,
        "model_input_hash_policy": MODEL_INPUT_HASH_POLICY,
        "shared_builder_name": MODEL_INPUT_BUILDER,
        "preprocessing_implementation_version": expected_preprocessing_version,
        "source_type": "dashboard_retraining_snapshot",
    }
    (dataset_dir / "metadata_preprocessing.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )

    # Validate the emitted artifact with the same loader and metadata checks
    # used by training before recording its manifest.
    validate_dataset_preprocessing(
        dataset_dir,
        expected_dataset_version=dataset_version,
        expected_preprocessing_version=expected_preprocessing_version,
        expected_text_column=MODEL_INPUT_TEXT_COLUMN,
    )
    load_dataset_file_manifest(dataset_dir)
    load_data_splits(dataset_dir, MODEL_INPUT_TEXT_COLUMN, "final_label")
    if capture_historical_file_hashes(historical_root) != captured_hashes:
        raise DashboardDatasetError(
            "historical dataset changed during snapshot creation"
        )

    manifest: dict[str, Any] = {
        "manifest_version": DATASET_MANIFEST_VERSION,
        "run_id": run_id,
        "dataset_version": dataset_version,
        "source_dataset_version": source_dataset_version,
        "preprocessing_version": expected_preprocessing_version,
        "input_historical_file_hashes": captured_hashes,
        "output_file_hashes": output_hashes,
        "holdout_file_hashes": {
            "validation.parquet": output_hashes["validation"],
            "test.parquet": output_hashes["test"],
        },
        "row_counts": {
            "train": int(len(train)),
            "validation": int(len(historical_by_split["validation"])),
            "test": int(len(historical_by_split["test"])),
            "approved_additions": len(samples),
        },
        "class_counts": {
            label: int(count)
            for label, count in train["final_label"].value_counts().sort_index().items()
        },
        "approved_additions_class_counts": dict(
            sorted(Counter(sample.verified_label for sample in samples).items())
        ),
        "source_review_lineage": [
            {
                "sample_id": sample.sample_id,
                "traffic_log_id": sample.traffic_log_id,
                "review_revision": sample.review_revision,
                "reviewed_at": sample.reviewed_at,
                "reviewer_id": sample.reviewer_id,
                "source_provenance": sample.source_provenance,
                "source_verification_status": sample.source_verification_status,
                "model_input_hash": sample.model_input_hash,
                "verified_label": sample.verified_label,
            }
            for sample in samples
        ],
        "duplicate_decisions": contamination_report,
        "golden_holdout": {
            "manifest_path": golden_path.name,
            "golden_version": golden_controls.golden_version,
            "manifest_sha256": _sha256_file(golden_path),
            "cases_sha256": _sha256_file(golden_controls.cases_path),
            "overlap_count": len(golden_overlaps),
        },
        "temporal_coverage": _temporal_coverage(samples),
        "source_family_coverage": _source_coverage(historical_frames, samples),
        "schema": {
            "text_column": MODEL_INPUT_TEXT_COLUMN,
            "label_column": "final_label",
            "train_columns": list(train.columns),
            "validation_columns": list(historical_by_split["validation"].columns),
            "test_columns": list(historical_by_split["test"].columns),
        },
        "historical_data_unchanged": True,
        "holdout_policy": "frozen_historical_validation_test",
    }
    manifest["manifest_sha256"] = hashlib.sha256(
        canonical_json(manifest).encode("utf-8")
    ).hexdigest()
    (dataset_dir / "dataset_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return DashboardDatasetResult(
        dataset_dir=dataset_dir,
        dataset_version=dataset_version,
        manifest=manifest,
    )


__all__ = [
    "DashboardDatasetContaminationError",
    "DashboardDatasetError",
    "DashboardDatasetResult",
    "build_dashboard_dataset_snapshot",
]
