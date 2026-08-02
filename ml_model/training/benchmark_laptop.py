"""Laptop CUDA benchmark runner for choosing final DistilBERT training settings."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import time
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import torch

from ml_model.training.config import TrainingConfig, load_training_config
from ml_model.training.paths import default_training_output_dir, resolve_project_root
from ml_model.training.train import run_training


@dataclass(frozen=True)
class BenchmarkCase:
    batch_size: int
    eval_batch_size: int
    num_workers: int
    gradient_accumulation_steps: int


@dataclass(frozen=True)
class BenchmarkResult:
    case_index: int
    status: str
    batch_size: int
    eval_batch_size: int
    num_workers: int
    gradient_accumulation_steps: int
    precision: str
    device: str
    elapsed_seconds: float | None
    max_train_samples: int | None
    train_samples_per_second: float | None
    peak_cuda_memory_mb: float | None
    run_dir: str | None
    error: str | None


def default_benchmark_matrix() -> list[BenchmarkCase]:
    return [
        BenchmarkCase(64, 128, 0, 2),
        BenchmarkCase(64, 128, 2, 2),
        BenchmarkCase(64, 128, 4, 2),
        BenchmarkCase(96, 192, 2, 1),
        BenchmarkCase(96, 192, 4, 1),
        BenchmarkCase(128, 256, 2, 1),
        BenchmarkCase(128, 256, 4, 1),
    ]


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def _default_output_dir() -> Path:
    project_root = resolve_project_root()
    return (
        default_training_output_dir(project_root=project_root)
        / "laptop_benchmarks"
        / f"distilbert_cuda_{_utc_timestamp()}"
    )


def _elapsed_seconds(started_at: float) -> float:
    return float(time.perf_counter() - started_at)


def _reset_cuda_peak_memory(device: torch.device) -> None:
    if device.type == "cuda" and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats(device)


def _cuda_peak_memory_mb(device: torch.device) -> float | None:
    if device.type != "cuda" or not torch.cuda.is_available():
        return None
    return float(torch.cuda.max_memory_allocated(device) / (1024 * 1024))


def _device_metadata(device: torch.device) -> dict[str, object]:
    payload: dict[str, object] = {
        "device": str(device),
        "cuda_available": bool(torch.cuda.is_available()),
        "torch_version": torch.__version__,
        "torch_cuda_version": torch.version.cuda,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
    }
    if device.type == "cuda" and torch.cuda.is_available():
        payload["gpu_name"] = torch.cuda.get_device_name(device)
        props = torch.cuda.get_device_properties(device)
        payload["gpu_total_memory_mb"] = float(props.total_memory / (1024 * 1024))
    return payload


def _case_output_dir(base_dir: Path, case_index: int, case: BenchmarkCase) -> Path:
    return base_dir / (
        f"case_{case_index:02d}_bs{case.batch_size}_"
        f"eval{case.eval_batch_size}_workers{case.num_workers}_"
        f"accum{case.gradient_accumulation_steps}"
    )


def _training_config_for_case(
    base_config: TrainingConfig,
    case: BenchmarkCase,
    *,
    case_output_dir: Path,
) -> TrainingConfig:
    return replace(
        base_config,
        models=("distilbert",),
        seeds=(base_config.seeds[0],),
        output_dir=case_output_dir,
        device="cuda",
        precision="fp16",
        batch_size=case.batch_size,
        eval_batch_size=case.eval_batch_size,
        num_workers=case.num_workers,
        gradient_accumulation_steps=case.gradient_accumulation_steps,
        epochs=1,
        resume=False,
        resume_checkpoint=None,
        prepare_only=False,
        max_train_samples=base_config.max_train_samples or 4096,
        max_validation_samples=base_config.max_validation_samples or 1024,
        max_test_samples=base_config.max_test_samples or 1024,
    ).validate()


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _recommend_result(results: Iterable[BenchmarkResult]) -> BenchmarkResult | None:
    passed = [result for result in results if result.status == "passed"]
    if not passed:
        return None
    return max(
        passed,
        key=lambda result: (
            result.train_samples_per_second or 0.0,
            result.batch_size,
            -result.num_workers,
        ),
    )


def _recommended_config_toml(base_config: TrainingConfig, result: BenchmarkResult) -> str:
    return "\n".join(
        [
            "[training]",
            f'dataset_version = "{base_config.dataset_version}"',
            'models = ["distilbert"]',
            f"seeds = {list(base_config.seeds)}",
            'device = "cuda"',
            'precision = "fp16"',
            f"batch_size = {result.batch_size}",
            f"eval_batch_size = {result.eval_batch_size}",
            f"epochs = {base_config.epochs}",
            f"learning_rate = {base_config.learning_rate or 0.00003}",
            f"num_workers = {result.num_workers}",
            f"checkpoint_interval_epochs = {base_config.checkpoint_interval_epochs}",
            "resume = true",
            f"max_seq_len = {base_config.max_seq_len or 128}",
            f"gradient_accumulation_steps = {result.gradient_accumulation_steps}",
            "",
        ]
    )


def run_benchmark(
    base_config: TrainingConfig,
    *,
    output_dir: Path | None = None,
    cases: Iterable[BenchmarkCase] | None = None,
) -> Path:
    benchmark_dir = (output_dir or _default_output_dir()).expanduser().resolve()
    benchmark_dir.mkdir(parents=True, exist_ok=True)

    matrix = list(cases or default_benchmark_matrix())
    device = torch.device("cuda")
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "benchmark_dir": str(benchmark_dir),
        "base_config": base_config.to_dict(),
        "device": _device_metadata(device),
        "matrix": [asdict(case) for case in matrix],
    }
    _write_json(benchmark_dir / "benchmark_bootstrap.json", metadata)

    results: list[BenchmarkResult] = []
    for index, case in enumerate(matrix, start=1):
        config = _training_config_for_case(
            base_config,
            case,
            case_output_dir=_case_output_dir(benchmark_dir, index, case),
        )
        started_at = time.perf_counter()
        _reset_cuda_peak_memory(device)
        try:
            run_dir = run_training(config)
            elapsed = _elapsed_seconds(started_at)
            max_train_samples = config.max_train_samples
            throughput = (
                float(max_train_samples / elapsed)
                if max_train_samples and elapsed > 0
                else None
            )
            result = BenchmarkResult(
                case_index=index,
                status="passed",
                batch_size=case.batch_size,
                eval_batch_size=case.eval_batch_size,
                num_workers=case.num_workers,
                gradient_accumulation_steps=case.gradient_accumulation_steps,
                precision=config.precision,
                device=config.device,
                elapsed_seconds=float(elapsed),
                max_train_samples=max_train_samples,
                train_samples_per_second=throughput,
                peak_cuda_memory_mb=_cuda_peak_memory_mb(device),
                run_dir=str(run_dir),
                error=None,
            )
        except torch.cuda.OutOfMemoryError as exc:
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            result = BenchmarkResult(
                case_index=index,
                status="oom",
                batch_size=case.batch_size,
                eval_batch_size=case.eval_batch_size,
                num_workers=case.num_workers,
                gradient_accumulation_steps=case.gradient_accumulation_steps,
                precision=config.precision,
                device=config.device,
                elapsed_seconds=None,
                max_train_samples=config.max_train_samples,
                train_samples_per_second=None,
                peak_cuda_memory_mb=_cuda_peak_memory_mb(device),
                run_dir=None,
                error=str(exc),
            )
        except Exception as exc:  # noqa: BLE001 - benchmark must record failures.
            result = BenchmarkResult(
                case_index=index,
                status="failed",
                batch_size=case.batch_size,
                eval_batch_size=case.eval_batch_size,
                num_workers=case.num_workers,
                gradient_accumulation_steps=case.gradient_accumulation_steps,
                precision=config.precision,
                device=config.device,
                elapsed_seconds=None,
                max_train_samples=config.max_train_samples,
                train_samples_per_second=None,
                peak_cuda_memory_mb=_cuda_peak_memory_mb(device),
                run_dir=None,
                error=f"{type(exc).__name__}: {exc}",
            )
        results.append(result)

        rows = [asdict(item) for item in results]
        _write_json(benchmark_dir / "benchmark_results.json", rows)
        _write_csv(benchmark_dir / "benchmark_results.csv", rows)

    recommended = _recommend_result(results)
    summary = {
        "benchmark_dir": str(benchmark_dir),
        "total_cases": len(results),
        "passed_cases": sum(1 for item in results if item.status == "passed"),
        "oom_cases": sum(1 for item in results if item.status == "oom"),
        "failed_cases": sum(1 for item in results if item.status == "failed"),
        "recommended_case": asdict(recommended) if recommended else None,
    }
    _write_json(benchmark_dir / "benchmark_summary.json", summary)
    if recommended:
        (benchmark_dir / "recommended_final_config.toml").write_text(
            _recommended_config_toml(base_config, recommended),
            encoding="utf-8",
        )
    else:
        raise RuntimeError(
            f"No benchmark cases passed. See {benchmark_dir / 'benchmark_results.json'}"
        )
    return benchmark_dir


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--max-train-samples", type=int)
    parser.add_argument("--max-validation-samples", type=int)
    parser.add_argument("--max-test-samples", type=int)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)
    config = load_training_config(args.config)
    overrides = {
        key: value
        for key, value in {
            "max_train_samples": args.max_train_samples,
            "max_validation_samples": args.max_validation_samples,
            "max_test_samples": args.max_test_samples,
        }.items()
        if value is not None
    }
    config = replace(config, **overrides).validate()
    output_dir = run_benchmark(config, output_dir=args.output_dir)
    print(f"Laptop benchmark directory: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
