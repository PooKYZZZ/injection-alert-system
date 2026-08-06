from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from ml_model.retraining.snapshots import build_cumulative_snapshot
from ml_model.retraining.validate_batch import validate_batch_file

REQUIRED = {
    "sample_id": "day-01-001",
    "model_input_text": "GET /api/users?page=2&limit=25",
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
