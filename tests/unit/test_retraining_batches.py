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
from ml_model.retraining.benchmark_contamination_index import run_benchmark
from ml_model.retraining.snapshots import (
    ContaminationIndex,
    SnapshotContaminationError,
    build_cumulative_snapshot,
    load_historical_frames,
    validate_snapshot_integrity,
)
from ml_model.retraining.validate_batch import validate_batch_file

REQUIRED = {
    "sample_id": "day-01-001",
    "model_input_text": "GET /api/users?page=2&limit=25",
    "model_input_hash": hashlib.sha256(b"GET /api/users?page=2&limit=25").hexdigest(),
    "ground_truth_label": "Normal",
    "batch_day": 1,
    "source_type": "curated_fixture",
    "is_synthetic": False,
    "review_status": "approved_for_training",
    "reviewer_id": "experiment-author",
    "reviewed_at": "2026-08-06T00:00:00Z",
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
        model_input_hash=hashlib.sha256(b"GET /api/users?page=1&limit=11").hexdigest(),
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
        model_input_hash=hashlib.sha256(b"Authorization=SECRET-TOKEN").hexdigest(),
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

    content = (tmp_path / "quarantine" / "day_01.quarantine.jsonl").read_text(
        encoding="utf-8"
    )
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


def test_synthetic_fixture_requires_explicit_simulation_mode(tmp_path: Path):
    row = dict(
        REQUIRED,
        source_type="curated_simulation_fixture",
        is_synthetic=True,
        review_status="curated_simulation_fixture",
        reviewer_id=None,
        reviewed_at=None,
    )
    batch_path = tmp_path / "day_01.jsonl"
    _write_jsonl(batch_path, [row])

    rejected = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_texts=set(),
        quarantine_dir=tmp_path / "rejected-quarantine",
    )
    accepted = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_texts=set(),
        allow_synthetic_fixtures=True,
        quarantine_dir=tmp_path / "accepted-quarantine",
    )

    assert rejected.accepted_samples == []
    assert "simulation fixture" in rejected.rejected_samples[0]["reason"]
    assert len(accepted.accepted_samples) == 1


def test_checked_in_records_search_simulation_batches_match_target_contract(
    tmp_path: Path,
):
    root = Path(__file__).resolve().parents[2]
    batch_root = (
        root
        / "data/experiments/retraining_20_day_v1/daily_batches/records_search_v1"
    )
    controls = load_golden_controls(
        root
        / "data/experiments/retraining_20_day_v1/golden/golden-v2/golden_manifest.json"
    )
    rows = []
    for day in range(1, 21):
        batch_path = batch_root / f"day_{day:02d}.jsonl"
        payloads = [
            json.loads(line)
            for line in batch_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        report = validate_batch_file(
            batch_path,
            expected_preprocessing_version="http-preprocessor-v1",
            expected_batch_day=day,
            golden_controls=controls,
            allow_synthetic_fixtures=True,
            quarantine_dir=tmp_path / "quarantine" / f"day_{day:02d}",
        )
        assert report.passed is True
        assert len(payloads) == 2
        assert all(
            row["model_input_text"].startswith("GET /records/search?")
            for row in payloads
        )
        assert all(row["request_method"] == "GET" for row in payloads)
        assert all(row["request_path"] == "/records/search" for row in payloads)
        assert all(row["route_scope"] == "target_route" for row in payloads)
        assert all(
            row["source_type"] == "curated_simulation_fixture" for row in payloads
        )
        assert all(row["is_synthetic"] is True for row in payloads)
        rows.extend(payloads)

    assert len(rows) == 40
    assert {row["ground_truth_label"] for row in rows} == {
        "Code Injection",
        "Normal",
        "Other Attacks",
        "SQL Injection",
    }
    assert sum(row["ground_truth_label"] == "Normal" for row in rows) == 20


def test_approved_synthetic_sample_is_rejected_even_with_fixture_override(
    tmp_path: Path,
):
    row = dict(REQUIRED, is_synthetic=True)
    batch_path = tmp_path / "day_01.jsonl"
    _write_jsonl(batch_path, [row])

    report = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_texts=set(),
        allow_synthetic_fixtures=True,
        quarantine_dir=tmp_path / "quarantine",
    )

    assert report.accepted_samples == []
    assert "synthetic samples are allowed only" in report.rejected_samples[0]["reason"]


def test_empty_batch_is_rejected(tmp_path: Path):
    batch_path = tmp_path / "day_01.jsonl"
    batch_path.write_text("", encoding="utf-8")

    report = validate_batch_file(
        batch_path,
        expected_preprocessing_version="http-preprocessor-v1",
        golden_texts=set(),
        quarantine_dir=tmp_path / "quarantine",
    )

    assert report.passed is False
    assert report.accepted_samples == []
    assert report.rejected_samples[0]["sample_id"] == "empty-batch"
    assert "no samples" in report.rejected_samples[0]["reason"]


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
        model_input_text="GET /api/teams?offset=0&count=25",
        model_input_hash=hashlib.sha256(
            b"GET /api/teams?offset=0&count=25"
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
    base = pd.DataFrame([{"combined_payload": "GET /health", "final_label": "Normal"}])
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


def test_snapshot_reuses_preloaded_historical_frames(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    historical = tmp_path / "historical"
    historical.mkdir()
    base = pd.DataFrame([{"combined_payload": "GET /health", "final_label": "Normal"}])
    for split in ("train", "validation", "test"):
        base.to_parquet(historical / f"{split}.parquet", index=False)

    historical_frames = load_historical_frames(historical)

    def fail_if_reloaded(*args, **kwargs):
        raise AssertionError("preloaded frames should avoid parquet reloads")

    monkeypatch.setattr(pd, "read_parquet", fail_if_reloaded)
    result = build_cumulative_snapshot(
        historical_data_dir=historical,
        historical_frames=historical_frames,
        cumulative_samples=[REQUIRED],
        output_root=tmp_path / "outputs",
        day=1,
        dataset_version="v3_907k_cleaned",
        preprocessing_version="http-preprocessor-v1",
    )

    assert result.train_rows == 2


def test_snapshot_rejects_near_duplicate_historical_sample_with_split_report(
    tmp_path: Path,
):
    historical = tmp_path / "historical"
    historical.mkdir()
    splits = {
        "train": "GET /api/users?page=1&limit=10",
        "validation": "POST /api/login",
        "test": "GET /api/search?q=books",
    }
    for split, text in splits.items():
        pd.DataFrame([{"combined_payload": text, "final_label": "Normal"}]).to_parquet(
            historical / f"{split}.parquet", index=False
        )

    near_duplicate = dict(
        REQUIRED,
        sample_id="near-historical",
        model_input_text="GET /api/users?page=1&limit=11",
        model_input_hash=hashlib.sha256(b"GET /api/users?page=1&limit=11").hexdigest(),
    )

    with pytest.raises(SnapshotContaminationError) as exc_info:
        build_cumulative_snapshot(
            historical_data_dir=historical,
            cumulative_samples=[near_duplicate],
            output_root=tmp_path / "outputs",
            day=1,
            dataset_version="v3_907k_cleaned",
            preprocessing_version="http-preprocessor-v1",
        )

    report = exc_info.value.report
    assert report["near_duplicate_count"] == 1
    assert report["exact_overlap_count"] == 0
    assert report["matches"][0]["affected_split"] == "train"
    assert report["rejected_sample_ids"] == ["near-historical"]


def test_contamination_index_checks_all_historical_splits_and_query_order(
    tmp_path: Path,
):
    historical = tmp_path / "historical"
    historical.mkdir()
    split_texts = {
        "train": "GET /api/train?id=1&limit=10",
        "validation": "GET /api/validation?id=2&limit=10",
        "test": "GET /api/test?id=3&limit=10",
    }
    for split, text in split_texts.items():
        pd.DataFrame([{"combined_payload": text, "final_label": "Normal"}]).to_parquet(
            historical / f"{split}.parquet", index=False
        )

    index = ContaminationIndex.from_historical_dir(historical)
    for split, text in split_texts.items():
        sample = dict(
            REQUIRED,
            sample_id=f"duplicate-{split}",
            model_input_text=text.replace("?id=", "?limit=10&id=").replace(
                "&limit=10", ""
            ),
            model_input_hash=hashlib.sha256(
                text.replace("?id=", "?limit=10&id=")
                .replace("&limit=10", "")
                .encode("utf-8")
            ).hexdigest(),
        )
        with pytest.raises(SnapshotContaminationError) as exc_info:
            index.validate_new_samples([sample])
        report = exc_info.value.report
        assert report["exact_overlap_count"] == 1
        assert report["matches"][0]["affected_split"] == split


def test_contamination_index_detects_near_duplicates_and_bounds_candidates():
    rows = []
    for index in range(2000):
        length = 50 + (index % 200)
        prefix = f"GET /synthetic/{index:04d}/"
        body = (hashlib.sha256(f"body-{index}".encode()).hexdigest() * 8)[
            : max(1, length - len(prefix))
        ]
        text = prefix + body
        rows.append({"combined_payload": text, "final_label": "Normal"})
    contamination_index = ContaminationIndex.from_historical_frames(
        [("train", pd.DataFrame(rows))]
    )
    source = rows[123]["combined_payload"]
    near_duplicate = dict(
        REQUIRED,
        sample_id="bounded-near-duplicate",
        model_input_text=source[:-1] + "y",
        model_input_hash=hashlib.sha256((source[:-1] + "y").encode()).hexdigest(),
    )

    with pytest.raises(SnapshotContaminationError) as exc_info:
        contamination_index.validate_new_samples([near_duplicate])

    report = exc_info.value.report
    assert report["near_duplicate_count"] == 1
    assert report["historical_row_count"] == 2000
    assert 0 < report["candidate_comparisons_checked"] < 2000


def test_contamination_index_uses_sequence_matcher_safe_length_bounds():
    historical_text = "GET /" + ("a" * 95)
    candidate_text = "GET /" + ("a" * 80)
    assert len(historical_text) == 100
    assert len(candidate_text) == 85

    contamination_index = ContaminationIndex.from_historical_frames(
        [
            (
                "train",
                pd.DataFrame(
                    [{"combined_payload": historical_text, "final_label": "Normal"}]
                ),
            )
        ]
    )
    candidate = dict(
        REQUIRED,
        sample_id="length-bound-near-duplicate",
        model_input_text=candidate_text,
        model_input_hash=hashlib.sha256(candidate_text.encode()).hexdigest(),
    )

    with pytest.raises(SnapshotContaminationError) as exc_info:
        contamination_index.validate_new_samples([candidate])

    report = exc_info.value.report
    assert report["near_duplicate_count"] == 1
    assert report["matches"][0]["similarity"] == pytest.approx(0.918919, abs=1e-6)


def test_contamination_index_does_not_retain_duplicate_raw_text():
    raw_text = "GET /sensitive/" + ("x" * 100)
    contamination_index = ContaminationIndex.from_historical_frames(
        [
            (
                "train",
                pd.DataFrame(
                    [{"combined_payload": raw_text, "final_label": "Normal"}]
                ),
            )
        ]
    )

    record = next(iter(contamination_index._records.values()))
    assert "text" not in record.__dataclass_fields__
    assert record.model_input_sha256 == hashlib.sha256(raw_text.encode()).hexdigest()


def test_contamination_index_benchmark_reports_memory_and_comparisons():
    result = run_benchmark(row_count=5000, query_count=8)

    assert result["historical_row_count"] == 5000
    assert result["query_count"] == 8
    assert result["peak_memory_mib"] > 0
    assert result["candidate_comparisons_checked"] >= 0
    assert result["full_scan_comparisons"] == 5000 * 8
    assert 0 <= result["candidate_comparison_ratio"] <= 1


def test_index_rejects_conflicting_labels_and_cross_day_duplicates():
    historical = pd.DataFrame(
        [{"combined_payload": "GET /health", "final_label": "Normal"}]
    )
    index = ContaminationIndex.from_historical_frames([("train", historical)])
    first = dict(
        REQUIRED, sample_id="day-01", model_input_text="GET /api/items?a=1&b=2"
    )
    first["model_input_hash"] = hashlib.sha256(
        first["model_input_text"].encode()
    ).hexdigest()
    conflict = dict(
        first,
        sample_id="day-01-conflict",
        ground_truth_label="SQL Injection",
        model_input_text="GET /api/items?b=2&a=1",
    )
    conflict["model_input_hash"] = hashlib.sha256(
        conflict["model_input_text"].encode()
    ).hexdigest()
    with pytest.raises(ValueError, match="conflicting daily label"):
        index.validate_new_samples([first, conflict])

    index.validate_new_samples([first])
    index.add_daily_samples([first])
    second = dict(
        first,
        sample_id="day-02-near-duplicate",
        batch_day=2,
        model_input_text="GET /api/items?a=1&b=3",
    )
    second["model_input_hash"] = hashlib.sha256(
        second["model_input_text"].encode()
    ).hexdigest()
    with pytest.raises(SnapshotContaminationError) as exc_info:
        index.validate_new_samples([second])
    assert exc_info.value.report["matches"][0]["affected_split"] == "cumulative_daily"


def test_snapshot_integrity_detects_contract_file_tampering(tmp_path: Path):
    historical = tmp_path / "historical"
    historical.mkdir()
    base = pd.DataFrame([{"combined_payload": "GET /health", "final_label": "Normal"}])
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

    assert validate_snapshot_integrity(result.snapshot_dir)["passed"] is True
    metadata_path = result.snapshot_dir / "metadata_preprocessing.json"
    metadata_path.write_text(
        metadata_path.read_text(encoding="utf-8").replace(
            "http-preprocessor-v1", "tampered-preprocessor"
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="contract_files_hash"):
        validate_snapshot_integrity(result.snapshot_dir)
