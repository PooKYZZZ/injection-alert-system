from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

from ml_model.preprocessing.model_input import prepare_legacy_model_input
from ml_model.retraining.generate_batches import (
    DAILY_SAMPLE_COUNT,
    HARD_NORMAL_COUNT,
    NORMAL_COUNT,
    _encoded_request,
    generate_experiment_batches,
    validate_fixture_manifest,
)


def _read_rows(batch_path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in batch_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_generator_creates_route_specific_30_row_batches_for_all_days(
    tmp_path: Path,
):
    result = generate_experiment_batches(tmp_path / "experiment", seed=2026)
    batch_root = tmp_path / "experiment" / "daily_batches" / "records_search_v2"

    assert result["day_count"] == 20
    assert result["total_sample_count"] == 600
    assert result["target_route"] == "/records/search"
    assert result["target_method"] == "GET"

    for day in range(1, 21):
        rows = _read_rows(batch_root / f"day_{day:02d}.jsonl")
        assert len(rows) == DAILY_SAMPLE_COUNT
        assert sum(row["ground_truth_label"] == "Normal" for row in rows) == (
            NORMAL_COUNT
        )
        assert sum(
            row["scenario_type"] == "hard_normal" for row in rows
        ) == HARD_NORMAL_COUNT
        assert all(row["batch_day"] == day for row in rows)
        assert all(row["request_method"] == "GET" for row in rows)
        assert all(row["request_path"] == "/records/search" for row in rows)
        assert all(row["route_scope"] == "target_route" for row in rows)
        assert all(row["is_synthetic"] is True for row in rows)
        assert all(row["review_status"] == "curated_simulation_fixture" for row in rows)
        assert all(
            row["preprocessing_version"] == "http-preprocessor-v1" for row in rows
        )
        assert all(
            row["model_input_hash"]
            == hashlib.sha256(str(row["model_input_text"]).encode("utf-8")).hexdigest()
            for row in rows
        )
        assert all("predicted_label" not in row for row in rows)


def test_generator_uses_the_three_day_attack_rotation(tmp_path: Path):
    result = generate_experiment_batches(tmp_path / "experiment", seed=2026)
    batch_root = tmp_path / "experiment" / "daily_batches" / "records_search_v2"

    expected = {
        1: {"SQL Injection": 4, "Code Injection": 3, "Other Attacks": 3},
        2: {"SQL Injection": 3, "Code Injection": 4, "Other Attacks": 3},
        3: {"SQL Injection": 3, "Code Injection": 3, "Other Attacks": 4},
    }
    for day in range(1, 21):
        rows = _read_rows(batch_root / f"day_{day:02d}.jsonl")
        counts = {
            label: sum(row["ground_truth_label"] == label for row in rows)
            for label in ("SQL Injection", "Code Injection", "Other Attacks")
        }
        assert counts == expected[((day - 1) % 3) + 1]

    assert result["label_distribution"] == {
        "Code Injection": 67,
        "Normal": 400,
        "Other Attacks": 66,
        "SQL Injection": 67,
    }


def test_generator_is_reproducible_and_records_manifest_hashes(tmp_path: Path):
    first = generate_experiment_batches(tmp_path / "first", seed=2026)
    second = generate_experiment_batches(tmp_path / "second", seed=2026)

    assert first["manifest_sha256"] == second["manifest_sha256"]
    assert first["batch_hashes"] == second["batch_hashes"]
    for day in range(1, 21):
        first_rows = (
            tmp_path / "first" / "daily_batches" / "records_search_v2"
            / f"day_{day:02d}.jsonl"
        ).read_bytes()
        second_rows = (
            tmp_path / "second" / "daily_batches" / "records_search_v2"
            / f"day_{day:02d}.jsonl"
        ).read_bytes()
        assert first_rows == second_rows
        assert b"\r\n" not in first_rows


def test_generator_rejects_unknown_seed_contract(tmp_path: Path):
    try:
        generate_experiment_batches(tmp_path / "experiment", seed=7)
    except ValueError as exc:
        assert "seed" in str(exc)
    else:
        raise AssertionError("unsupported seed should be rejected")


def test_generated_text_uses_the_declared_legacy_preprocessor():
    raw = "GET /records/search?query=North%20District HTTP/1.1\r\n\r\n"
    expected, _, version = prepare_legacy_model_input(raw)

    assert version == "http-preprocessor-v1"
    assert _encoded_request("North District") == expected
    assert "%20" not in expected
    assert expected == "get /records/search?query=north district"


def test_fixture_manifest_rejects_tampered_batch(tmp_path: Path):
    experiment_root = tmp_path / "experiment"
    generate_experiment_batches(experiment_root, days=(1,))
    batch_path = (
        experiment_root / "daily_batches" / "records_search_v2" / "day_01.jsonl"
    )
    batch_path.write_text(
        batch_path.read_text(encoding="utf-8") + "\n",
        encoding="utf-8",
    )

    try:
        validate_fixture_manifest(experiment_root)
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("tampered fixture batch should be rejected")


def test_fixture_manifest_rejects_unlisted_or_unexpected_days(tmp_path: Path):
    experiment_root = tmp_path / "experiment"
    generate_experiment_batches(experiment_root, days=(1, 2))
    batch_root = experiment_root / "daily_batches" / "records_search_v2"
    shutil.copyfile(batch_root / "day_02.jsonl", batch_root / "day_03.jsonl")

    try:
        validate_fixture_manifest(experiment_root, expected_days=(1, 2))
    except ValueError as exc:
        assert "day" in str(exc).lower()
    else:
        raise AssertionError("unlisted fixture days should be rejected")
