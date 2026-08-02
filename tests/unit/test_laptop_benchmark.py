from __future__ import annotations

import json
from pathlib import Path

import pytest
import torch


def test_default_benchmark_matrix_targets_laptop_cuda_search_space():
    from ml_model.training.benchmark_laptop import default_benchmark_matrix

    matrix = default_benchmark_matrix()

    assert [case.batch_size for case in matrix] == [64, 64, 64, 96, 96, 128, 128]
    assert [case.eval_batch_size for case in matrix] == [
        128,
        128,
        128,
        192,
        192,
        256,
        256,
    ]
    assert [case.num_workers for case in matrix] == [0, 2, 4, 2, 4, 2, 4]
    assert [case.gradient_accumulation_steps for case in matrix] == [2, 2, 2, 1, 1, 1, 1]


def test_benchmark_writes_results_and_recommended_config(tmp_path: Path, monkeypatch):
    from ml_model.training import benchmark_laptop
    from ml_model.training.benchmark_laptop import BenchmarkCase
    from ml_model.training.config import TrainingConfig

    calls: list[TrainingConfig] = []

    def fake_run_training(config: TrainingConfig) -> Path:
        calls.append(config)
        config.output_dir.mkdir(parents=True, exist_ok=True)
        return config.output_dir

    elapsed = iter([10.0, 5.0])
    monkeypatch.setattr(benchmark_laptop, "run_training", fake_run_training)
    monkeypatch.setattr(benchmark_laptop, "_elapsed_seconds", lambda started_at: next(elapsed))
    monkeypatch.setattr(
        benchmark_laptop,
        "_cuda_peak_memory_mb",
        lambda device: 2048.0 if len(calls) == 1 else 3072.0,
    )
    monkeypatch.setattr(
        benchmark_laptop,
        "_device_metadata",
        lambda device: {"device": str(device), "cuda_available": True, "gpu_name": "GPU"},
    )

    output_dir = benchmark_laptop.run_benchmark(
        TrainingConfig(
            models=("distilbert",),
            seeds=(42,),
            device="cuda",
            precision="fp16",
            max_train_samples=1000,
            max_validation_samples=200,
            max_test_samples=200,
        ),
        output_dir=tmp_path,
        cases=[
            BenchmarkCase(64, 128, 2, 2),
            BenchmarkCase(96, 192, 2, 1),
        ],
    )

    assert output_dir == tmp_path
    assert [call.batch_size for call in calls] == [64, 96]
    assert [call.eval_batch_size for call in calls] == [128, 192]
    assert [call.num_workers for call in calls] == [2, 2]
    assert [call.gradient_accumulation_steps for call in calls] == [2, 1]
    assert all(call.prepare_only is False for call in calls)

    summary = json.loads((tmp_path / "benchmark_summary.json").read_text(encoding="utf-8"))
    assert summary["recommended_case"]["batch_size"] == 96
    assert summary["recommended_case"]["train_samples_per_second"] == 200.0
    assert (tmp_path / "benchmark_results.csv").is_file()
    assert (tmp_path / "benchmark_results.json").is_file()
    assert (tmp_path / "recommended_final_config.toml").read_text(
        encoding="utf-8"
    ).startswith("[training]")


def test_benchmark_records_cuda_oom_and_continues(tmp_path: Path, monkeypatch):
    from ml_model.training import benchmark_laptop
    from ml_model.training.benchmark_laptop import BenchmarkCase
    from ml_model.training.config import TrainingConfig

    def fake_run_training(config: TrainingConfig) -> Path:
        if config.batch_size == 128:
            raise torch.cuda.OutOfMemoryError("CUDA out of memory")
        config.output_dir.mkdir(parents=True, exist_ok=True)
        return config.output_dir

    monkeypatch.setattr(benchmark_laptop, "run_training", fake_run_training)
    monkeypatch.setattr(benchmark_laptop, "_elapsed_seconds", lambda started_at: 4.0)
    monkeypatch.setattr(benchmark_laptop, "_cuda_peak_memory_mb", lambda device: 1024.0)
    monkeypatch.setattr(
        benchmark_laptop,
        "_device_metadata",
        lambda device: {"device": str(device), "cuda_available": True, "gpu_name": "GPU"},
    )

    benchmark_laptop.run_benchmark(
        TrainingConfig(device="cuda", precision="fp16"),
        output_dir=tmp_path,
        cases=[
            BenchmarkCase(128, 256, 2, 1),
            BenchmarkCase(64, 128, 2, 2),
        ],
    )

    results = json.loads((tmp_path / "benchmark_results.json").read_text(encoding="utf-8"))

    assert [result["status"] for result in results] == ["oom", "passed"]
    assert json.loads((tmp_path / "benchmark_summary.json").read_text(encoding="utf-8"))[
        "recommended_case"
    ]["batch_size"] == 64


def test_benchmark_fails_when_no_case_passes(tmp_path: Path, monkeypatch):
    from ml_model.training import benchmark_laptop
    from ml_model.training.benchmark_laptop import BenchmarkCase
    from ml_model.training.config import TrainingConfig

    def fake_run_training(config: TrainingConfig) -> Path:
        raise RuntimeError("simulated training failure")

    monkeypatch.setattr(benchmark_laptop, "run_training", fake_run_training)
    monkeypatch.setattr(benchmark_laptop, "_cuda_peak_memory_mb", lambda device: None)
    monkeypatch.setattr(
        benchmark_laptop,
        "_device_metadata",
        lambda device: {"device": str(device), "cuda_available": True, "gpu_name": "GPU"},
    )

    with pytest.raises(RuntimeError, match="No benchmark cases passed"):
        benchmark_laptop.run_benchmark(
            TrainingConfig(device="cuda", precision="fp16"),
            output_dir=tmp_path,
            cases=[BenchmarkCase(128, 256, 2, 1)],
        )

    summary = json.loads((tmp_path / "benchmark_summary.json").read_text(encoding="utf-8"))
    assert summary["passed_cases"] == 0
    assert summary["recommended_case"] is None
