"""Deterministic cumulative training snapshots for the offline experiment."""

from __future__ import annotations

import json
from dataclasses import dataclass
from difflib import SequenceMatcher
from math import ceil, floor
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

import pandas as pd

from ml_model.preprocessing.dataset_io import load_dataset_file_manifest
from ml_model.preprocessing.model_input import (
    MODEL_INPUT_BUILDER,
    MODEL_INPUT_HASH_POLICY,
    MODEL_INPUT_TEXT_COLUMN,
    canonicalize_text,
)
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


class SnapshotContaminationError(ValueError):
    """Raised when a cumulative batch overlaps historical data."""

    def __init__(self, report: dict[str, Any]) -> None:
        self.report = report
        super().__init__(
            "snapshot contamination detected: "
            f"{report['exact_overlap_count']} exact and "
            f"{report['near_duplicate_count']} near-duplicate matches"
        )


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
                "model_input_hash": str(sample["model_input_hash"]),
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


def _similarity_text(value: str) -> str:
    """Normalize request text and make query-parameter ordering deterministic."""

    normalized = canonicalize_text(value)
    parts = normalized.split(maxsplit=1)
    if len(parts) != 2:
        return normalized
    method, target = parts
    parsed = urlsplit(target)
    if not parsed.query:
        return normalized
    query = urlencode(sorted(parse_qsl(parsed.query, keep_blank_values=True)))
    normalized_target = urlunsplit(
        (parsed.scheme, parsed.netloc, parsed.path, query, parsed.fragment)
    )
    return f"{method} {normalized_target}"


LENGTH_BUCKET_WIDTH = 32


@dataclass(frozen=True)
class ContaminationRecord:
    """Normalized, non-sensitive index entry for one historical or daily row."""

    record_key: str
    sample_id: str
    source: str
    text: str
    normalized_text: str
    normalized_hash: str
    label: str | None


class ContaminationIndex:
    """Reusable exact and length-bucketed near-duplicate contamination index.

    The length-range candidate filter is the same safe precondition used by the
    previous implementation: a SequenceMatcher ratio cannot reach the configured
    threshold when the normalized lengths fall outside this range. It therefore
    reduces comparisons without filtering on method/path, which could miss a
    high-ratio near duplicate whose request dimensions changed.
    """

    def __init__(
        self,
        historical_records: Sequence[ContaminationRecord],
    ) -> None:
        self.exact_hashes: dict[str, list[ContaminationRecord]] = {}
        self.buckets: dict[int, list[ContaminationRecord]] = {}
        self._records: dict[str, ContaminationRecord] = {}
        self._daily_record_keys: set[str] = set()
        self._historical_row_count = len(historical_records)
        self._candidate_comparisons_checked = 0
        self._add_records(historical_records)

    @classmethod
    def from_historical_frames(
        cls,
        historical_frames: Sequence[tuple[str, pd.DataFrame]],
    ) -> "ContaminationIndex":
        records: list[ContaminationRecord] = []
        for split, frame in historical_frames:
            for row_number, row in frame.reset_index(drop=True).iterrows():
                text = str(row["combined_payload"])
                records.append(
                    cls._record(
                        record_key=f"historical:{split}:{row_number}",
                        sample_id=str(row.get("sample_id", f"{split}:{row_number}")),
                        source=str(split),
                        text=text,
                        label=(
                            None
                            if row.get("final_label") is None
                            else str(row["final_label"])
                        ),
                    )
                )
        return cls(records)

    @classmethod
    def from_historical_dir(
        cls, historical_data_dir: Path | str
    ) -> "ContaminationIndex":
        root = Path(historical_data_dir).expanduser().resolve()
        historical = [
            (split, _load_split(root, split))
            for split in ("train", "validation", "test")
        ]
        return cls.from_historical_frames(historical)

    @staticmethod
    def _record(
        *,
        record_key: str,
        sample_id: str,
        source: str,
        text: str,
        label: str | None,
    ) -> ContaminationRecord:
        normalized_text = _similarity_text(text)
        return ContaminationRecord(
            record_key=record_key,
            sample_id=sample_id,
            source=source,
            text=text,
            normalized_text=normalized_text,
            normalized_hash=sha256_text(normalized_text),
            label=label,
        )

    @staticmethod
    def _bucket_for(text: str) -> int:
        return len(text) // LENGTH_BUCKET_WIDTH

    def _add_records(self, records: Sequence[ContaminationRecord]) -> None:
        for record in records:
            self._records[record.record_key] = record
            self.exact_hashes.setdefault(record.normalized_hash, []).append(record)
            self.buckets.setdefault(
                self._bucket_for(record.normalized_text), []
            ).append(record)
            if record.source == "cumulative_daily":
                self._daily_record_keys.add(record.record_key)

    @property
    def historical_row_count(self) -> int:
        return self._historical_row_count

    @property
    def daily_row_count(self) -> int:
        return len(self._daily_record_keys)

    @property
    def sample_ids(self) -> frozenset[str]:
        return frozenset(record.sample_id for record in self._records.values())

    def diagnostics(self) -> dict[str, int]:
        return {
            "historical_row_count": self.historical_row_count,
            "daily_row_count": self.daily_row_count,
            "candidate_comparisons_checked": self._candidate_comparisons_checked,
        }

    def _candidate_records(
        self, normalized_text: str, *, threshold: float
    ) -> list[ContaminationRecord]:
        minimum_length = ceil(len(normalized_text) * threshold)
        maximum_length = floor(len(normalized_text) / threshold)
        minimum_bucket = self._bucket_for("x" * minimum_length)
        maximum_bucket = self._bucket_for("x" * maximum_length)
        candidates: list[ContaminationRecord] = []
        for bucket in range(minimum_bucket, maximum_bucket + 1):
            candidates.extend(self.buckets.get(bucket, ()))
        return [
            record
            for record in candidates
            if minimum_length <= len(record.normalized_text) <= maximum_length
        ]

    def _find_record_matches(
        self,
        record: ContaminationRecord,
        *,
        threshold: float,
    ) -> tuple[list[dict[str, Any]], int]:
        exact_matches = self.exact_hashes.get(record.normalized_hash, [])
        if exact_matches:
            return [
                self._match(record, match, similarity=1.0) for match in exact_matches
            ], 0
        candidates = self._candidate_records(
            record.normalized_text, threshold=threshold
        )
        matches: list[dict[str, Any]] = []
        comparisons = 0
        for candidate in candidates:
            comparisons += 1
            matcher = SequenceMatcher(
                None, record.normalized_text, candidate.normalized_text
            )
            if matcher.quick_ratio() < threshold:
                continue
            similarity = matcher.ratio()
            if similarity >= threshold:
                matches.append(self._match(record, candidate, similarity=similarity))
        return matches, comparisons

    @staticmethod
    def _match(
        candidate: ContaminationRecord,
        matched: ContaminationRecord,
        *,
        similarity: float,
    ) -> dict[str, Any]:
        return {
            "sample_id": candidate.sample_id,
            "matched_sample_id": matched.sample_id,
            "affected_split": matched.source,
            "match_type": (
                "exact"
                if candidate.normalized_hash == matched.normalized_hash
                else "near_duplicate"
            ),
            "similarity": round(similarity, 6),
            "candidate_model_input_sha256": sha256_text(candidate.text),
            "matched_model_input_sha256": sha256_text(matched.text),
        }

    def _report(
        self,
        *,
        threshold: float,
        matches: Sequence[dict[str, Any]],
        candidate_comparisons_checked: int,
    ) -> dict[str, Any]:
        exact_count = sum(match["match_type"] == "exact" for match in matches)
        near_count = sum(match["match_type"] == "near_duplicate" for match in matches)
        return {
            "near_duplicate_threshold": threshold,
            "historical_row_count": self.historical_row_count,
            "daily_row_count": self.daily_row_count,
            "candidate_comparisons_checked": candidate_comparisons_checked,
            "exact_overlap_count": exact_count,
            "near_duplicate_count": near_count,
            "rejected_sample_ids": sorted(
                {str(match["sample_id"]) for match in matches}
            ),
            "matches": sorted(
                (dict(match) for match in matches),
                key=lambda match: (
                    str(match.get("sample_id", "")),
                    str(match.get("affected_split", "")),
                    str(match.get("matched_sample_id", "")),
                ),
            ),
        }

    def check_new_samples(
        self,
        samples: Sequence[Mapping[str, Any]],
        *,
        threshold: float = 0.90,
    ) -> dict[str, Any]:
        if not 0.0 < threshold <= 1.0:
            raise ValueError("near_duplicate_threshold must be within (0, 1]")
        sample_list = list(samples)
        seen_ids: set[str] = set()
        seen_hashes: dict[str, str] = {}
        records: list[ContaminationRecord] = []
        for sample in sample_list:
            sample_id = str(sample["sample_id"])
            text = str(sample["model_input_text"])
            label = str(sample["ground_truth_label"])
            if sample_id in seen_ids:
                raise ValueError(f"duplicate daily sample_id: {sample_id}")
            if sample_id in self.sample_ids:
                raise ValueError(f"duplicate daily sample_id: {sample_id}")
            seen_ids.add(sample_id)
            record = self._record(
                record_key=f"daily:{sample_id}",
                sample_id=sample_id,
                source="cumulative_daily",
                text=text,
                label=label,
            )
            if record.normalized_hash in seen_hashes:
                if seen_hashes[record.normalized_hash] != label:
                    raise ValueError(f"conflicting daily label for: {sample_id}")
                raise ValueError(f"duplicate daily text for: {sample_id}")
            seen_hashes[record.normalized_hash] = label
            records.append(record)

        matches: list[dict[str, Any]] = []
        candidate_comparisons = 0
        pending = ContaminationIndex(())
        for record in records:
            existing_matches, comparisons = self._find_record_matches(
                record, threshold=threshold
            )
            candidate_comparisons += comparisons
            pending_matches, comparisons = pending._find_record_matches(
                record, threshold=threshold
            )
            candidate_comparisons += comparisons
            matches.extend(existing_matches)
            for match in pending_matches:
                matches.append(match)
            pending._add_records((record,))
        self._candidate_comparisons_checked += candidate_comparisons
        return self._report(
            threshold=threshold,
            matches=matches,
            candidate_comparisons_checked=candidate_comparisons,
        )

    def validate_new_samples(
        self,
        samples: Sequence[Mapping[str, Any]],
        *,
        threshold: float = 0.90,
    ) -> dict[str, Any]:
        report = self.check_new_samples(samples, threshold=threshold)
        if report["matches"]:
            raise SnapshotContaminationError(report)
        return report

    def add_daily_samples(self, samples: Sequence[Mapping[str, Any]]) -> None:
        records = [
            self._record(
                record_key=f"daily:{sample['sample_id']}",
                sample_id=str(sample["sample_id"]),
                source="cumulative_daily",
                text=str(sample["model_input_text"]),
                label=str(sample["ground_truth_label"]),
            )
            for sample in samples
        ]
        self._add_records(records)


def _contamination_report(
    samples: Sequence[Mapping[str, Any]],
    historical_frames: Sequence[tuple[str, pd.DataFrame]],
    *,
    threshold: float = 0.90,
) -> dict[str, Any]:
    index = ContaminationIndex.from_historical_frames(historical_frames)
    return index.validate_new_samples(samples, threshold=threshold)


def sha256_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _validate_daily_samples(
    samples: Sequence[Mapping[str, Any]],
    historical_frames: Sequence[tuple[str, pd.DataFrame]],
) -> dict[str, Any]:
    return _contamination_report(samples, historical_frames)


def _write_training_dataset_contract(
    snapshot_dir: Path,
    *,
    dataset_version: str,
    preprocessing_version: str,
    output_files: Mapping[str, str],
) -> None:
    metadata = {
        "dataset_version": dataset_version,
        "preprocessing_version": preprocessing_version,
        "text_column": MODEL_INPUT_TEXT_COLUMN,
        "model_input_hash_policy": MODEL_INPUT_HASH_POLICY,
        "shared_builder_name": MODEL_INPUT_BUILDER,
        "preprocessing_implementation_version": preprocessing_version,
        "source_type": "controlled_retraining_snapshot",
    }
    (snapshot_dir / "metadata_preprocessing.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    split_names = ("train.parquet", "validation.parquet", "test.parquet")
    checksum_lines = [f"{output_files[name]}  {name}" for name in split_names]
    (snapshot_dir / "checksums.txt").write_text(
        "\n".join(checksum_lines) + "\n", encoding="utf-8"
    )


def _portable_path(path: Path, project_root: Path | None) -> str:
    if project_root is not None:
        try:
            return str(path.resolve().relative_to(project_root.resolve()))
        except ValueError:
            pass
    return path.name


def _integrity_hashes(
    snapshot_dir: Path, output_files: Mapping[str, str]
) -> dict[str, str]:
    contract_files = {
        "metadata_preprocessing.json": sha256_file(
            snapshot_dir / "metadata_preprocessing.json"
        ),
        "checksums.txt": sha256_file(snapshot_dir / "checksums.txt"),
    }
    return {
        "data_files_hash": canonical_json_sha256(dict(output_files)),
        "contract_files_hash": canonical_json_sha256(contract_files),
    }


def validate_snapshot_integrity(snapshot_dir: Path | str) -> dict[str, Any]:
    root = Path(snapshot_dir).expanduser().resolve()
    manifest_path = root / "snapshot_manifest.json"
    if not manifest_path.is_file():
        raise ValueError(f"snapshot manifest is missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    stored_manifest_hash = manifest.get("manifest_sha256")
    unsigned_manifest = {
        key: value for key, value in manifest.items() if key != "manifest_sha256"
    }
    if stored_manifest_hash != canonical_json_sha256(unsigned_manifest):
        raise ValueError("snapshot manifest_sha256 mismatch")
    output_files = manifest.get("output_files")
    if not isinstance(output_files, Mapping):
        raise ValueError("snapshot output_files is missing")
    for name, expected_hash in output_files.items():
        path = root / str(name)
        if not path.is_file() or sha256_file(path) != expected_hash:
            raise ValueError(f"snapshot data file hash mismatch: {name}")
    dataset_manifest = load_dataset_file_manifest(root)
    if dataset_manifest["files"] != dict(output_files):
        raise ValueError("snapshot checksums.txt does not match output_files")
    if manifest.get("dataset_file_manifest_sha256") != dataset_manifest["sha256"]:
        raise ValueError("snapshot dataset_file_manifest_sha256 mismatch")
    integrity = _integrity_hashes(root, output_files)
    for name, expected in integrity.items():
        if manifest.get(name) != expected:
            raise ValueError(f"snapshot {name} mismatch")
    return {"passed": True, **integrity, "manifest_sha256": stored_manifest_hash}


def build_cumulative_snapshot(
    *,
    historical_data_dir: Path | str,
    cumulative_samples: Sequence[Mapping[str, Any]],
    output_root: Path | str,
    day: int,
    dataset_version: str,
    preprocessing_version: str,
    project_root: Path | str | None = None,
    contamination_index: ContaminationIndex | None = None,
    new_samples: Sequence[Mapping[str, Any]] | None = None,
) -> SnapshotResult:
    if not 1 <= int(day) <= 20:
        raise ValueError("simulation day must be between 1 and 20")
    historical_root = Path(historical_data_dir).expanduser().resolve()
    output_root = Path(output_root).expanduser().resolve()
    _safe_output_root(output_root, historical_root, dataset_version)
    historical = [
        (split, _load_split(historical_root, split))
        for split in ("train", "validation", "test")
    ]
    if contamination_index is None:
        contamination = _validate_daily_samples(cumulative_samples, historical)
    else:
        samples_to_validate = list(new_samples or ())
        if new_samples is None:
            known_ids = contamination_index.sample_ids
            samples_to_validate = [
                sample
                for sample in cumulative_samples
                if str(sample["sample_id"]) not in known_ids
            ]
        contamination = contamination_index.validate_new_samples(samples_to_validate)
        contamination_index.add_daily_samples(samples_to_validate)
        contamination = {
            **contamination,
            "daily_row_count": contamination_index.daily_row_count,
            "index_diagnostics": contamination_index.diagnostics(),
        }
    daily = _daily_frame(cumulative_samples)
    train = pd.concat([historical[0][1], daily], ignore_index=True, sort=False)
    snapshot_dir = output_root / f"day_{int(day):02d}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    split_frames = {
        "train": train,
        "validation": historical[1][1],
        "test": historical[2][1],
    }
    for split, frame in split_frames.items():
        frame.to_parquet(snapshot_dir / f"{split}.parquet", index=False)
    output_files = {
        f"{split}.parquet": sha256_file(snapshot_dir / f"{split}.parquet")
        for split in ("train", "validation", "test")
    }
    _write_training_dataset_contract(
        snapshot_dir,
        dataset_version=dataset_version,
        preprocessing_version=preprocessing_version,
        output_files=output_files,
    )

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
    historical_data_file_manifest_sha256 = canonical_json_sha256({"files": input_files})
    integrity = _integrity_hashes(snapshot_dir, output_files)
    dataset_file_manifest_sha256 = canonical_json_sha256({"files": output_files})
    manifest: dict[str, Any] = {
        "snapshot_version": "retraining-snapshot.v1",
        "day": int(day),
        "dataset_version": dataset_version,
        "preprocessing_version": preprocessing_version,
        "historical_data_dir": _portable_path(
            historical_root,
            Path(project_root).expanduser().resolve()
            if project_root is not None
            else None,
        ),
        "historical_data_file_hashes": input_files,
        "historical_data_file_manifest_sha256": historical_data_file_manifest_sha256,
        "cumulative_sample_count": len(cumulative_samples),
        "train_rows": int(len(train)),
        "validation_rows": int(len(historical[1][1])),
        "test_rows": int(len(historical[2][1])),
        "input_hash": input_hash,
        "output_files": output_files,
        "dataset_file_manifest_sha256": dataset_file_manifest_sha256,
        **integrity,
        "contamination": contamination,
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
    output_hash = canonical_json_sha256(
        {
            "data_files_hash": integrity["data_files_hash"],
            "contract_files_hash": integrity["contract_files_hash"],
            "manifest_sha256": manifest["manifest_sha256"],
        }
    )
    return SnapshotResult(
        snapshot_dir=snapshot_dir,
        train_rows=int(len(train)),
        validation_rows=int(len(historical[1][1])),
        test_rows=int(len(historical[2][1])),
        input_hash=input_hash,
        output_hash=output_hash,
        manifest=manifest,
    )
