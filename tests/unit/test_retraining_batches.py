from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest

from ml_model.evaluation.golden_controls import load_golden_controls
from ml_model.preprocessing.dataset_io import (
    load_dataset_file_manifest,
    validate_dataset_preprocessing,
)
from ml_model.retraining.snapshots import build_cumulative_snapshot
from ml_model.retraining.validate_batch import validate_batch_file

REQUIRED = {
    "sample_id": "day-01-001",
    "model_input_text": "GET /api/users?page=2&limit=25",
    "model_input_hash": hashlib.sha256(
        b"GET /api/users?page=2&limit=25"
    ).hexdigest(),
    "ground_truth_label": "Normal",
    "batch_day": 1,
    "source_type": "curated_fixture",
    "is_synthetic": True,
    "review_status": "approved_for_training",
    "provenance_id": "fixture:day-01-001",
    "preprocessing_version": "http-preprocessor-v1",
}


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("ground_truth_label", "Unknown", "unknown label"),
        ("ground_truth_label", None, "missing ground truth"),
        ("predicted_label", "Normal", "predicted label"),
        ("review_status", "pending", "not approved"),
        ("provenance_id", "", "provenance"),
        ("preprocessing_version", "model-input-v2-redacted", "preprocessing"),
    ],
)
def test_batch_validator_rejects_untrusted_sample_fields(
    tmp_path: Path, field: str, value: object, message: str
):
    row = dict(REQUIRED)
    row[field] = value
    batch_path = tmp_path / "day_01.jsonl"
    _write_jsonl(batch_path, [row])

    report = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_texts=set(),
        quarantine_dir=tmp_path / "quarantine",
    )

    assert report.accepted_samples == []
    assert any(message in rejection["reason"] for rejection in report.rejected_samples)
    assert (tmp_path / "quarantine" / "day_01.quarantine.jsonl").is_file()


def test_batch_validator_rejects_unknown_labels_duplicates_conflicts_and_golden_overlap(
    tmp_path: Path,
):
    duplicate = dict(REQUIRED)
    conflict = dict(
        REQUIRED,
        sample_id="day-01-002",
        ground_truth_label="SQL Injection",
    )
    overlap = dict(REQUIRED, sample_id="day-01-003")
    batch_path = tmp_path / "day_01.jsonl"
    _write_jsonl(batch_path, [REQUIRED, duplicate, conflict, overlap])

    report = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_texts={REQUIRED["model_input_text"]},
        quarantine_dir=tmp_path / "quarantine",
    )

    assert report.accepted_samples == []
    reasons = " ".join(row["reason"] for row in report.rejected_samples)
    assert "golden overlap" in reasons
    assert "duplicate" in reasons
    assert "conflicting label" in reasons


def test_batch_validator_rejects_near_duplicate_locked_golden_control(tmp_path: Path):
    controls = load_golden_controls(
        "data/experiments/retraining_20_day_v1/golden/golden_manifest.json"
    )
    near_duplicate = dict(
        REQUIRED,
        sample_id="near-golden",
        model_input_text="GET /api/users?page=1&limit=11",
        model_input_hash=hashlib.sha256(
            b"GET /api/users?page=1&limit=11"
        ).hexdigest(),
    )
    batch_path = tmp_path / "day_01.jsonl"
    _write_jsonl(batch_path, [near_duplicate])

    report = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_controls=controls,
        quarantine_dir=tmp_path / "quarantine",
    )

    assert report.accepted_samples == []
    assert "golden overlap" in report.rejected_samples[0]["reason"]


def test_quarantine_does_not_store_raw_request_text(tmp_path: Path):
    row = dict(
        REQUIRED,
        model_input_text="Authorization=SECRET-TOKEN",
        model_input_hash=hashlib.sha256(
            b"Authorization=SECRET-TOKEN"
        ).hexdigest(),
        review_status="pending",
    )
    batch_path = tmp_path / "day_01.jsonl"
    _write_jsonl(batch_path, [row])

    validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_texts=set(),
        quarantine_dir=tmp_path / "quarantine",
    )

    content = (
        tmp_path / "quarantine" / "day_01.quarantine.jsonl"
    ).read_text(encoding="utf-8")
    assert "SECRET-TOKEN" not in content
    assert "Authorization=SECRET-TOKEN" not in content
    assert "model_input_sha256" in content


def test_batch_validator_rejects_missing_or_invalid_model_input_hash(
    tmp_path: Path,
):
    missing = dict(REQUIRED)
    missing.pop("model_input_hash")
    invalid = dict(REQUIRED, model_input_hash="0" * 64)
    batch_path = tmp_path / "day_01.jsonl"
    _write_jsonl(batch_path, [missing, invalid])

    report = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        expected_batch_day=1,
        golden_texts=set(),
        quarantine_dir=tmp_path / "quarantine",
    )

    assert report.accepted_samples == []
    reasons = " ".join(row["reason"] for row in report.rejected_samples)
    assert "missing model_input_hash" in reasons
    assert "model_input_hash does not match" in reasons


def test_batch_validator_rejects_wrong_batch_day(tmp_path: Path):
    batch_path = tmp_path / "day_01.jsonl"
    _write_jsonl(batch_path, [dict(REQUIRED, batch_day=2)])

    report = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        expected_batch_day=1,
        golden_texts=set(),
        quarantine_dir=tmp_path / "quarantine",
    )

    assert report.accepted_samples == []
    assert "does not match expected day 1" in report.rejected_samples[0]["reason"]


def test_batch_report_is_deterministic_and_snapshot_is_cumulative(tmp_path: Path):
    batch_path = tmp_path / "day_01.jsonl"
    _write_jsonl(batch_path, [REQUIRED])
    first = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_texts=set(),
        quarantine_dir=tmp_path / "q1",
    )
    second = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_texts=set(),
        quarantine_dir=tmp_path / "q2",
    )
    assert first.to_dict() == second.to_dict()

    historical = tmp_path / "historical"
    historical.mkdir()
    base = pd.DataFrame([{"combined_payload": "GET /health", "final_label": "Normal"}])
    for split in ("train", "validation", "test"):
        base.to_parquet(historical / f"{split}.parquet", index=False)

    day_one = build_cumulative_snapshot(
        historical_data_dir=historical,
        cumulative_samples=first.accepted_samples,
        output_root=tmp_path / "outputs",
        day=1,
        dataset_version="v3_907k_cleaned",
        preprocessing_version="http-preprocessor-v1",
    )
    day_two_sample = dict(
        REQUIRED,
        sample_id="day-02-001",
        batch_day=2,
        model_input_text="GET /api/users?page=3&limit=25",
        model_input_hash=hashlib.sha256(
            b"GET /api/users?page=3&limit=25"
        ).hexdigest(),
    )
    day_two = build_cumulative_snapshot(
        historical_data_dir=historical,
        cumulative_samples=[*first.accepted_samples, day_two_sample],
        output_root=tmp_path / "outputs",
        day=2,
        dataset_version="v3_907k_cleaned",
        preprocessing_version="http-preprocessor-v1",
    )

    assert day_one.train_rows == 2
    assert day_two.train_rows == 3
    assert day_one.output_hash != day_two.output_hash
    assert day_one.snapshot_dir != day_two.snapshot_dir
    assert day_one.manifest["validation_rows"] == 1
    assert (day_two.snapshot_dir / "train.parquet").is_file()


def test_snapshot_is_accepted_by_training_dataset_preflight(tmp_path: Path):
    historical = tmp_path / "historical"
    historical.mkdir()
    base = pd.DataFrame(
        [{"combined_payload": "GET /health", "final_label": "Normal"}]
    )
    for split in ("train", "validation", "test"):
        base.to_parquet(historical / f"{split}.parquet", index=False)

    result = build_cumulative_snapshot(
        historical_data_dir=historical,
        cumulative_samples=[REQUIRED],
        output_root=tmp_path / "outputs",
        day=1,
        dataset_version="v3_907k_cleaned",
        preprocessing_version="http-preprocessor-v1",
    )

    metadata = validate_dataset_preprocessing(
        result.snapshot_dir,
        expected_dataset_version="v3_907k_cleaned",
        expected_preprocessing_version="http-preprocessor-v1",
    )
    manifest = load_dataset_file_manifest(result.snapshot_dir)

    assert metadata["text_column"] == "combined_payload"
    assert manifest["files"]["train.parquet"]
    assert (result.snapshot_dir / "metadata_preprocessing.json").is_file()
    assert (result.snapshot_dir / "checksums.txt").is_file()
