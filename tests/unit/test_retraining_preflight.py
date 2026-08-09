from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ml_model.retraining.generate_batches import generate_experiment_batches
from ml_model.retraining.preflight_20_day import run_data_preflight


def test_data_preflight_produces_all_twenty_cumulative_days_without_training(
    tmp_path: Path,
):
    experiment_root = tmp_path / "experiment"
    generate_experiment_batches(experiment_root)
    historical = tmp_path / "historical"
    historical.mkdir()
    frame = pd.DataFrame(
        [
            {"combined_payload": "get /health", "final_label": "Normal"},
            {"combined_payload": "get /legacy/sql", "final_label": "SQL Injection"},
        ]
    )
    for split in ("train", "validation", "test"):
        frame.to_parquet(historical / f"{split}.parquet", index=False)

    root = Path(__file__).resolve().parents[2]
    report = run_data_preflight(
        config_path=root / "ml_model/configs/retraining_20_day_v2.toml",
        historical_data_dir=historical,
        daily_batch_dir=experiment_root
        / "daily_batches"
        / "records_search_v2",
        output_dir=tmp_path / "preflight",
        allow_test_overrides=True,
    )

    assert report["status"] == "PREPARATION_SUCCESS"
    assert report["execution_mode"] == "controlled_data_preflight"
    assert report["real_training_status"] == "NOT_RUN"
    assert report["model_quality_conclusion"] == "NOT_PERMITTED"
    assert report["day_count"] == 20
    assert report["total_accepted_samples"] == 600
    assert report["total_rejected_samples"] == 0
    assert report["days"][-1]["day"] == 20
    assert report["days"][-1]["cumulative_fixture_samples"] == 600
    assert all(day["status"] == "READY_FOR_NATIVE_TRAINING" for day in report["days"])
    assert (tmp_path / "preflight" / "preflight_report.json").is_file()
    assert (tmp_path / "preflight" / "preflight_report.md").is_file()


def test_data_preflight_report_is_json_reproducible(tmp_path: Path):
    experiment_root = tmp_path / "experiment"
    generate_experiment_batches(experiment_root, days=range(1, 3))
    historical = tmp_path / "historical"
    historical.mkdir()
    frame = pd.DataFrame(
        [{"combined_payload": "get /health", "final_label": "Normal"}]
    )
    for split in ("train", "validation", "test"):
        frame.to_parquet(historical / f"{split}.parquet", index=False)
    root = Path(__file__).resolve().parents[2]
    kwargs = {
        "config_path": root / "ml_model/configs/retraining_20_day_v2.toml",
        "historical_data_dir": historical,
        "daily_batch_dir": experiment_root
        / "daily_batches"
        / "records_search_v2",
        "allow_test_overrides": True,
    }
    first = run_data_preflight(output_dir=tmp_path / "first", days=(1, 2), **kwargs)
    second = run_data_preflight(output_dir=tmp_path / "second", days=(1, 2), **kwargs)

    assert first["report_sha256"] == second["report_sha256"]
    assert json.loads(
        (tmp_path / "first" / "preflight_report.json").read_text(encoding="utf-8")
    ) == json.loads(
        (tmp_path / "second" / "preflight_report.json").read_text(encoding="utf-8")
    )
