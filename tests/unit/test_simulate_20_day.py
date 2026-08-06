from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from ml_model.retraining.simulate_20_day import (
    SimulationHooks,
    evaluate_acceptance_gates,
    run_simulation,
    run_smoke,
)


def _write_config(path: Path) -> None:
    path.write_text(
        """
[experiment]
name = "controlled-retraining-20-day"
version = "retraining-20-day-v1"

[data]
historical_dataset_version = "v3_907k_cleaned"
preprocessing_version = "http-preprocessor-v1"

[model]
model_family = "native_distilbert"
model_id = "distilbert-base-uncased"
model_revision = "12040accade4e8a0f71eabdb258fecc2e7e948be"
daily_seed = 2026
confirmation_seeds = [42, 1337, 2026]
max_epochs = 4

[golden]
version = "golden-v1"
manifest_file = "golden_manifest.json"

[labels]
names = ["Code Injection", "Normal", "Other Attacks", "SQL Injection"]

[policy.thresholds]
low = 0.50
high = 0.80
critical = 0.90

[policy.actions]
normal = "ALLOWED"
low = "ALLOWED"
medium = "THROTTLED"
high = "BLOCKED"
critical = "BLOCKED"

[acceptance]
normal_false_positive_tolerance = 0.001
attack_escape_tolerance = 0.001
macro_f1_drop_tolerance = 0.002
normal_recall_minimum = 0.995
supported_attack_recall_drop_tolerance = 0.01
""".lstrip(),
        encoding="utf-8",
    )


def _write_batch(path: Path, day: int) -> None:
    path.write_text(
        json.dumps(
            {
                "sample_id": f"day-{day:02d}-001",
                "model_input_text": f"GET /api/users?page={day + 1}&limit=25",
                "ground_truth_label": "Normal",
                "batch_day": day,
                "source_type": "curated_fixture",
                "is_synthetic": True,
                "review_status": "approved_for_training",
                "provenance_id": f"fixture:day-{day:02d}-001",
                "preprocessing_version": "http-preprocessor-v1",
            },
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def test_acceptance_gates_report_rejection_reasons():
    result = evaluate_acceptance_gates(
        baseline={
            "normal_false_positive_rate": 0.01,
            "attack_escape_rate": 0.0,
            "macro_f1": 0.99,
            "normal_recall": 1.0,
            "supported_attack_recall": {"SQL Injection": 1.0},
        },
        candidate={
            "normal_false_positive_rate": 0.02,
            "attack_escape_rate": 0.0,
            "macro_f1": 0.99,
            "normal_recall": 1.0,
            "supported_attack_recall": {"SQL Injection": 1.0},
        },
        golden={"passed": True},
        package_passed=True,
        reload_passed=True,
        backend_passed=True,
    )

    assert result.passed is False
    assert "normal_false_positive_rate" in result.failures


def test_smoke_simulation_preserves_training_failure_and_does_not_touch_active_registry(
    tmp_path: Path,
):
    config_path = tmp_path / "experiment.toml"
    _write_config(config_path)
    historical = tmp_path / "historical"
    historical.mkdir()
    base = pd.DataFrame([{"combined_payload": "GET /health", "final_label": "Normal"}])
    for split in ("train", "validation", "test"):
        base.to_parquet(historical / f"{split}.parquet", index=False)
    batches = tmp_path / "batches"
    batches.mkdir()
    _write_batch(batches / "day_01.jsonl", 1)
    active_registry = tmp_path / "active-registry"
    active_registry.mkdir()
    marker = active_registry / "active.marker"
    marker.write_text("unchanged", encoding="utf-8")

    def fail_training(*_args, **_kwargs):
        raise RuntimeError("synthetic training failure")

    report = run_simulation(
        config_path=config_path,
        historical_data_dir=historical,
        daily_batch_dir=batches,
        output_dir=tmp_path / "outputs",
        days=[1],
        baseline={
            "normal_false_positive_rate": 0.0,
            "attack_escape_rate": 0.0,
            "macro_f1": 1.0,
            "normal_recall": 1.0,
            "supported_attack_recall": {},
        },
        golden_texts=set(),
        hooks=SimulationHooks(train=fail_training),
        active_registry_dir=active_registry,
    )

    assert report.days[0]["status"] == "REJECTED"
    assert report.days[0]["stage"] == "training"
    assert "synthetic training failure" in report.days[0]["error"]
    assert marker.read_text(encoding="utf-8") == "unchanged"
    assert (tmp_path / "outputs" / "simulation_report.json").is_file()


def test_two_day_smoke_completes_and_repeats_input_hashes(tmp_path: Path):
    config_path = tmp_path / "experiment.toml"
    _write_config(config_path)
    first = run_smoke(config_path=config_path, output_dir=tmp_path / "smoke-1")
    second = run_smoke(config_path=config_path, output_dir=tmp_path / "smoke-2")

    assert first.status == "SUCCESS"
    assert [day["input_hash"] for day in first.days] == [
        day["input_hash"] for day in second.days
    ]
    assert [day["snapshot_hash"] for day in first.days] == [
        day["snapshot_hash"] for day in second.days
    ]


def test_simulation_preserves_incomplete_evaluation_and_packaging_failures(
    tmp_path: Path,
):
    config_path = tmp_path / "experiment.toml"
    _write_config(config_path)
    historical = tmp_path / "historical"
    historical.mkdir()
    base = pd.DataFrame([{"combined_payload": "GET /health", "final_label": "Normal"}])
    for split in ("train", "validation", "test"):
        base.to_parquet(historical / f"{split}.parquet", index=False)
    batches = tmp_path / "batches"
    batches.mkdir()
    _write_batch(batches / "day_01.jsonl", 1)
    baseline = {
        "normal_false_positive_rate": 0.0,
        "attack_escape_rate": 0.0,
        "macro_f1": 1.0,
        "normal_recall": 1.0,
        "supported_attack_recall": {},
    }

    def train(**kwargs):
        path = kwargs["day_dir"] / "run"
        path.mkdir(parents=True)
        return path

    incomplete = run_simulation(
        config_path=config_path,
        historical_data_dir=historical,
        daily_batch_dir=batches,
        output_dir=tmp_path / "incomplete",
        days=[1],
        baseline=baseline,
        golden_texts=set(),
        hooks=SimulationHooks(
            train=train,
            evaluate=lambda **_: {"status": "incomplete"},
        ),
    )
    assert incomplete.days[0]["stage"] == "evaluation"
    assert "incomplete training run bundle" in incomplete.days[0]["error"]

    packaged = run_simulation(
        config_path=config_path,
        historical_data_dir=historical,
        daily_batch_dir=batches,
        output_dir=tmp_path / "packaging-failure",
        days=[1],
        baseline=baseline,
        golden_texts=set(),
        hooks=SimulationHooks(
            train=train,
            evaluate=lambda **_: {
                "status": "complete",
                "metrics": {
                    "normal_false_positive_rate": 0.0,
                    "attack_escape_rate": 0.0,
                    "macro_f1": 1.0,
                    "normal_recall": 1.0,
                    "supported_attack_recall": {},
                },
            },
            package=lambda **_: (_ for _ in ()).throw(
                RuntimeError("packaging failure")
            ),
        ),
    )
    assert packaged.days[0]["stage"] == "packaging"
    assert "packaging failure" in packaged.days[0]["error"]
