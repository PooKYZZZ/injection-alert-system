"""Validate all prepared days and build cumulative snapshots without training."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from ml_model.evaluation.golden_controls import load_golden_controls
from ml_model.preprocessing.dataset_io import (
    load_dataset_file_manifest,
    validate_dataset_preprocessing,
)
from ml_model.retraining.experiment_contract import (
    canonical_json_sha256,
    load_experiment_config,
    sha256_file,
)
from ml_model.retraining.generate_batches import validate_fixture_manifest
from ml_model.retraining.snapshots import (
    ContaminationIndex,
    SnapshotResult,
    build_cumulative_snapshot,
    capture_historical_file_hashes,
    load_historical_frames,
    validate_snapshot_integrity,
)
from ml_model.retraining.validate_batch import (
    BatchValidationReport,
    validate_batch_file,
)


def _requested_days(days: Iterable[int] | None) -> tuple[int, ...]:
    selected = tuple(sorted({int(day) for day in (days or range(1, 21))}))
    if not selected or any(day < 1 or day > 20 for day in selected):
        raise ValueError("days must contain values from 1 through 20")
    return tuple(range(1, max(selected) + 1))


def _write_day_report(day_dir: Path, payload: dict[str, Any]) -> None:
    day_dir.mkdir(parents=True, exist_ok=True)
    (day_dir / "day_preflight.json").write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _fixture_manifest_info(
    daily_batch_dir: Path,
    *,
    expected_days: Iterable[int] | None = None,
    require_complete: bool = False,
) -> dict[str, Any]:
    experiment_root = daily_batch_dir.parent.parent
    manifest_path = experiment_root / "manifest.json"
    if not manifest_path.is_file():
        return {"present": False}
    manifest = validate_fixture_manifest(
        experiment_root,
        expected_days=expected_days,
        require_complete=require_complete,
    )
    return {
        "present": True,
        "manifest_sha256": sha256_file(manifest_path),
        "fixture_manifest_sha256": manifest.get("manifest_sha256"),
        "experiment_version": manifest.get("experiment_version"),
        "generator_version": manifest.get("generator_version"),
        "seed": manifest.get("seed"),
        "synthetic_fixture_only": manifest.get("synthetic_fixture_only"),
    }


def _write_markdown(output_dir: Path, report: dict[str, Any]) -> None:
    lines = [
        "# Controlled 20-Day Data Preflight",
        "",
        "This report validates prepared synthetic route-specific batches and",
        "cumulative snapshots. It does not train, evaluate, package, promote,",
        "or deploy a model.",
        "",
        f"- Status: `{report['status']}`",
        f"- Execution mode: `{report['execution_mode']}`",
        f"- Real training status: `{report['real_training_status']}`",
        f"- Model-quality conclusion: `{report['model_quality_conclusion']}`",
        f"- Accepted fixture rows: `{report['total_accepted_samples']}`",
        f"- Rejected fixture rows: `{report['total_rejected_samples']}`",
        "",
        (
            "| Day | Batch rows | Cumulative fixture rows | Exact overlap | "
            "Near duplicate | Status |"
        ),
        "| ---: | ---: | ---: | ---: | ---: | --- |",
    ]
    for day in report["days"]:
        contamination = day.get("contamination", {})
        lines.append(
            "| {day} | {batch} | {cumulative} | {exact} | {near} | {status} |".format(
                day=day["day"],
                batch=day.get("accepted_samples", 0),
                cumulative=day.get("cumulative_fixture_samples", 0),
                exact=contamination.get("exact_overlap_count", "NOT_AVAILABLE"),
                near=contamination.get("near_duplicate_count", "NOT_AVAILABLE"),
                status=day["status"],
            )
        )
    (output_dir / "preflight_report.md").write_text(
        "\n".join(lines) + "\n", encoding="utf-8"
    )


def run_data_preflight(
    *,
    config_path: Path | str,
    historical_data_dir: Path | str,
    daily_batch_dir: Path | str,
    output_dir: Path | str,
    days: Iterable[int] | None = None,
    allow_test_overrides: bool = False,
) -> dict[str, Any]:
    """Validate prepared batches and snapshots while explicitly skipping training."""

    config = load_experiment_config(config_path)
    historical_root = Path(historical_data_dir).expanduser().resolve()
    batch_root = Path(daily_batch_dir).expanduser().resolve()
    output_root = Path(output_dir).expanduser().resolve()
    days_to_process = _requested_days(days)

    fixture_manifest_path = batch_root.parent.parent / "manifest.json"
    try:
        validate_fixture_manifest(
            batch_root.parent.parent,
            expected_days=days_to_process,
            require_complete=not allow_test_overrides,
        )
    except Exception as exc:
        output_root.mkdir(parents=True, exist_ok=True)
        unsigned_report: dict[str, Any] = {
            "report_version": "controlled-data-preflight.v1",
            "status": "BLOCKED",
            "execution_mode": "controlled_data_preflight",
            "real_training_status": "NOT_RUN",
            "model_quality_conclusion": "NOT_PERMITTED",
            "production_data": False,
            "experiment_contract_hash": config.contract_hash,
            "fixture_manifest": {
                "present": fixture_manifest_path.is_file(),
                "error": str(exc),
            },
            "requested_days": list(days_to_process),
            "day_count": 0,
            "total_accepted_samples": 0,
            "total_rejected_samples": 0,
            "days": [],
        }
        report = {
            **unsigned_report,
            "report_sha256": canonical_json_sha256(unsigned_report),
        }
        (output_root / "preflight_report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _write_markdown(output_root, report)
        return report

    if not allow_test_overrides:
        config.validate_runtime_inputs(
            historical_data_dir=historical_root,
            daily_batch_dir=batch_root,
            days=days_to_process,
        )
        validate_dataset_preprocessing(
            historical_root,
            expected_dataset_version=config.historical_dataset_version,
            expected_preprocessing_version=config.preprocessing_version,
        )
        load_dataset_file_manifest(historical_root)
    else:
        for split in ("train", "validation", "test"):
            if not (historical_root / f"{split}.parquet").is_file():
                raise FileNotFoundError(f"historical {split} split is missing")

    controls = load_golden_controls(config.golden_manifest_file)
    historical_frames = load_historical_frames(historical_root)
    historical_data_file_hashes = capture_historical_file_hashes(historical_root)
    contamination_index = ContaminationIndex.from_historical_frames(
        historical_frames
    )
    output_root.mkdir(parents=True, exist_ok=True)
    cumulative_samples: list[dict[str, Any]] = []
    day_reports: list[dict[str, Any]] = []

    for day in days_to_process:
        day_dir = output_root / f"day_{day:02d}"
        batch_path = batch_root / f"day_{day:02d}.jsonl"
        report: dict[str, Any] = {
            "day": day,
            "status": "BLOCKED",
            "stage": "batch_validation",
        }
        try:
            batch: BatchValidationReport = validate_batch_file(
                batch_path,
                expected_preprocessing_version=config.preprocessing_version,
                expected_batch_day=day,
                golden_controls=controls,
                allow_synthetic_fixtures=True,
                quarantine_dir=day_dir / "quarantine",
            )
            report["batch_input_sha256"] = batch.input_sha256
            report["batch_validation"] = batch.to_dict()
            report["accepted_samples"] = len(batch.accepted_samples)
            report["rejected_samples"] = len(batch.rejected_samples)
            if not batch.passed:
                report["error"] = "; ".join(
                    str(item["reason"]) for item in batch.rejected_samples
                )
                _write_day_report(day_dir, report)
                day_reports.append(report)
                break
            cumulative_samples.extend(batch.accepted_samples)
        except Exception as exc:
            report["error"] = str(exc)
            _write_day_report(day_dir, report)
            day_reports.append(report)
            break

        try:
            snapshot: SnapshotResult = build_cumulative_snapshot(
                historical_data_dir=historical_root,
                cumulative_samples=cumulative_samples,
                new_samples=batch.accepted_samples,
                output_root=day_dir / "snapshot",
                day=day,
                dataset_version=config.historical_dataset_version,
                preprocessing_version=config.preprocessing_version,
                project_root=config.project_root,
                contamination_index=contamination_index,
                historical_frames=historical_frames,
                historical_data_file_hashes=historical_data_file_hashes,
            )
            report["contamination"] = snapshot.manifest["contamination"]
            report["snapshot_integrity"] = validate_snapshot_integrity(
                snapshot.snapshot_dir
            )
            report["snapshot_hash"] = snapshot.output_hash
            report["snapshot_manifest"] = snapshot.manifest
            report["cumulative_fixture_samples"] = len(cumulative_samples)
            report["cumulative_training_rows"] = snapshot.train_rows
            report["cumulative_label_distribution"] = dict(
                sorted(Counter(
                    str(sample["ground_truth_label"])
                    for sample in cumulative_samples
                ).items())
            )
            report["stage"] = "preflight_complete"
            report["status"] = "READY_FOR_NATIVE_TRAINING"
        except Exception as exc:
            report["error"] = str(exc)
            report["contamination"] = getattr(exc, "report", {})
            _write_day_report(day_dir, report)
            day_reports.append(report)
            break
        _write_day_report(day_dir, report)
        day_reports.append(report)

    all_days_ready = len(day_reports) == len(days_to_process) and all(
        report["status"] == "READY_FOR_NATIVE_TRAINING" for report in day_reports
    )
    complete = days_to_process == tuple(range(1, 21))
    accepted_total = sum(
        int(report.get("accepted_samples", 0)) for report in day_reports
    )
    rejected_total = sum(
        int(report.get("rejected_samples", 0)) for report in day_reports
    )
    unsigned_report: dict[str, Any] = {
        "report_version": "controlled-data-preflight.v1",
        "status": (
            "PREPARATION_SUCCESS"
            if complete and all_days_ready
            else "PREPARATION_PARTIAL"
            if all_days_ready
            else "BLOCKED"
        ),
        "execution_mode": "controlled_data_preflight",
        "real_training_status": "NOT_RUN",
        "model_quality_conclusion": "NOT_PERMITTED",
        "production_data": False,
        "experiment_contract_hash": config.contract_hash,
        "fixture_manifest": _fixture_manifest_info(
            batch_root,
            expected_days=days_to_process,
            require_complete=not allow_test_overrides,
        ),
        "golden_controls": {
            "manifest_file_sha256": sha256_file(config.golden_manifest_file),
            "canonical_manifest_sha256": str(
                controls.manifest["manifest_sha256"]
            ),
            "cases_file_sha256": sha256_file(config.golden_cases_file),
        },
        "requested_days": list(days_to_process),
        "day_count": len(day_reports),
        "total_accepted_samples": accepted_total,
        "total_rejected_samples": rejected_total,
        "days": day_reports,
    }
    report = {
        **unsigned_report,
        "report_sha256": canonical_json_sha256(unsigned_report),
    }
    (output_root / "preflight_report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    _write_markdown(output_root, report)
    return report


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--historical-data-dir", type=Path, required=True)
    parser.add_argument("--daily-batch-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--days", nargs="+", type=int, default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    report = run_data_preflight(
        config_path=args.config,
        historical_data_dir=args.historical_data_dir,
        daily_batch_dir=args.daily_batch_dir,
        output_dir=args.output_dir,
        days=args.days,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PREPARATION_SUCCESS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
